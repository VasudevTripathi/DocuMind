import pytest
from app.evaluation.metrics import (
    hit_rate_at_k,
    recall_at_k,
    precision_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
    average_precision_at_k,
    mean_average_precision,
)

def test_hit_rate_at_k_scenarios():
    # 1. Perfect retrieval (first item is relevant)
    assert hit_rate_at_k(["c1", "c2", "c3"], ["c1"], k=1) == 1.0
    assert hit_rate_at_k(["c1", "c2", "c3"], ["c1"], k=3) == 1.0

    # 2. Zero-hit retrieval
    assert hit_rate_at_k(["x1", "x2", "x3"], ["c1"], k=3) == 0.0

    # 3. Partial / later rank retrieval
    assert hit_rate_at_k(["x1", "x2", "c1"], ["c1"], k=1) == 0.0
    assert hit_rate_at_k(["x1", "x2", "c1"], ["c1"], k=2) == 0.0
    assert hit_rate_at_k(["x1", "x2", "c1"], ["c1"], k=3) == 1.0

    # 4. Duplicate results in retrieved
    assert hit_rate_at_k(["c1", "c1", "c2"], ["c1"], k=1) == 1.0
    assert hit_rate_at_k(["c1", "c1", "c2"], ["c1"], k=2) == 1.0

    # 5. K larger than result count
    assert hit_rate_at_k(["c1"], ["c1"], k=10) == 1.0
    assert hit_rate_at_k(["x1"], ["c1"], k=10) == 0.0

    # 6. Empty results and edge cases
    assert hit_rate_at_k([], ["c1"], k=5) == 0.0
    assert hit_rate_at_k(["c1"], [], k=5) == 0.0
    assert hit_rate_at_k(["c1"], ["c1"], k=0) == 0.0
    assert hit_rate_at_k(["c1"], ["c1"], k=-1) == 0.0

def test_recall_at_k_scenarios():
    relevant = ["c1", "c2"]

    # 1. Perfect retrieval (all relevant in top K)
    assert recall_at_k(["c1", "c2", "c3"], relevant, k=2) == 1.0
    assert recall_at_k(["c1", "c2", "c3"], relevant, k=3) == 1.0

    # 2. Zero-hit retrieval
    assert recall_at_k(["x1", "x2", "x3"], relevant, k=3) == 0.0

    # 3. Partial retrieval (1 of 2 retrieved)
    assert recall_at_k(["c1", "x1", "x2"], relevant, k=1) == 0.5
    assert recall_at_k(["c1", "x1", "x2"], relevant, k=3) == 0.5

    # 4. Duplicate chunk IDs in retrieved (must not double-count)
    assert recall_at_k(["c1", "c1", "x1"], relevant, k=2) == 0.5
    assert recall_at_k(["c1", "c1", "c2"], relevant, k=3) == 1.0

    # 5. K larger than result count
    assert recall_at_k(["c1"], relevant, k=5) == 0.5
    assert recall_at_k(["c1", "c2"], relevant, k=5) == 1.0

    # 6. Multiple relevant chunks
    assert recall_at_k(["c1", "c2", "c3"], ["c1", "c2", "c3", "c4"], k=3) == 0.75

    # 7. Empty results and invalid k
    assert recall_at_k([], relevant, k=5) == 0.0
    assert recall_at_k(["c1"], [], k=5) == 0.0
    assert recall_at_k(["c1"], relevant, k=0) == 0.0
    assert recall_at_k(["c1"], relevant, k=-2) == 0.0

def test_precision_at_k_scenarios():
    relevant = ["c1", "c2"]

    # 1. Perfect precision (2 relevant in top 2)
    assert precision_at_k(["c1", "c2", "x1"], relevant, k=2) == 1.0

    # 2. Zero-hit precision
    assert precision_at_k(["x1", "x2", "x3"], relevant, k=3) == 0.0

    # 3. Partial precision (1 relevant in top 2)
    assert precision_at_k(["c1", "x1", "x2"], relevant, k=2) == 0.5
    # 1 relevant in top 3
    assert round(precision_at_k(["c1", "x1", "x2"], relevant, k=3), 4) == round(1.0 / 3.0, 4)

    # 4. Duplicate chunk IDs in retrieved (unique hits divided by K)
    assert precision_at_k(["c1", "c1"], relevant, k=2) == 0.5

    # 5. K larger than result count (K strictly in denominator)
    assert precision_at_k(["c1"], relevant, k=5) == 0.2

    # 6. Empty results and edge cases
    assert precision_at_k([], relevant, k=3) == 0.0
    assert precision_at_k(["c1"], [], k=3) == 0.0
    assert precision_at_k(["c1"], relevant, k=0) == 0.0
    assert precision_at_k(["c1"], relevant, k=-1) == 0.0

def test_reciprocal_rank_and_mrr():
    relevant = ["c1", "c2"]

    # First relevant at rank 1
    assert reciprocal_rank(["c1", "x1", "x2"], relevant) == 1.0

    # First relevant at rank 2
    assert reciprocal_rank(["x1", "c2", "x2"], relevant) == 0.5

    # First relevant at rank 4
    assert reciprocal_rank(["x1", "x2", "x3", "c1"], relevant) == 0.25

    # No relevant retrieved
    assert reciprocal_rank(["x1", "x2", "x3"], relevant) == 0.0

    # Empty inputs
    assert reciprocal_rank([], relevant) == 0.0
    assert reciprocal_rank(["c1"], []) == 0.0

    # Mean Reciprocal Rank
    rr_scores = [1.0, 0.5, 0.25, 0.0]
    assert mean_reciprocal_rank(rr_scores) == (1.0 + 0.5 + 0.25 + 0.0) / 4.0
    assert mean_reciprocal_rank([]) == 0.0

def test_average_precision_and_map():
    # Query with relevant at ranks 1 and 3
    # Precision@1 = 1/1 = 1.0
    # Precision@3 = 2/3
    # AP = (1.0 + 2/3) / 2 = 1.6667 / 2 = 0.8333
    ap = average_precision_at_k(["c1", "x1", "c2"], ["c1", "c2"], k=3)
    assert round(ap, 4) == round((1.0 + (2.0 / 3.0)) / 2.0, 4)

    # Empty edge cases
    assert average_precision_at_k([], ["c1"]) == 0.0
    assert average_precision_at_k(["c1"], []) == 0.0
    assert average_precision_at_k(["c1"], ["c1"], k=0) == 0.0

    # MAP
    assert mean_average_precision([1.0, 0.5]) == 0.75
    assert mean_average_precision([]) == 0.0

def test_grounding_metrics():
    from app.evaluation.metrics import (
        grounded_answer_rate,
        unsupported_claim_rate,
        numeric_consistency_rate,
        no_context_rejection_rate
    )

    # 1. Grounded answer rate
    assert grounded_answer_rate(["SUPPORTED", "SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE"]) == 0.5
    assert grounded_answer_rate([]) == 0.0

    # 2. Unsupported claim rate
    # 3 supported, 1 unsupported -> 1 / (3 + 1) = 0.25
    assert unsupported_claim_rate([3], [1]) == 0.25
    assert unsupported_claim_rate([], []) == 0.0

    # 3. Numeric consistency rate
    # 4 consistent out of 5 numeric claims -> 4/5 = 0.8
    assert numeric_consistency_rate([4], [5]) == 0.8
    assert numeric_consistency_rate([], []) == 1.0

    # 4. No-context rejection rate
    assert no_context_rejection_rate(3, 3) == 1.0
    assert no_context_rejection_rate(2, 4) == 0.5
    assert no_context_rejection_rate(0, 0) == 1.0
