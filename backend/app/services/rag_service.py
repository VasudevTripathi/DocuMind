import logging
import re
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.services.retrieval_service import retrieval_service, RetrievalService, DocumentNotFoundError
from app.services.llm_service import llm_service, LLMService
from app.services.grounding_service import grounding_service, GroundingService, GroundingStatus, GroundingEvaluation

logger = logging.getLogger("documind.rag")

NO_CONTEXT_FALLBACK = "The answer could not be found in the provided documents."

def select_context_chunks(
    chunks: List[Dict[str, Any]],
    max_context_words: Optional[int] = None,
    min_similarity: float = 0.10,
    max_overlap_ratio: float = 0.65
) -> List[Dict[str, Any]]:
    """
    Selects the smallest sufficient, high-quality, non-redundant set of document chunks
    to fit within a strict context budget (Part 7, Part 8, Part 9, Part 11).

    Pipeline:
    1. Relevance filtering: Discards chunks below min_similarity.
    2. Sorts candidates by quality (rerank_score descending, semantic_score descending).
    3. MMR-like redundancy minimization: Prunes overlapping chunks (> 65% token Jaccard overlap).
    4. Hard context budget: Accumulates words up to max_context_words; stops once budget is met.
    """
    if not chunks:
        return []

    budget = max_context_words if max_context_words is not None else getattr(settings, "RAG_MAX_CONTEXT_WORDS", 2500)

    # 1. Relevance thresholding: chunk must have meaningful semantic or lexical relevance
    relevant_candidates = []
    for c in chunks:
        sem_score = float(c.get("semantic_score") or c.get("similarity_score") or c.get("score") or 0.0)
        lex_score = float(c.get("lexical_score", 0.0))
        rerank_sc = float(c.get("rerank_score") or c.get("score") or 0.0)

        # If explicit semantic score is present and is below min_similarity with 0 lexical overlap, drop
        explicit_sem = c.get("semantic_score") if c.get("semantic_score") is not None else c.get("similarity_score")
        if explicit_sem is not None and float(explicit_sem) < min_similarity and lex_score == 0.0:
            continue

        # If general score is below min_similarity, drop
        if max(sem_score, rerank_sc) < min_similarity:
            continue

        relevant_candidates.append(c)

    if not relevant_candidates:
        return []

    # 2. Sort by best rerank / semantic score
    sorted_candidates = sorted(
        relevant_candidates,
        key=lambda x: (
            -float(x.get("rerank_score", x.get("score", 0.0))),
            -float(x.get("semantic_score", x.get("similarity_score", 0.0))),
            x.get("chunk_index", 0)
        )
    )

    selected: List[Dict[str, Any]] = []
    selected_token_sets: List[Set[str]] = []
    total_words = 0

    for cand in sorted_candidates:
        cand_text = (cand.get("text") or "").strip()
        cand_words = len(cand_text.split())
        if cand_words == 0:
            continue

        cand_tokens = set(re.findall(r"\b\w{3,}\b", cand_text.lower()))

        # 3. MMR-like redundancy check: containment ratio against already selected chunks from same document
        is_redundant = False
        cand_doc_id = cand.get("document_id")
        cand_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", cand_text))

        for sel, sel_tokens in zip(selected, selected_token_sets):
            if sel.get("document_id") == cand_doc_id and cand_tokens and sel_tokens:
                sel_text = (sel.get("text") or "").strip()
                sel_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", sel_text))
                # Distinct numeric entities (e.g. 7 years vs 10 years) carry crucial distinct facts/conflicts
                if cand_nums != sel_nums:
                    continue

                intersection = len(cand_tokens & sel_tokens)
                containment = intersection / max(1, min(len(cand_tokens), len(sel_tokens)))
                if containment > max_overlap_ratio:
                    is_redundant = True
                    break

        if is_redundant:
            continue

        # 4. Hard context budget check
        if selected and (total_words + cand_words > budget):
            # Budget exceeded and we already have at least one top evidence chunk
            break

        selected.append(cand)
        selected_token_sets.append(cand_tokens)
        total_words += cand_words

        if total_words >= budget:
            break

    return selected

def format_grounded_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks into clear, structured context sections with source identifiers.
    """
    sections = []
    for i, c in enumerate(chunks, start=1):
        doc_name = c.get("document_name") or c.get("document_id") or "Unknown Document"
        chunk_idx = c.get("chunk_index", 0)
        chunk_id = c.get("chunk_id", "")
        score = c.get("score") or c.get("similarity_score", 0.0)
        text = (c.get("text") or "").strip()

        sections.append(
            f"[Source {i}]\n"
            f"Document: {doc_name}\n"
            f"Chunk ID: {chunk_id}\n"
            f"Chunk Index: {chunk_idx}\n"
            f"Relevance Score: {score:.4f}\n"
            f"Content:\n{text}"
        )
    return "\n\n".join(sections)

class RAGService:
    """
    Orchestrates the document-grounded question answering workflow (Phase 8.4):
    1. Validates query and document scoping.
    2. Calls RetrievalService to fetch candidate chunks.
    3. Selects relevant, diverse chunks respecting the hard context budget.
    4. Handles no-context scenarios safely without calling the LLM.
    5. Assembles grounded context with source citations.
    6. Invokes LLM service with dedicated grounding prompt.
    7. Verifies answer grounding and source attribution.
    8. Returns structured answer, source attribution, and deterministic grounding metadata.
    """

    def __init__(
        self,
        retrieval: RetrievalService = retrieval_service,
        llm: LLMService = llm_service,
        grounding: GroundingService = grounding_service
    ):
        self.retrieval_service = retrieval
        self.llm_service = llm
        self.grounding_service = grounding

    def answer_question(
        self,
        db: Session,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Answers a user question grounded strictly in retrieved document context.
        Raises ValueError if query is empty.
        Raises DocumentNotFoundError if document_id is provided but not found in the DB.
        """
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            raise ValueError("Query string cannot be empty.")

        # If document_id is supplied, verify it exists in DB
        if document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise DocumentNotFoundError(f"Document with ID '{document_id}' was not found.")

        # 1. Retrieve candidate chunks from RetrievalService
        candidate_k = max(getattr(settings, "RAG_CANDIDATE_K", 8), top_k)
        chunks = self.retrieval_service.search(
            db=db,
            query=cleaned_query,
            top_k=candidate_k,
            document_id=document_id
        )

        # 2. Select minimal sufficient context chunks (budget, relevance, diversity)
        usable_chunks = select_context_chunks(
            chunks=chunks,
            max_context_words=getattr(settings, "RAG_MAX_CONTEXT_WORDS", 2500),
            min_similarity=0.10
        )
        if len(usable_chunks) > top_k:
            usable_chunks = usable_chunks[:top_k]

        # 3. No-context guard: If no usable chunks retrieved or all evidence is irrelevant, do NOT call LLM
        q_tokens = set(self.grounding_service.reranker.tokenize(cleaned_query))
        has_any_overlap = any(
            bool(q_tokens & set(self.grounding_service.reranker.tokenize(c.get("text", ""))))
            for c in usable_chunks
        )
        top_semantic = max(
            (float(c.get("semantic_score", c.get("similarity_score", 0.0))) for c in usable_chunks),
            default=0.0
        )

        if not usable_chunks or (top_semantic < 0.12 and not has_any_overlap):
            logger.info(f"[RAGService] No usable or relevant chunks for query: '{cleaned_query[:40]}'. Returning safe fallback.")
            fallback_grounding = GroundingEvaluation(
                status=GroundingStatus.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                supported_claims=[],
                unsupported_claims=[],
                source_chunk_ids=[]
            )
            return {
                "query": cleaned_query,
                "answer": NO_CONTEXT_FALLBACK,
                "sources": [],
                "document_id": document_id,
                "grounding": fallback_grounding.to_dict(),
                "provider": "system_guard",
                "model": "no-context-abstention"
            }

        # 3. Assemble grounded context
        context_str = format_grounded_context(usable_chunks)

        # 4. Generate grounded answer via LLM
        logger.info(f"[RAGService] Invoking LLM answering with {len(usable_chunks)} context sources.")
        answer = self.llm_service.answer_question(
            question=cleaned_query,
            context=context_str
        )

        # 5. Evaluate answer grounding deterministically
        grounding_eval = self.grounding_service.verify_answer(
            query=cleaned_query,
            answer=answer,
            evidence_chunks=usable_chunks
        )

        # 6. Format sources and enforce abstention when answer is unsupported (Task 5)
        if (
            answer.strip() == NO_CONTEXT_FALLBACK
            or (grounding_eval.status == GroundingStatus.INSUFFICIENT_EVIDENCE and not grounding_eval.supported_claims)
        ):
            answer = NO_CONTEXT_FALLBACK
            sources = []
            grounding_eval.source_chunk_ids = []
        else:
            sources = [
                {
                    "document_id": c["document_id"],
                    "document_name": c.get("document_name"),
                    "chunk_id": c["chunk_id"],
                    "chunk_index": c["chunk_index"],
                    "page_number": c.get("page_number"),
                    "score": c.get("score") or c.get("similarity_score", 0.0),
                    "text": c.get("text"),
                    "semantic_score": c.get("semantic_score"),
                    "lexical_score": c.get("lexical_score"),
                    "phrase_score": c.get("phrase_score"),
                    "coverage_score": c.get("coverage_score"),
                    "context_score": c.get("context_score"),
                    "rerank_score": c.get("rerank_score"),
                    "score_breakdown": c.get("score_breakdown")
                }
                for c in usable_chunks
            ]

        return {
            "query": cleaned_query,
            "answer": str(answer),
            "sources": sources,
            "document_id": document_id,
            "grounding": grounding_eval.to_dict(),
            "provider": getattr(answer, "provider", "heuristic_fallback"),
            "model": getattr(answer, "model", "extractive-rules")
        }

rag_service = RAGService()
