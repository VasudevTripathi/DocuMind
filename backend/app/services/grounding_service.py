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
    "gigabyte": {"gb", "gigabyte", "gigabytes"},
    "terabyte": {"tb", "terabyte", "terabytes"},
    "date": {"date"}
}

def canonical_unit(unit: str) -> str:
    unit_clean = unit.lower().strip()
    for canon, aliases in UNIT_EQUIVALENCES.items():
        if unit_clean in aliases:
            return canon
    return unit_clean

# Common pairs of mutually exclusive metric qualifiers
EXCLUSIVE_METRIC_ATTRIBUTES = [
    {"interval", "timeout"},
    {"minimum", "maximum"},
    {"inbound", "outbound"},
    {"read", "write"},
    {"incremental", "full"},
    {"rto", "rpo"},
    {"connect", "read"}
]

@dataclass
class NumericEntity:
    value: str
    unit: Optional[str] = None
    raw: str = ""
    context_tokens: Set[str] = field(default_factory=set)
    attribute_tokens: Set[str] = field(default_factory=set)

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
    is_multi_chunk: bool = False
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
    1. Extracts individual factual claims from multi-sentence, bulleted, or list answers.
    2. Identifies numeric and entity factual specifications (units, storage, percentages, dates).
    3. Verifies claims against retrieved evidence chunks with single-chunk and multi-chunk support.
    4. Detects numeric inconsistencies and attribute contradictions.
    5. Detects conflicting evidence between retrieved chunks.
    6. Produces deterministic GroundingEvaluation with status and calibrated confidence.
    """

    def __init__(self):
        self.reranker = reranker

    def extract_claims(self, text: str) -> List[str]:
        """
        Extracts individual factual claims from an answer.
        Handles multi-sentence paragraphs, bullet points, numbered lists,
        and markdown headings while filtering conversational filler and refusal strings.
        """
        if not text or not text.strip():
            return []

        raw_text = text.strip()
        # Exclude standard no-context fallback
        if "could not be found in the provided documents" in raw_text.lower():
            return []

        # Split across lines first to respect bullet points, headings, and lists
        raw_lines = raw_text.splitlines()
        candidate_segments: List[str] = []

        for line in raw_lines:
            l_clean = line.strip()
            if not l_clean:
                continue
            # Skip markdown heading lines (e.g., # Title, ## Section, ### Subheading)
            if l_clean.startswith("#"):
                continue
            # Strip bullet and numbered list prefixes (-, *, •, 1., 2.)
            l_clean = re.sub(r"^(?:[-*•]|\d+\.)\s*", "", l_clean).strip()
            # Remove inline citation tags like [Source 1], [Source 2]
            l_clean = re.sub(r"\[Source\s*\d+\]", "", l_clean).strip()

            if not l_clean or len(l_clean) < 5:
                continue

            # Split line into sentences if it contains sentence terminators
            sub_sentences = re.split(r"(?<=[.!?])\s+", l_clean)
            for s in sub_sentences:
                s_strip = s.strip()
                if s_strip:
                    candidate_segments.append(s_strip)

        claims: List[str] = []
        ignore_prefixes = (
            "sure", "here is", "based on", "according to", "in summary",
            "hello", "hi", "note that", "please note", "in conclusion",
            "the provided", "as stated in"
        )

        for s_clean in candidate_segments:
            s_clean = re.sub(r"\[Source\s*\d+\]", "", s_clean).strip()
            if not s_clean or len(s_clean) < 8:
                continue

            lower_s = s_clean.lower()
            # If sentence is purely a greeting or conversational introductory clause
            if any(lower_s.startswith(p) for p in ignore_prefixes) and len(s_clean.split()) <= 4:
                continue

            claims.append(s_clean)

        return claims

    def extract_numeric_entities(self, text: str) -> List[NumericEntity]:
        """
        Extracts numeric values with attached or adjacent units, storage, percentages, and dates.
        Recognizes integers, decimals, percentages, dates, and temporal/storage units.
        """
        if not text:
            return []

        entities: List[NumericEntity] = []
        spans: List[Tuple[int, int]] = []

        # 0. Match ISO dates (YYYY-MM-DD)
        date_pattern = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
        for m in date_pattern.finditer(text):
            val = m.group(1)
            start, end = m.span()
            window = text[max(0, start - 60):min(len(text), end + 60)]
            w_tokens = set(self.reranker.tokenize(window))
            ctx_tokens = {t for t in w_tokens if not t.isdigit() and len(t) > 2}

            # Immediate attribute window (+/- 25 chars)
            attr_window = text[max(0, start - 25):min(len(text), end + 25)]
            attr_tokens = {t for t in self.reranker.tokenize(attr_window) if not t.isdigit() and len(t) > 2}

            entities.append(NumericEntity(
                value=val,
                unit="date",
                raw=m.group(0),
                context_tokens=ctx_tokens,
                attribute_tokens=attr_tokens
            ))
            spans.append((start, end))

        # 1. Match numbers with explicit units
        unit_pattern = re.compile(
            r"\b(\d+(?:\.\d+)?)\s*(ms|milliseconds?|s|sec|secs|seconds?|m|min|mins|minutes?|"
            r"h|hr|hrs|hours?|d|day|days|wk|weeks?|mo|months?|yr|yrs|years?|%|percent|percentage|"
            r"kb|mb|gb|tb|terabytes?|gigabytes?|megabytes?|kilobytes?|bytes?)\b",
            re.IGNORECASE
        )
        for m in unit_pattern.finditer(text):
            start, end = m.span()
            if any(s_start <= start and end <= s_end for s_start, s_end in spans):
                continue
            val, unit = m.group(1), m.group(2)
            window = text[max(0, start - 150):min(len(text), end + 150)]
            w_tokens = set(self.reranker.tokenize(window))
            ctx_tokens = {t for t in w_tokens if not t.isdigit() and len(t) > 2}

            attr_window = text[max(0, start - 25):min(len(text), end + 25)]
            attr_tokens = {t for t in self.reranker.tokenize(attr_window) if not t.isdigit() and len(t) > 2}

            entities.append(NumericEntity(
                value=val,
                unit=unit,
                raw=m.group(0),
                context_tokens=ctx_tokens,
                attribute_tokens=attr_tokens
            ))
            spans.append((start, end))

        # 2. Match standalone numbers not part of units (including 4-digit years)
        standalone_pattern = re.compile(r"\b(\d+(?:\.\d+)?)\b")
        for m in standalone_pattern.finditer(text):
            start, end = m.span()
            if any(s_start <= start and end <= s_end for s_start, s_end in spans):
                continue
            val = m.group(1)
            unit = "year" if (len(val) == 4 and val.startswith(("19", "20"))) else None
            window = text[max(0, start - 150):min(len(text), end + 150)]
            w_tokens = set(self.reranker.tokenize(window))
            ctx_tokens = {t for t in w_tokens if not t.isdigit() and len(t) > 2}

            attr_window = text[max(0, start - 25):min(len(text), end + 25)]
            attr_tokens = {t for t in self.reranker.tokenize(attr_window) if not t.isdigit() and len(t) > 2}

            entities.append(NumericEntity(
                value=val,
                unit=unit,
                raw=m.group(0),
                context_tokens=ctx_tokens,
                attribute_tokens=attr_tokens
            ))

        return entities

    def check_numeric_consistency(
        self,
        claim_entities: List[NumericEntity],
        evidence_entities: List[NumericEntity]
    ) -> bool:
        """
        Verifies that every numeric entity asserted in a claim is compatible
        with at least one numeric entity present in the evidence.
        Enforces attribute alignment to prevent swapped or misattributed values.
        """
        if not claim_entities:
            return True
        if not evidence_entities:
            return False

        for c_ent in claim_entities:
            matched = False
            for e_ent in evidence_entities:
                if not c_ent.matches(e_ent):
                    continue

                # Check for mutually exclusive attribute collision
                conflict_attr = False
                for excl in EXCLUSIVE_METRIC_ATTRIBUTES:
                    c_overlap = c_ent.attribute_tokens & excl
                    e_overlap = e_ent.attribute_tokens & excl
                    if c_overlap and e_overlap and not (c_overlap & e_overlap):
                        conflict_attr = True
                        break

                if not conflict_attr:
                    matched = True
                    break

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
        Distinguishes between:
        A. Same fact, same value -> no conflict
        B. Same fact, different value -> conflict
        C. Different facts using the same unit -> NOT a conflict (e.g. interval vs timeout)
        """
        if len(evidence_chunks) < 2:
            return None

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
                            # Unitless numbers should only conflict if they describe the exact same attribute
                            if bool(ea.attribute_tokens & eb.attribute_tokens) and not (
                                ea.raw in ("00", "01", "02") or "-" in ea.raw or "-" in eb.raw
                            ):
                                same_unit = True

                        if same_unit and ea.value != eb.value:
                            # Both entities must share context tokens that align with query
                            shared_ctx = ea.context_tokens & eb.context_tokens
                            shared_with_query = shared_ctx & q_tokens

                            # Check if the entities have mutually exclusive metric attributes
                            is_different_metric = False
                            for excl in EXCLUSIVE_METRIC_ATTRIBUTES:
                                a_excl = ea.attribute_tokens & excl
                                b_excl = eb.attribute_tokens & excl
                                if a_excl and b_excl and not (a_excl & b_excl):
                                    is_different_metric = True
                                    break

                            # Conflict requires strong topical alignment with the query:
                            # Disregard generic domain filler words to prevent irrelevant numbers from conflicting
                            common_domain_tokens = {
                                "storage", "data", "system", "default", "node", "nodes",
                                "log", "logs", "service", "file", "files", "set", "across"
                            }
                            topical_query_overlap = shared_with_query - common_domain_tokens
                            strong_query_align = len(topical_query_overlap) >= 1 and (
                                len(shared_with_query) >= 2 or bool(ea.attribute_tokens & eb.attribute_tokens)
                            )

                            if strong_query_align and not is_different_metric:
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
        Performs holistic deterministic grounding verification with both
        single-chunk and multi-chunk support.
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
        has_multi_chunk_claim = False

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
            claim_stems = set(canonical_unit(t) for t in claim_tokens)

            best_chunk_id: Optional[str] = None
            best_chunk_score: float = 0.0
            claim_supported = False
            numeric_ok = True

            # Phase A: Single chunk support
            for ev in parsed_evidence:
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
                phrase_overlap = self.reranker.compute_phrase_score(claim, ev["text"])
                num_consistent = self.check_numeric_consistency(claim_entities, ev["entities"])

                if (effective_overlap >= 0.28 or phrase_overlap >= 0.28):
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
                    numeric_consistent=True,
                    is_multi_chunk=False
                ))
                continue

            # Phase B: Multi-chunk composite support (Task 2)
            # When a compound claim spans multiple chunks or adjacent context
            candidate_chunks = []
            for ev in parsed_evidence:
                ev_stems = set(canonical_unit(t) for t in ev["tokens"])
                s_ov = len(claim_stems & ev_stems) / len(claim_stems) if claim_stems else 0.0
                if s_ov >= 0.15:
                    candidate_chunks.append(ev)

            if len(candidate_chunks) >= 2:
                combined_tokens = set().union(*(c["tokens"] for c in candidate_chunks))
                combined_stems = set(canonical_unit(t) for t in combined_tokens)
                comb_overlap = len(claim_stems & combined_stems) / len(claim_stems) if claim_stems else 0.0

                combined_entities: List[NumericEntity] = []
                for c in candidate_chunks:
                    combined_entities.extend(c["entities"])

                comb_num_consistent = self.check_numeric_consistency(claim_entities, combined_entities)

                if comb_overlap >= 0.40 and comb_num_consistent:
                    claim_supported = True
                    has_multi_chunk_claim = True
                    matched_ids = [c["chunk_id"] for c in candidate_chunks]
                    avg_cand_score = sum(c["score"] for c in candidate_chunks) / len(candidate_chunks)
                    supported_claims.append(claim)
                    actively_used_chunk_ids.update(matched_ids)
                    verifications.append(ClaimVerificationResult(
                        claim_text=claim,
                        is_supported=True,
                        matched_chunk_ids=matched_ids,
                        confidence=avg_cand_score,
                        numeric_consistent=True,
                        is_multi_chunk=True
                    ))
                    continue
                else:
                    if not comb_num_consistent:
                        numeric_ok = False

            # Unsupported claim
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

        # 5. Deterministic confidence calibration (Task 6)
        top_score = max((ev["score"] for ev in parsed_evidence), default=0.5)
        top_score = min(1.0, max(0.0, top_score))

        used_chunks = [ev for ev in parsed_evidence if ev["chunk_id"] in actively_used_chunk_ids]
        avg_used_score = (
            sum(ev["score"] for ev in used_chunks) / len(used_chunks)
            if used_chunks else top_score
        )
        avg_used_score = min(1.0, max(0.0, avg_used_score))

        composite_multiplier = 0.92 if has_multi_chunk_claim else 1.0

        if status == GroundingStatus.SUPPORTED:
            raw_conf = (0.45 + (0.30 * top_score) + (0.25 * avg_used_score)) * composite_multiplier
            confidence = min(0.99, max(0.60, raw_conf))
        elif status == GroundingStatus.PARTIALLY_SUPPORTED:
            ratio = supported_count / total_claims
            raw_conf = ratio * (0.35 + (0.45 * top_score)) * composite_multiplier
            confidence = min(0.70, max(0.20, raw_conf))
        else:
            confidence = 0.0

        ordered_source_ids = [
            ev["chunk_id"] for ev in parsed_evidence
            if ev["chunk_id"] in actively_used_chunk_ids
        ]
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
