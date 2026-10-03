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

def test_exact_phrase_match_beats_weaker_lexical():
    """Exact phrase match beats weaker lexical match when semantic scores are close."""
    candidates = [
        {
            "chunk_id": "chk-scattered",
            "chunk_index": 0,
            "text": "The node heartbeat failed and after a long timeout we checked the interval.",
            "similarity_score": 0.60
        },
        {
            "chunk_id": "chk-exact-phrase",
            "chunk_index": 1,
            "text": "The primary cluster heartbeat timeout interval is set to 250 milliseconds.",
            "similarity_score": 0.60
        }
    ]
    reranked = reranker.rerank("heartbeat timeout interval", candidates)
    assert reranked[0]["chunk_id"] == "chk-exact-phrase"
    assert reranked[0]["phrase_score"] > reranked[1]["phrase_score"]
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

def test_higher_query_term_coverage_improves_ranking():
    """Higher query-term coverage improves ranking when other signals are comparable."""
    candidates = [
        {
            "chunk_id": "chk-low-cov",
            "chunk_index": 0,
            "text": "Cluster heartbeat monitoring daemon runs continuously in background.",
            "similarity_score": 0.55
        },
        {
            "chunk_id": "chk-high-cov",
            "chunk_index": 1,
            "text": "Cluster heartbeat failover triggers standby leadership election when missed.",
            "similarity_score": 0.55
        }
    ]
    # Query has 4 tokens: heartbeat, failover, standby, election
    reranked = reranker.rerank("heartbeat failover standby election", candidates)
    assert reranked[0]["chunk_id"] == "chk-high-cov"
    assert reranked[0]["coverage_score"] > reranked[1]["coverage_score"]
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

def test_semantic_relevance_still_matters():
    """High semantic relevance still dominates when lexical/phrase match is low."""
    candidates = [
        {
            "chunk_id": "chk-high-sem",
            "chunk_index": 0,
            "text": "Automated Raft consensus handles node failure recovery seamlessly.",
            "similarity_score": 0.95
        },
        {
            "chunk_id": "chk-low-sem",
            "chunk_index": 1,
            "text": "Raft protocol is a consensus protocol.",
            "similarity_score": 0.20
        }
    ]
    reranked = reranker.rerank("high availability Raft failure recovery", candidates)
    assert reranked[0]["chunk_id"] == "chk-high-sem"

def test_phrase_score_bounds():
    """Verify phrase score is strictly bounded in [0.0, 1.0]."""
    rr = RetrievalReranker()
    assert rr.compute_phrase_score("cluster heartbeat", "The cluster heartbeat interval") == 1.0
    assert 0.0 <= rr.compute_phrase_score("cluster heartbeat interval", "cluster heartbeat timing") <= 1.0
    assert rr.compute_phrase_score("cluster heartbeat", "unrelated apples") == 0.0
    assert rr.compute_phrase_score("", "some text") == 0.0
    assert rr.compute_phrase_score("some query", "") == 0.0

def test_coverage_score_bounds():
    """Verify coverage score is strictly bounded in [0.0, 1.0]."""
    rr = RetrievalReranker()
    q_tokens = rr.tokenize("cluster leadership election")
    assert rr.compute_coverage_score(q_tokens, "cluster leadership election protocol") == 1.0
    assert round(rr.compute_coverage_score(q_tokens, "cluster protocol only"), 2) == round(1 / 3, 2)
    assert rr.compute_coverage_score(q_tokens, "unrelated text") == 0.0
    assert rr.compute_coverage_score([], "some text") == 0.0

def test_context_score_bounds_and_discount():
    """Verify context score distinguishes direct match from expanded neighbor."""
    rr = RetrievalReranker()
    direct_cand = {"chunk_id": "c1", "is_expanded": False, "context_distance": 0}
    expanded_cand = {"chunk_id": "c2", "is_expanded": True, "context_distance": 1}

    assert rr.compute_context_score(direct_cand) == 1.0
    assert rr.compute_context_score(expanded_cand) == rr.context_discount
    assert 0.0 <= rr.compute_context_score(expanded_cand) <= 1.0

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
    assert reranked[0]["phrase_score"] == 0.0
    assert reranked[0]["coverage_score"] == 0.0
    assert 0.0 <= reranked[0]["rerank_score"] <= 1.0

def test_phase_8_1_compatibility_mode():
    """Verify 2-argument constructor behaves identically to Phase 8.1 reranker."""
    legacy_rr = RetrievalReranker(semantic_weight=0.75, lexical_weight=0.25)
    assert legacy_rr.semantic_weight == 0.75
    assert legacy_rr.lexical_weight == 0.25
    assert legacy_rr.phrase_weight == 0.0
    assert legacy_rr.coverage_weight == 0.0
    assert legacy_rr.context_weight == 0.0

    candidates = [
        {
            "chunk_id": "chk-1",
            "chunk_index": 0,
            "text": "Circuit breaker threshold is 11 percent.",
            "similarity_score": 0.80
        }
    ]
    res = legacy_rr.rerank("circuit breaker", candidates)
    # Expected score: 0.75 * 0.80 + 0.25 * 1.0 = 0.60 + 0.25 = 0.85
    assert res[0]["rerank_score"] == 0.85

def test_score_bounds_and_exposures():
    """Verify all score fields are exposed and bounded in [0.0, 1.0]."""
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
    expected_keys = [
        "semantic_score",
        "similarity_score",
        "lexical_score",
        "phrase_score",
        "coverage_score",
        "context_score",
        "rerank_score",
        "score"
    ]
    for key in expected_keys:
        assert key in res
        assert 0.0 <= res[key] <= 1.0
