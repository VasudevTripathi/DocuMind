import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
import numpy as np
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.schemas.qa import SourceChunk, GroundingMetadata
from app.schemas.comparison import (
    DocumentInfo,
    AdditionItem,
    RemovalItem,
    ModificationItem,
    ConflictItem,
    CommonItem,
    ComparisonResponse
)
from app.services.chunk_service import ChunkService
from app.services.embedding_service import embedding_service, BaseEmbeddingService
from app.services.reranker import reranker, RetrievalReranker
from app.services.grounding_service import (
    grounding_service,
    GroundingService,
    GroundingStatus,
    GroundingEvaluation,
    NumericEntity,
    canonical_unit,
    EXCLUSIVE_METRIC_ATTRIBUTES
)
from app.services.llm_service import llm_service, LLMService
from app.services.retrieval_service import DocumentNotFoundError, retrieval_service, RetrievalService

logger = logging.getLogger("documind.comparison")

# Opposing semantic concept pairs for contradiction detection
CONTRADICTION_PAIRS = [
    ({"mandatory", "required"}, {"optional", "voluntary"}),
    ({"enabled", "activated"}, {"disabled", "deactivated"}),
    ({"allowed", "permitted"}, {"prohibited", "forbidden", "disallowed"}),
    ({"active"}, {"inactive", "deprecated"}),
    ({"true"}, {"false"}),
    ({"yes"}, {"no"}),
    ({"supports", "supported"}, {"unsupported", "deprecated", "prohibited"}),
    ({"minimum", "min"}, {"maximum", "max"}),
    ({"increase", "increased"}, {"decrease", "decreased"}),
    ({"pass", "passed", "success"}, {"fail", "failed", "failure"}),
    ({"encrypted"}, {"unencrypted", "plaintext"}),
    ({"public"}, {"private"}),
    ({"strict"}, {"permissive", "lenient"}),
]

STOP_TOPIC_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at",
    "to", "for", "with", "by", "from", "of", "it", "this", "that", "these", "those"
}


@dataclass
class EvidenceStatement:
    id: str
    document_id: str
    document_name: str
    chunk_id: str
    chunk_index: int
    page_number: Optional[int]
    chunk_text: str
    text: str
    clean_lower: str
    tokens: Set[str]
    numeric_entities: List[NumericEntity] = field(default_factory=list)


def extract_topic_from_text(text: str, shared_tokens: Optional[Set[str]] = None) -> str:
    """
    Deterministically extracts a concise, human-readable topic name for a difference item.
    Prioritizes key-value prefixes, attribute tokens, and key noun phrases.
    """
    clean = text.strip()

    # 1. Key-value style: "Maximum storage: 500 GB" -> "Maximum Storage"
    kv_match = re.match(r"^([A-Za-z0-9_\-\s]{3,35}):", clean)
    if kv_match:
        topic_candidate = kv_match.group(1).strip()
        if topic_candidate.lower() not in STOP_TOPIC_WORDS:
            return topic_candidate.title()

    # 2. Shared tokens if available
    if shared_tokens:
        substantive = [t for t in shared_tokens if t not in STOP_TOPIC_WORDS and len(t) > 2]
        if substantive:
            return " ".join(substantive[:3]).title()

    # 3. Capitalized phrases or first words
    tokens = [w for w in re.findall(r"\b[A-Za-z0-9\-_]+\b", clean) if w.lower() not in STOP_TOPIC_WORDS]
    if tokens:
        return " ".join(tokens[:3]).title()

    return "General Specification"


UNIT_FAMILIES: Dict[str, str] = {
    "b": "storage", "byte": "storage", "bytes": "storage",
    "kb": "storage", "kilobyte": "storage", "kilobytes": "storage",
    "mb": "storage", "megabyte": "storage", "megabytes": "storage",
    "gb": "storage", "gigabyte": "storage", "gigabytes": "storage",
    "tb": "storage", "terabyte": "storage", "terabytes": "storage",
    "ms": "time", "millisecond": "time", "milliseconds": "time",
    "s": "time", "sec": "time", "secs": "time", "second": "time", "seconds": "time",
    "m": "time", "min": "time", "mins": "time", "minute": "time", "minutes": "time",
    "h": "time", "hr": "time", "hrs": "time", "hour": "time", "hours": "time",
    "d": "time", "day": "time", "days": "time",
    "wk": "time", "week": "time", "weeks": "time",
    "mo": "time", "month": "time", "months": "time",
    "yr": "time", "yrs": "time", "year": "time", "years": "time",
    "%": "percentage", "pct": "percentage", "percent": "percentage", "percentage": "percentage",
    "date": "date"
}

def get_unit_family(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    return UNIT_FAMILIES.get(unit.lower().strip(), unit.lower().strip())


class ComparisonService:
    """
    Evidence-grounded, deterministic backend engine for document comparison (Phase 1):
    1. Validates and retrieves authoritative chunks for Document A and Document B.
    2. Segments chunks into granular factual evidence statements without assuming chunk alignment.
    3. Performs semantic & lexical cross-document alignment using local embeddings and reranker.
    4. Deterministically detects additions, removals, modifications, and conflicts.
       - Enforces strict verification on numbers, units, dates, percentages, and contradictions.
    5. Captures granular source attribution (document_id, chunk_id, chunk_index) for every difference.
    6. Calls Gemini 2.5 Flash with strict anti-prompt-injection isolation to synthesize an explanation.
    7. Seamlessly degrades to deterministic heuristic fallback when Gemini is offline or unconfigured.
    8. Produces structured, frontend-ready ComparisonResponse with GroundingMetadata.
    """

    def __init__(
        self,
        embedder: BaseEmbeddingService = embedding_service,
        rerank_service: RetrievalReranker = reranker,
        grounding: GroundingService = grounding_service,
        llm: LLMService = llm_service,
        retrieval: RetrievalService = retrieval_service
    ):
        self.embedding_service = embedder
        self.reranker = rerank_service
        self.grounding_service = grounding
        self.llm_service = llm
        self.retrieval_service = retrieval

    def _extract_statements(
        self,
        chunks: List[DocumentChunk],
        doc: Document
    ) -> List[EvidenceStatement]:
        """
        Segments document chunks into granular factual statements.
        Handles multi-sentence text, lists, and key-value lines while tracking originating chunk IDs.
        """
        statements: List[EvidenceStatement] = []
        seen_texts: Set[str] = set()
        stmt_idx = 0

        for chunk in chunks:
            raw_text = (chunk.text or "").strip()
            if not raw_text:
                continue

            # First attempt claim extraction
            claims = self.grounding_service.extract_claims(raw_text)

            # If claims extraction yielded nothing or missed short lines (e.g. key-value pairs)
            if not claims:
                lines = [line.strip() for line in re.split(r"(?<=[.!?])\s+|\n+", raw_text)]
                claims = [
                    re.sub(r"^(?:[-*•]|\d+\.)\s*", "", line).strip()
                    for line in lines
                    if len(line.strip()) >= 5 and not line.strip().startswith("#")
                ]

            for s in claims:
                s_clean = s.strip()
                if not s_clean or len(s_clean) < 6:
                    continue

                # Remove inline citation tags if any
                s_clean = re.sub(r"\[Source\s*\d+\]", "", s_clean).strip()
                s_lower = s_clean.lower()

                if s_lower in seen_texts:
                    continue
                seen_texts.add(s_lower)

                tokens = set(self.reranker.tokenize(s_clean))
                numeric_entities = self.grounding_service.extract_numeric_entities(s_clean)

                stmt_idx += 1
                statements.append(EvidenceStatement(
                    id=f"{doc.id}-stmt-{stmt_idx}",
                    document_id=doc.id,
                    document_name=doc.name,
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    chunk_text=raw_text,
                    text=s_clean,
                    clean_lower=s_lower,
                    tokens=tokens,
                    numeric_entities=numeric_entities
                ))

        return statements

    def _detect_numeric_or_antonym_conflict(
        self,
        stmt_a: EvidenceStatement,
        stmt_b: EvidenceStatement,
        cosine_sim: float
    ) -> Optional[Tuple[str, str, str]]:
        """
        Determines if two statements represent a conflict (materially incompatible claim):
        Returns (conflict_type, topic, explanation) or None if not conflicting.
        """
        tokens_a = stmt_a.tokens
        tokens_b = stmt_b.tokens
        shared_tokens = tokens_a & tokens_b

        # A. Semantic antonym / polarity collision
        for set1, set2 in CONTRADICTION_PAIRS:
            a_has_1 = bool(tokens_a & set1)
            a_has_2 = bool(tokens_a & set2)
            b_has_1 = bool(tokens_b & set1)
            b_has_2 = bool(tokens_b & set2)

            if (a_has_1 and b_has_2) or (a_has_2 and b_has_1):
                # Ensure they share the topical subject
                non_contrast_shared = shared_tokens - (set1 | set2)
                if len(non_contrast_shared) >= 1 or cosine_sim >= 0.55:
                    topic = extract_topic_from_text(stmt_a.text, non_contrast_shared)
                    term_a = list(tokens_a & (set1 | set2))[0]
                    term_b = list(tokens_b & (set1 | set2))[0]
                    expl = f"Document A asserts '{term_a}' whereas Document B asserts '{term_b}'."
                    return ("contradiction", topic, expl)

        # B. Numeric / Date / Percentage entity difference
        ents_a = stmt_a.numeric_entities
        ents_b = stmt_b.numeric_entities

        if ents_a and ents_b:
            for ea in ents_a:
                for eb in ents_b:
                    fam_a = get_unit_family(ea.unit)
                    fam_b = get_unit_family(eb.unit)

                    same_family = False
                    if fam_a and fam_b and fam_a == fam_b:
                        same_family = True
                    elif fam_a is None and fam_b is None:
                        # Unitless numbers with shared attributes or strong topical overlap
                        if bool(ea.attribute_tokens & eb.attribute_tokens) or cosine_sim >= 0.50:
                            same_family = True

                    value_changed = (ea.value != eb.value) or (
                        ea.unit and eb.unit and canonical_unit(ea.unit) != canonical_unit(eb.unit)
                    )

                    if same_family and value_changed:
                        # Shared context check: both describe the same metric
                        shared_attr = ea.attribute_tokens & eb.attribute_tokens
                        topical_overlap = shared_tokens - {"data", "system", "default", "value", "set", "number"}

                        if len(shared_attr) >= 1 or len(topical_overlap) >= 1 or cosine_sim >= 0.45:
                            # Avoid conflicting mutually exclusive attributes within same document
                            is_different_metric = False
                            for excl in EXCLUSIVE_METRIC_ATTRIBUTES:
                                a_excl = ea.attribute_tokens & excl
                                b_excl = eb.attribute_tokens & excl
                                if a_excl and b_excl and not (a_excl & b_excl):
                                    is_different_metric = True
                                    break

                            if not is_different_metric:
                                topic = extract_topic_from_text(stmt_a.text, shared_attr or topical_overlap)
                                unit_a = f" {ea.unit}" if ea.unit and ea.unit != "date" else ""
                                unit_b = f" {eb.unit}" if eb.unit and eb.unit != "date" else ""
                                expl = f"Value changed from {ea.value}{unit_a} in Document A to {eb.value}{unit_b} in Document B."
                                return ("numeric", topic, expl)

        return None

    def _to_source_chunk(self, stmt: EvidenceStatement) -> SourceChunk:
        """Converts an EvidenceStatement into a SourceChunk schema model."""
        return SourceChunk(
            document_id=stmt.document_id,
            document_name=stmt.document_name,
            chunk_id=stmt.chunk_id,
            chunk_index=stmt.chunk_index,
            page_number=stmt.page_number,
            score=1.0,
            text=stmt.chunk_text
        )

    def compare_documents(
        self,
        db: Session,
        document_a_id: str,
        document_b_id: str,
        focus: Optional[str] = None
    ) -> ComparisonResponse:
        """
        Executes end-to-end evidence-based document comparison:
        1. Validates document existence and non-identity.
        2. Retrieves chunks from SQLite.
        3. Segments chunks into factual evidence statements.
        4. Aligns statements semantically and lexically.
        5. Deterministically detects additions, removals, modifications, and conflicts.
        6. Constructs GroundingMetadata.
        7. Invokes Gemini (or fallback) for executive explanation.
        8. Returns structured ComparisonResponse.
        """
        # 1. Validation
        if not document_a_id or not document_b_id:
            raise ValueError("Both document_a_id and document_b_id must be provided.")

        clean_a_id = document_a_id.strip()
        clean_b_id = document_b_id.strip()

        if clean_a_id == clean_b_id:
            raise ValueError("Document A and Document B must be different documents.")

        doc_a = db.query(Document).filter(Document.id == clean_a_id).first()
        if not doc_a:
            raise DocumentNotFoundError(f"Document with ID '{clean_a_id}' was not found.")

        doc_b = db.query(Document).filter(Document.id == clean_b_id).first()
        if not doc_b:
            raise DocumentNotFoundError(f"Document with ID '{clean_b_id}' was not found.")

        # 2. Retrieve chunks
        chunks_a = ChunkService.get_chunks_by_document_id(db, clean_a_id)
        chunks_b = ChunkService.get_chunks_by_document_id(db, clean_b_id)

        # Check for usable content
        has_text_a = any(bool(c.text and c.text.strip()) for c in chunks_a)
        has_text_b = any(bool(c.text and c.text.strip()) for c in chunks_b)

        if not chunks_a or not has_text_a:
            raise ValueError(f"Document '{doc_a.name}' contains no usable indexed content.")
        if not chunks_b or not has_text_b:
            raise ValueError(f"Document '{doc_b.name}' contains no usable indexed content.")

        # 3. Extract evidence statements
        stmts_a = self._extract_statements(chunks_a, doc_a)
        stmts_b = self._extract_statements(chunks_b, doc_b)

        if not stmts_a or not stmts_b:
            raise ValueError("Could not extract meaningful factual evidence from one or both documents.")

        # 4. Semantic embeddings
        texts_a = [s.text for s in stmts_a]
        texts_b = [s.text for s in stmts_b]

        embeddings_a = self.embedding_service.embed_texts(texts_a)
        embeddings_b = self.embedding_service.embed_texts(texts_b)

        # Cosine similarity matrix: shape (len(stmts_a), len(stmts_b))
        sim_matrix = np.dot(embeddings_a, embeddings_b.T)

        # 5. Deterministic alignment & classification
        matched_a_indices: Set[int] = set()
        matched_b_indices: Set[int] = set()

        common_items: List[CommonItem] = []
        conflict_items: List[ConflictItem] = []
        modification_items: List[ModificationItem] = []
        addition_items: List[AdditionItem] = []
        removal_items: List[RemovalItem] = []

        item_counter = 0

        # Step A: Exact matches (100% identical normalized content)
        for i, sa in enumerate(stmts_a):
            for j, sb in enumerate(stmts_b):
                if j in matched_b_indices:
                    continue
                if sa.clean_lower == sb.clean_lower:
                    matched_a_indices.add(i)
                    matched_b_indices.add(j)
                    item_counter += 1
                    src_a = [self._to_source_chunk(sa)]
                    src_b = [self._to_source_chunk(sb)]
                    common_items.append(CommonItem(
                        id=f"com-{item_counter}",
                        topic=extract_topic_from_text(sa.text, sa.tokens),
                        content=sa.text,
                        explanation="Identical content present in both documents.",
                        sources_a=src_a,
                        sources_b=src_b
                    ))
                    break

        # Assemble candidate pairs for non-exact matches sorted by similarity descending
        candidate_pairs: List[Tuple[float, int, int]] = []
        for i, sa in enumerate(stmts_a):
            if i in matched_a_indices:
                continue
            for j, sb in enumerate(stmts_b):
                if j in matched_b_indices:
                    continue
                score = float(sim_matrix[i, j])
                shared = sa.tokens & sb.tokens
                if score >= 0.40 or len(shared) >= 1:
                    candidate_pairs.append((score, i, j))

        candidate_pairs.sort(key=lambda x: -x[0])

        # Step B: Detect CONFLICTS on candidate pairs
        for score, i, j in candidate_pairs:
            if i in matched_a_indices or j in matched_b_indices:
                continue

            sa = stmts_a[i]
            sb = stmts_b[j]

            conflict_info = self._detect_numeric_or_antonym_conflict(sa, sb, score)
            if conflict_info:
                conf_type, topic, expl = conflict_info
                matched_a_indices.add(i)
                matched_b_indices.add(j)
                item_counter += 1
                src_a = [self._to_source_chunk(sa)]
                src_b = [self._to_source_chunk(sb)]

                conf_item = ConflictItem(
                    id=f"conf-{item_counter}",
                    topic=topic,
                    document_a=sa.text,
                    document_b=sb.text,
                    explanation=expl,
                    sources_a=src_a,
                    sources_b=src_b
                )
                conflict_items.append(conf_item)

                # Also surface under modifications so value changes are visible in both views
                modification_items.append(ModificationItem(
                    id=f"mod-{item_counter}",
                    topic=topic,
                    document_a=sa.text,
                    document_b=sb.text,
                    explanation=expl,
                    sources_a=src_a,
                    sources_b=src_b
                ))

        # Step C: Near-identical matches (high semantic score, NO conflict, identical numbers/entities if any)
        for score, i, j in candidate_pairs:
            if i in matched_a_indices or j in matched_b_indices:
                continue

            sa = stmts_a[i]
            sb = stmts_b[j]
            jaccard = len(sa.tokens & sb.tokens) / max(len(sa.tokens | sb.tokens), 1)

            if score >= 0.88 and jaccard >= 0.60:
                ents_match = True
                if sa.numeric_entities or sb.numeric_entities:
                    if len(sa.numeric_entities) != len(sb.numeric_entities):
                        ents_match = False
                    else:
                        ents_match = all(
                            any(ea.matches(eb) for eb in sb.numeric_entities)
                            for ea in sa.numeric_entities
                        )

                if ents_match:
                    matched_a_indices.add(i)
                    matched_b_indices.add(j)
                    item_counter += 1
                    src_a = [self._to_source_chunk(sa)]
                    src_b = [self._to_source_chunk(sb)]
                    common_items.append(CommonItem(
                        id=f"com-{item_counter}",
                        topic=extract_topic_from_text(sa.text, sa.tokens & sb.tokens),
                        content=sa.text,
                        explanation="Near-identical information expressed in both documents.",
                        sources_a=src_a,
                        sources_b=src_b
                    ))

        # Step D: General modifications (topical similarity score >= 0.62)
        for score, i, j in candidate_pairs:
            if i in matched_a_indices or j in matched_b_indices:
                continue

            if score >= 0.62:
                sa = stmts_a[i]
                sb = stmts_b[j]
                matched_a_indices.add(i)
                matched_b_indices.add(j)
                item_counter += 1
                src_a = [self._to_source_chunk(sa)]
                src_b = [self._to_source_chunk(sb)]
                topic = extract_topic_from_text(sa.text, sa.tokens & sb.tokens)

                modification_items.append(ModificationItem(
                    id=f"mod-{item_counter}",
                    topic=topic,
                    document_a=sa.text,
                    document_b=sb.text,
                    explanation="Topic present in both documents with updated wording or scope.",
                    sources_a=src_a,
                    sources_b=src_b
                ))


        # Step D: Unmatched statements in Document B -> ADDITIONS
        for j, sb in enumerate(stmts_b):
            if j not in matched_b_indices:
                item_counter += 1
                src_b = [self._to_source_chunk(sb)]
                topic = extract_topic_from_text(sb.text, sb.tokens)
                addition_items.append(AdditionItem(
                    id=f"add-{item_counter}",
                    topic=topic,
                    content=sb.text,
                    explanation=f"New information introduced in '{doc_b.name}'.",
                    sources_b=src_b,
                    sources=src_b
                ))

        # Step E: Unmatched statements in Document A -> REMOVALS
        for i, sa in enumerate(stmts_a):
            if i not in matched_a_indices:
                item_counter += 1
                src_a = [self._to_source_chunk(sa)]
                topic = extract_topic_from_text(sa.text, sa.tokens)
                removal_items.append(RemovalItem(
                    id=f"rem-{item_counter}",
                    topic=topic,
                    content=sa.text,
                    explanation=f"Information from '{doc_a.name}' omitted in '{doc_b.name}'.",
                    sources_a=src_a,
                    sources=src_a
                ))

        # 6. Aggregate unique sources
        all_sources_dict: Dict[str, SourceChunk] = {}
        for item in common_items:
            for s in item.sources_a + item.sources_b:
                all_sources_dict[s.chunk_id] = s
        for item in conflict_items:
            for s in item.sources_a + item.sources_b:
                all_sources_dict[s.chunk_id] = s
        for item in modification_items:
            for s in item.sources_a + item.sources_b:
                all_sources_dict[s.chunk_id] = s
        for item in addition_items:
            for s in item.sources_b:
                all_sources_dict[s.chunk_id] = s
        for item in removal_items:
            for s in item.sources_a:
                all_sources_dict[s.chunk_id] = s

        all_sources = list(all_sources_dict.values())
        all_chunk_ids = list(all_sources_dict.keys())

        # 7. Grounding evaluation
        if conflict_items:
            status = GroundingStatus.CONFLICTING_EVIDENCE
            confidence = 0.85
        elif not addition_items and not removal_items and not modification_items:
            status = GroundingStatus.SUPPORTED
            confidence = 1.0
        else:
            status = GroundingStatus.SUPPORTED
            confidence = 0.95

        supported_claims = (
            [f"Added: {a.content}" for a in addition_items[:10]] +
            [f"Removed: {r.content}" for r in removal_items[:10]] +
            [f"Modified: {m.topic}" for m in modification_items[:10]]
        )

        conflicts_list = [
            f"Conflict on '{c.topic}': '{c.document_a}' vs '{c.document_b}'"
            for c in conflict_items
        ] if conflict_items else None

        grounding_eval = GroundingEvaluation(
            status=status,
            confidence=confidence,
            supported_claims=supported_claims,
            unsupported_claims=[],
            source_chunk_ids=all_chunk_ids,
            conflicts=conflicts_list
        )

        # 8. Synthesize explanation via LLM (Gemini or heuristic fallback)
        diff_data = {
            "additions": [{"topic": a.topic, "content": a.content} for a in addition_items],
            "removals": [{"topic": r.topic, "content": r.content} for r in removal_items],
            "modifications": [{"topic": m.topic, "document_a": m.document_a, "document_b": m.document_b, "explanation": m.explanation} for m in modification_items],
            "conflicts": [{"topic": c.topic, "document_a": c.document_a, "document_b": c.document_b, "explanation": c.explanation} for c in conflict_items],
            "common": [{"topic": cm.topic, "content": cm.content} for cm in common_items]
        }

        explanation_result = self.llm_service.explain_comparison(
            doc_a_name=doc_a.name,
            doc_b_name=doc_b.name,
            differences_data=diff_data
        )

        # 9. Return structured response
        return ComparisonResponse(
            document_a=DocumentInfo(
                id=doc_a.id,
                name=doc_a.name,
                category=doc_a.category or "General",
                chunk_count=len(chunks_a)
            ),
            document_b=DocumentInfo(
                id=doc_b.id,
                name=doc_b.name,
                category=doc_b.category or "General",
                chunk_count=len(chunks_b)
            ),
            summary=str(explanation_result),
            additions=addition_items,
            removals=removal_items,
            modifications=modification_items,
            conflicts=conflict_items,
            common=common_items,
            sources=all_sources,
            grounding=GroundingMetadata(**grounding_eval.to_dict()),
            provider=getattr(explanation_result, "provider", "heuristic_fallback"),
            model=getattr(explanation_result, "model", "extractive-rules")
        )


comparison_service = ComparisonService()
