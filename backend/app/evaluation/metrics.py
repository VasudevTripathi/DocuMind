import math
from typing import Collection, Dict, List, Optional, Sequence, Set

def hit_rate_at_k(retrieved_ids: Sequence[str], relevant_ids: Collection[str], k: int) -> float:
    """
    Hit@K: 1.0 if at least one relevant chunk appears in top K results, 0.0 otherwise.
    Handles empty inputs, k <= 0, k larger than available results, and duplicate IDs safely.
    """
    if k <= 0 or not retrieved_ids or not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    top_k = retrieved_ids[:k]
    for cid in top_k:
        if cid in relevant_set:
            return 1.0
    return 0.0

def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Collection[str], k: int) -> float:
    """
    Recall@K: (number of unique relevant chunks retrieved in top K) / (total number of relevant chunks).
    Returns 0.0 if relevant_ids is empty or k <= 0.
    Duplicate chunk IDs in retrieved results are deduplicated to avoid inflating counts.
    """
    if k <= 0 or not retrieved_ids or not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    if not relevant_set:
        return 0.0

    seen: Set[str] = set()
    unique_top_k: List[str] = []
    for cid in retrieved_ids[:k]:
        if cid not in seen:
            seen.add(cid)
            unique_top_k.append(cid)

    hits = sum(1 for cid in unique_top_k if cid in relevant_set)
    return float(hits) / float(len(relevant_set))

def precision_at_k(retrieved_ids: Sequence[str], relevant_ids: Collection[str], k: int) -> float:
    """
    Precision@K: (number of unique relevant chunks retrieved in top K) / K.
    Returns 0.0 if relevant_ids is empty or k <= 0.
    Denominator is strictly K according to standard information retrieval definitions.
    """
    if k <= 0 or not retrieved_ids or not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    if not relevant_set:
        return 0.0

    seen: Set[str] = set()
    unique_top_k: List[str] = []
    for cid in retrieved_ids[:k]:
        if cid not in seen:
            seen.add(cid)
            unique_top_k.append(cid)

    hits = sum(1 for cid in unique_top_k if cid in relevant_set)
    return float(hits) / float(k)

def reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: Collection[str]) -> float:
    """
    Reciprocal Rank (RR): 1 / rank of the first relevant result (1-indexed).
    If no relevant result appears in retrieved_ids, RR = 0.0.
    """
    if not retrieved_ids or not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in relevant_set:
            return 1.0 / float(rank)
    return 0.0

def mean_reciprocal_rank(rr_scores: Sequence[float]) -> float:
    """
    Mean Reciprocal Rank (MRR): Average RR across all evaluated queries.
    Returns 0.0 if rr_scores is empty.
    """
    if not rr_scores:
        return 0.0
    return float(sum(rr_scores)) / float(len(rr_scores))

def average_precision_at_k(
    retrieved_ids: Sequence[str],
    relevant_ids: Collection[str],
    k: Optional[int] = None
) -> float:
    """
    Average Precision (AP) for a query up to cutoff K (or all retrieved if k is None).
    AP = sum_{i=1}^k (Precision@i * rel(i)) / min(len(relevant_ids), k)
    """
    if not retrieved_ids or not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    if not relevant_set:
        return 0.0

    target_k = len(retrieved_ids) if k is None else max(0, k)
    if target_k == 0:
        return 0.0

    seen: Set[str] = set()
    unique_top: List[str] = []
    for cid in retrieved_ids[:target_k]:
        if cid not in seen:
            seen.add(cid)
            unique_top.append(cid)

    cum_hits = 0
    sum_precisions = 0.0
    for rank, cid in enumerate(unique_top, start=1):
        if cid in relevant_set:
            cum_hits += 1
            sum_precisions += float(cum_hits) / float(rank)

    normalizer = min(len(relevant_set), target_k)
    return float(sum_precisions) / float(normalizer) if normalizer > 0 else 0.0

def mean_average_precision(ap_scores: Sequence[float]) -> float:
    """
    Mean Average Precision (MAP): Mean of AP scores across queries.
    """
    if not ap_scores:
        return 0.0
    return float(sum(ap_scores)) / float(len(ap_scores))

def grounded_answer_rate(statuses: Sequence[str]) -> float:
    """
    Grounded Answer Rate: fraction of evaluated answers that are fully supported.
    """
    if not statuses:
        return 0.0
    supported = sum(1 for s in statuses if s == "SUPPORTED")
    return float(supported) / float(len(statuses))

def unsupported_claim_rate(supported_counts: Sequence[int], unsupported_counts: Sequence[int]) -> float:
    """
    Unsupported Claim Rate: (total unsupported claims) / (total claims evaluated).
    """
    total_unsupported = sum(unsupported_counts)
    total_claims = sum(supported_counts) + total_unsupported
    if total_claims == 0:
        return 0.0
    return float(total_unsupported) / float(total_claims)

def numeric_consistency_rate(consistent_counts: Sequence[int], total_numeric_counts: Sequence[int]) -> float:
    """
    Numeric Consistency Rate: (consistent numeric claims) / (total claims containing numeric facts).
    """
    total_numeric = sum(total_numeric_counts)
    if total_numeric == 0:
        return 1.0  # vacuously 100% consistent if no numeric claims
    return float(sum(consistent_counts)) / float(total_numeric)

def no_context_rejection_rate(rejected_count: int, total_no_context: int) -> float:
    """
    No-Context Rejection Rate: correctly rejected no-context queries / total no-context queries.
    """
    if total_no_context <= 0:
        return 1.0
    return float(rejected_count) / float(total_no_context)

def conflict_detection_rate(detected_conflicts: int, total_conflict_cases: int) -> float:
    """
    Conflict Detection Rate: correctly detected conflicting evidence cases / total conflicting cases.
    """
    if total_conflict_cases <= 0:
        return 1.0
    return float(detected_conflicts) / float(total_conflict_cases)

def partial_support_detection_rate(detected_partial: int, total_partial_cases: int) -> float:
    """
    Partial Support Detection Rate: correctly flagged partial-support answers / total partial cases.
    """
    if total_partial_cases <= 0:
        return 1.0
    return float(detected_partial) / float(total_partial_cases)

