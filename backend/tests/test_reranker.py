import pytest
from app.services.reranker import RetrievalReranker, reranker

def test_semantic_score_preservation():
    """Verify that original semantic similarity score is preserved without distortion."""
    candidates = [
        {
            "chunk_id": "chk-1",
            "chunk_index": 0,
            "text": "The circuit breaker operates on an 11 percent failure threshold.",
            "similarity_score": 0.8523,
            "score": 0.8523
        }
    ]
    reranked = reranker.rerank("circuit breaker threshold", candidates)
    assert len(reranked) == 1
    assert reranked[0]["semantic_score"] == 0.8523
    assert reranked[0]["similarity_score"] == 0.8523

def test_lexical_overlap_calculation_and_bounds():
    """Verify normalized token overlap computation and bounds in [0.0, 1.0]."""
    rr = RetrievalReranker(semantic_weight=0.75, lexical_weight=0.25)
    query_tokens = rr.tokenize("heartbeat timeout configuration")

    # 1. Full overlap
    score_full = rr.compute_lexical_score(query_tokens, "heartbeat timeout configuration details")
    assert score_full == 1.0

    # 2. Partial overlap (2 of 3 tokens match)
    score_partial = rr.compute_lexical_score(query_tokens, "heartbeat timeout settings")
    assert round(score_partial, 2) == round(2 / 3, 2)

    # 3. Zero overlap
    score_zero = rr.compute_lexical_score(query_tokens, "unrelated text about bananas")
    assert score_zero == 0.0

    # 4. Empty text or tokens
    assert rr.compute_lexical_score([], "some text") == 0.0
    assert rr.compute_lexical_score(query_tokens, "") == 0.0

def test_relevant_lexical_match_ranking():
    """
    Verify that between two chunks with equal semantic score,
    the chunk with higher lexical overlap ranks higher.
    """
    candidates = [
        {
            "chunk_id": "chk-low-lex",
            "chunk_index": 0,
            "text": "General maintenance rules for physical hardware appliances.",
            "similarity_score": 0.60
        },
        {
            "chunk_id": "chk-high-lex",
            "chunk_index": 1,
            "text": "Strict annual equipment maintenance audit is scheduled on November 15.",
            "similarity_score": 0.60
        }
    ]
    reranked = reranker.rerank("equipment maintenance audit", candidates)
    assert reranked[0]["chunk_id"] == "chk-high-lex"
    assert reranked[0]["lexical_score"] > reranked[1]["lexical_score"]
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

def test_deterministic_tie_breaking():
    """
    Verify deterministic ordering:
    1. rerank_score descending
    2. semantic_score descending
    3. chunk_index ascending
    """
    candidates = [
        {
            "chunk_id": "chk-idx-5",
            "chunk_index": 5,
            "text": "Data backup procedure.",
            "similarity_score": 0.50
        },
        {
            "chunk_id": "chk-idx-2",
            "chunk_index": 2,
            "text": "Data backup procedure.",
            "similarity_score": 0.50
        }
    ]
    # Identical query and text -> equal rerank_score and semantic_score.
    # Should tie-break by chunk_index ascending (chk-idx-2 before chk-idx-5).
    reranked = reranker.rerank("backup", candidates)
    assert reranked[0]["chunk_id"] == "chk-idx-2"
    assert reranked[1]["chunk_id"] == "chk-idx-5"

def test_duplicate_candidate_handling():
    """Verify duplicate candidate chunks are consolidated keeping the highest score."""
    candidates = [
        {
            "chunk_id": "chk-dup",
            "chunk_index": 1,
            "text": "Failover election begins.",
            "similarity_score": 0.40
        },
        {
            "chunk_id": "chk-dup",
            "chunk_index": 1,
            "text": "Failover election begins.",
            "similarity_score": 0.70
        }
    ]
    reranked = reranker.rerank("failover election", candidates)
    assert len(reranked) == 1
    assert reranked[0]["semantic_score"] == 0.70

def test_empty_query_and_candidates():
    """Verify safe behavior when candidates or query are empty."""
    assert reranker.rerank("query", []) == []

    candidates = [
        {
            "chunk_id": "chk-1",
            "chunk_index": 0,
            "text": "Some text content.",
            "similarity_score": 0.50
        }
    ]
    reranked = reranker.rerank("", candidates)
    assert len(reranked) == 1
    assert reranked[0]["lexical_score"] == 0.0
    # rerank_score is purely weighted semantic score (0.75 * 0.50 = 0.375)
    assert reranked[0]["rerank_score"] == round(0.75 * 0.50, 4)

def test_score_bounds_and_exposures():
    """Verify all internal score fields (semantic_score, lexical_score, rerank_score, score) are exposed and bounded."""
    candidates = [
        {
            "chunk_id": "chk-1",
            "chunk_index": 0,
            "text": "Protocol configuration details.",
            "similarity_score": 0.80
        }
    ]
    reranked = reranker.rerank("protocol details", candidates)
    res = reranked[0]
    for key in ["semantic_score", "similarity_score", "lexical_score", "rerank_score", "score"]:
        assert key in res
        assert 0.0 <= res[key] <= 1.0
