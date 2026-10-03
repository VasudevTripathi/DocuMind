import re
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

from app.services.reranker import reranker

logger = logging.getLogger("documind.grounding")

class GroundingStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"

# Unit equivalence mappings (normalized singular lowercase)
UNIT_EQUIVALENCES: Dict[str, Set[str]] = {
    "millisecond": {"ms", "millisecond", "milliseconds"},
    "second": {"s", "sec", "secs", "second", "seconds"},
    "minute": {"m", "min", "mins", "minute", "minutes"},
    "hour": {"h", "hr", "hrs", "hour", "hours"},
    "day": {"d", "day", "days"},
    "week": {"wk", "week", "weeks"},
    "month": {"mo", "month", "months"},
    "year": {"yr", "yrs", "year", "years"},
    "percent": {"%", "pct", "percent", "percentage"},
    "byte": {"b", "byte", "bytes"},
    "kilobyte": {"kb", "kilobyte", "kilobytes"},
    "megabyte": {"mb", "megabyte", "megabytes"},
    "gigabyte": {"gb", "gigabyte", "gigabytes"}
}

def canonical_unit(unit: str) -> str:
    unit_clean = unit.lower().strip()
    for canon, aliases in UNIT_EQUIVALENCES.items():
        if unit_clean in aliases:
            return canon
    return unit_clean

@dataclass
class NumericEntity:
    value: str
    unit: Optional[str] = None
    raw: str = ""
    context_tokens: Set[str] = field(default_factory=set)

    def matches(self, other: "NumericEntity") -> bool:
        if self.value != other.value:
            return False
        if self.unit is None or other.unit is None:
            return True
        return canonical_unit(self.unit) == canonical_unit(other.unit)

@dataclass
class ClaimVerificationResult:
    claim_text: str
    is_supported: bool
    matched_chunk_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    numeric_consistent: bool = True
    reason: Optional[str] = None

@dataclass
class GroundingEvaluation:
    status: GroundingStatus
    confidence: float
    supported_claims: List[str]
    unsupported_claims: List[str]
    source_chunk_ids: List[str]
    conflicts: Optional[List[str]] = None
    claim_verifications: List[ClaimVerificationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "status": self.status.value,
            "confidence": round(self.confidence, 2),
            "supported_claims": self.supported_claims,
            "unsupported_claims": self.unsupported_claims,
            "source_chunk_ids": self.source_chunk_ids,
        }
        if self.conflicts:
            data["conflicts"] = self.conflicts
        return data

class GroundingService:
    """
    Deterministic, CPU-friendly verification service:
    1. Extracts individual factual claims from an answer.
    2. Identifies numeric and entity factual specifications.
    3. Verifies claims against retrieved evidence chunks.
    4. Detects numeric inconsistencies and contradictions.
    5. Detects conflicting evidence between retrieved chunks.
    6. Produces deterministic GroundingEvaluation with status and confidence.
    """

    def __init__(self):
        self.reranker = reranker

    def extract_claims(self, text: str) -> List[str]:
        """
        Extracts sentence-level claims from an answer.
        Filters conversational filler, empty lines, and refusal strings.
        """
        if not text or not text.strip():
            return []

        raw_text = text.strip()
        # Exclude standard no-context fallback
        if "could not be found in the provided documents" in raw_text.lower():
            return []

        # Split into sentences on sentence terminators while preserving words
        raw_sentences = re.split(r"(?<=[.!?])\s+", raw_text)
        claims: List[str] = []

        ignore_prefixes = (
            "sure", "here is", "based on", "according to", "in summary",
            "hello", "hi", "note that", "please note"
        )

        for s in raw_sentences:
            s_clean = s.strip()
            # Remove markdown citations like [Source 1] from claim text for verification
            s_clean = re.sub(r"\[Source\s*\d+\]", "", s_clean).strip()
            if not s_clean or len(s_clean) < 10:
                continue

            lower_s = s_clean.lower()
            # If sentence is purely a greeting or conversational introductory clause
            if any(lower_s.startswith(p) for p in ignore_prefixes) and len(s_clean.split()) <= 4:
                continue

            claims.append(s_clean)

        return claims

    def extract_numeric_entities(self, text: str) -> List[NumericEntity]:
        """
        Extracts numeric values with attached or adjacent units.
        Recognizes integers, decimals, percentages, and temporal/storage units.
        """
        if not text:
            return []

        pattern = re.compile(
            r"\b(\d+(?:\.\d+)?)\s*(ms|milliseconds?|s|sec|secs|seconds?|m|min|mins|minutes?|"
            r"h|hr|hrs|hours?|d|day|days|wk|weeks?|mo|months?|yr|yrs|years?|%|percent|percentage|"
            r"kb|mb|gb|bytes?)\b",
            re.IGNORECASE
        )

        entities: List[NumericEntity] = []
        spans: List[Tuple[int, int]] = []

        # 1. Match numbers with explicit units
        for m in pattern.finditer(text):
            val, unit = m.group(1), m.group(2)
            start, end = m.span()
            window = text[max(0, start - 60):min(len(text), end + 60)]
            w_tokens = set(self.reranker.tokenize(window))
            ctx_tokens = {t for t in w_tokens if not t.isdigit() and len(t) > 2}
            entities.append(NumericEntity(value=val, unit=unit, raw=m.group(0), context_tokens=ctx_tokens))
            spans.append((start, end))

        # 2. Match standalone numbers not part of units
        standalone_pattern = re.compile(r"\b(\d+(?:\.\d+)?)\b")
        for m in standalone_pattern.finditer(text):
            start, end = m.span()
            if any(s_start <= start and end <= s_end for s_start, s_end in spans):
                continue
            window = text[max(0, start - 60):min(len(text), end + 60)]
            w_tokens = set(self.reranker.tokenize(window))
            ctx_tokens = {t for t in w_tokens if not t.isdigit() and len(t) > 2}
            entities.append(NumericEntity(value=m.group(1), unit=None, raw=m.group(0), context_tokens=ctx_tokens))

        return entities

    def check_numeric_consistency(
        self,
        claim_entities: List[NumericEntity],
        evidence_entities: List[NumericEntity]
    ) -> bool:
        """
        Verifies that every numeric entity asserted in a claim is compatible
        with at least one numeric entity present in the evidence chunk.
        """
        if not claim_entities:
            return True
        if not evidence_entities:
            # Claim has numbers, but evidence chunk has none
            return False

        for c_ent in claim_entities:
            matched = any(c_ent.matches(e_ent) for e_ent in evidence_entities)
            if not matched:
                return False
        return True

    def detect_evidence_conflicts(
        self,
        query: str,
        evidence_chunks: List[Dict[str, Any]]
    ) -> Optional[List[str]]:
        """
        Detects contradictory factual values across top retrieved chunks.
        e.g., Chunk 1: 'retention is 7 years', Chunk 2: 'retention is 10 years'.
        Requires that the conflicting entities share contextual terms that align with the query.
        """
        if len(evidence_chunks) < 2:
            return None

        # Extract entities per chunk along with topic words
        q_tokens = set(self.reranker.tokenize(query))
        chunk_facts: List[Tuple[str, List[NumericEntity]]] = []

        for c in evidence_chunks:
            text = c.get("text", "")
            tokens = set(self.reranker.tokenize(text))
            # Only consider chunks that actively match the query topic
            if len(q_tokens & tokens) >= 1:
                entities = self.extract_numeric_entities(text)
                if entities:
                    chunk_facts.append((c.get("chunk_id", ""), entities))

        if len(chunk_facts) < 2:
            return None

        # Check for conflicting entities sharing the same canonical unit and query context
        conflicts: List[str] = []
        for i in range(len(chunk_facts)):
            cid_a, ents_a = chunk_facts[i]
            for j in range(i + 1, len(chunk_facts)):
                cid_b, ents_b = chunk_facts[j]
                if cid_a == cid_b:
                    continue
                for ea in ents_a:
                    for eb in ents_b:
                        same_unit = False
                        if ea.unit and eb.unit and canonical_unit(ea.unit) == canonical_unit(eb.unit):
                            same_unit = True
                        elif ea.unit is None and eb.unit is None:
                            same_unit = True

                        if same_unit and ea.value != eb.value:
                            shared_ctx = ea.context_tokens & eb.context_tokens
                            shared_with_query = shared_ctx & q_tokens
                            if shared_with_query:
                                unit_str_a = f" {ea.unit}" if ea.unit else ""
                                unit_str_b = f" {eb.unit}" if eb.unit else ""
                                msg = (
                                    f"Conflict between {cid_a} ({ea.value}{unit_str_a}) "
                                    f"and {cid_b} ({eb.value}{unit_str_b})"
                                )
                                if msg not in conflicts:
                                    conflicts.append(msg)

        return conflicts if conflicts else None

    def verify_answer(
        self,
        query: str,
        answer: str,
        evidence_chunks: List[Dict[str, Any]]
    ) -> GroundingEvaluation:
        """
        Performs holistic deterministic grounding verification.
        """
        cleaned_answer = (answer or "").strip()

        # 1. Check for empty or no-context response
        if not cleaned_answer or "could not be found in the provided documents" in cleaned_answer.lower():
            return GroundingEvaluation(
                status=GroundingStatus.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                supported_claims=[],
                unsupported_claims=[],
                source_chunk_ids=[]
            )

        if not evidence_chunks:
            return GroundingEvaluation(
                status=GroundingStatus.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                supported_claims=[],
                unsupported_claims=self.extract_claims(cleaned_answer),
                source_chunk_ids=[]
            )

        # 2. Detect conflicting evidence across retrieved chunks
        conflicts = self.detect_evidence_conflicts(query, evidence_chunks)
        if conflicts:
            conflicting_chunk_ids = [c.get("chunk_id") for c in evidence_chunks if c.get("chunk_id")]
            return GroundingEvaluation(
                status=GroundingStatus.CONFLICTING_EVIDENCE,
                confidence=0.30,
                supported_claims=[],
                unsupported_claims=self.extract_claims(cleaned_answer),
                source_chunk_ids=conflicting_chunk_ids,
                conflicts=conflicts
            )

        # 3. Extract claims from the answer
        claims = self.extract_claims(cleaned_answer)
        if not claims:
            return GroundingEvaluation(
                status=GroundingStatus.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                supported_claims=[],
                unsupported_claims=[],
                source_chunk_ids=[]
            )

        supported_claims: List[str] = []
        unsupported_claims: List[str] = []
        actively_used_chunk_ids: Set[str] = set()
        verifications: List[ClaimVerificationResult] = []

        # Pre-extract evidence entities and tokens
        parsed_evidence = []
        for c in evidence_chunks:
            c_text = c.get("text", "")
            cid = c.get("chunk_id", "")
            c_score = float(c.get("score") or c.get("similarity_score", 0.0))
            parsed_evidence.append({
                "chunk_id": cid,
                "text": c_text,
                "tokens": set(self.reranker.tokenize(c_text)),
                "entities": self.extract_numeric_entities(c_text),
                "score": c_score
            })

        for claim in claims:
            claim_tokens = self.reranker.tokenize(claim)
            claim_entities = self.extract_numeric_entities(claim)

            best_chunk_id: Optional[str] = None
            best_chunk_score: float = 0.0
            claim_supported = False
            numeric_ok = True

            claim_stems = set(canonical_unit(t) for t in claim_tokens)
            for ev in parsed_evidence:
                # 1. Lexical and stem overlap ratio
                token_overlap = (
                    len(set(claim_tokens) & ev["tokens"]) / len(set(claim_tokens))
                    if claim_tokens else 0.0
                )
                ev_stems = set(canonical_unit(t) for t in ev["tokens"])
                stem_overlap = (
                    len(claim_stems & ev_stems) / len(claim_stems)
                    if claim_stems else 0.0
                )
                effective_overlap = max(token_overlap, stem_overlap)

                # 2. Phrase matching score
                phrase_overlap = self.reranker.compute_phrase_score(claim, ev["text"])

                # 3. Numeric consistency check
                num_consistent = self.check_numeric_consistency(claim_entities, ev["entities"])

                # Combined support criteria:
                # Meaningful lexical/stem overlap (>= 0.30) or phrase overlap (>= 0.30)
                # AND numeric consistency must hold if numbers are asserted
                if (effective_overlap >= 0.30 or phrase_overlap >= 0.30):
                    if num_consistent:
                        claim_supported = True
                        if ev["score"] > best_chunk_score:
                            best_chunk_score = ev["score"]
                            best_chunk_id = ev["chunk_id"]
                    else:
                        numeric_ok = False

            if claim_supported and best_chunk_id:
                supported_claims.append(claim)
                actively_used_chunk_ids.add(best_chunk_id)
                verifications.append(ClaimVerificationResult(
                    claim_text=claim,
                    is_supported=True,
                    matched_chunk_ids=[best_chunk_id],
                    confidence=best_chunk_score,
                    numeric_consistent=True
                ))
            else:
                unsupported_claims.append(claim)
                verifications.append(ClaimVerificationResult(
                    claim_text=claim,
                    is_supported=False,
                    matched_chunk_ids=[],
                    confidence=0.0,
                    numeric_consistent=numeric_ok,
                    reason="Numeric mismatch" if not numeric_ok else "Insufficient lexical/phrase overlap"
                ))

        # 4. Determine overall GroundingStatus
        total_claims = len(claims)
        supported_count = len(supported_claims)

        if supported_count == total_claims and total_claims > 0:
            status = GroundingStatus.SUPPORTED
        elif supported_count > 0:
            status = GroundingStatus.PARTIALLY_SUPPORTED
        else:
            status = GroundingStatus.INSUFFICIENT_EVIDENCE

        # 5. Deterministic confidence calculation
        top_score = max((ev["score"] for ev in parsed_evidence), default=0.5)
        top_score = min(1.0, max(0.0, top_score))

        if status == GroundingStatus.SUPPORTED:
            # High confidence based on top evidence score and complete support
            raw_conf = 0.50 + (0.35 * top_score) + 0.15
            confidence = min(0.99, max(0.60, raw_conf))
        elif status == GroundingStatus.PARTIALLY_SUPPORTED:
            # Scaled down proportionally by fraction of supported claims
            ratio = supported_count / total_claims
            confidence = min(0.75, max(0.30, ratio * top_score))
        else:
            confidence = 0.0

        # Sort actively used source chunks by original evidence order
        ordered_source_ids = [
            ev["chunk_id"] for ev in parsed_evidence
            if ev["chunk_id"] in actively_used_chunk_ids
        ]
        # If no specific chunk was isolated but answer was supported (e.g. general), include top evidence chunk
        if status == GroundingStatus.SUPPORTED and not ordered_source_ids and parsed_evidence:
            ordered_source_ids = [parsed_evidence[0]["chunk_id"]]

        return GroundingEvaluation(
            status=status,
            confidence=round(confidence, 2),
            supported_claims=supported_claims,
            unsupported_claims=unsupported_claims,
            source_chunk_ids=ordered_source_ids,
            claim_verifications=verifications
        )

grounding_service = GroundingService()
