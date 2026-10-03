import pytest
from app.services.grounding_service import (
    grounding_service,
    GroundingStatus,
    GroundingService,
    NumericEntity,
    canonical_unit
)

def test_unit_canonicalization():
    assert canonical_unit("ms") == "millisecond"
    assert canonical_unit("milliseconds") == "millisecond"
    assert canonical_unit("sec") == "second"
    assert canonical_unit("seconds") == "second"
    assert canonical_unit("min") == "minute"
    assert canonical_unit("hours") == "hour"
    assert canonical_unit("years") == "year"
    assert canonical_unit("%") == "percent"
    assert canonical_unit("gb") == "gigabyte"

def test_claim_extraction():
    answer = (
        "The primary cluster heartbeat interval is set to 250 milliseconds. "
        "Failover begins after three consecutive missed heartbeats. [Source 1]"
    )
    claims = grounding_service.extract_claims(answer)
    assert len(claims) == 2
    assert "250 milliseconds" in claims[0]
    assert "[Source 1]" not in claims[1]
    assert "Failover begins" in claims[1]

def test_fully_supported_claim():
    evidence = [
        {
            "chunk_id": "chk-1",
            "text": "The primary cluster heartbeat interval is set to 250 milliseconds.",
            "score": 0.85
        }
    ]
    answer = "The primary cluster heartbeat interval is set to 250 milliseconds."
    res = grounding_service.verify_answer(
        query="What is the heartbeat interval?",
        answer=answer,
        evidence_chunks=evidence
    )
    assert res.status == GroundingStatus.SUPPORTED
    assert len(res.supported_claims) == 1
    assert len(res.unsupported_claims) == 0
    assert "chk-1" in res.source_chunk_ids
    assert res.confidence >= 0.80

def test_unsupported_claim():
    evidence = [
        {
            "chunk_id": "chk-1",
            "text": "The database operates on an automated replication schedule.",
            "score": 0.60
        }
    ]
    answer = "The database cluster uses Paxos consensus protocol."
    res = grounding_service.verify_answer(
        query="What consensus protocol is used?",
        answer=answer,
        evidence_chunks=evidence
    )
    assert res.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert len(res.unsupported_claims) == 1
    assert len(res.supported_claims) == 0
    assert res.confidence == 0.0

def test_partially_supported_answer():
    evidence = [
        {
            "chunk_id": "chk-1",
            "text": "The primary cluster heartbeat interval is set to 250 milliseconds.",
            "score": 0.80
        }
    ]
    # Claim 1 is supported, Claim 2 is fabricated
    answer = (
        "The primary cluster heartbeat interval is set to 250 milliseconds. "
        "The cluster automatically shuts down when CPU usage reaches 99 percent."
    )
    res = grounding_service.verify_answer(
        query="What are the heartbeat and CPU shutdown parameters?",
        answer=answer,
        evidence_chunks=evidence
    )
    assert res.status == GroundingStatus.PARTIALLY_SUPPORTED
    assert len(res.supported_claims) == 1
    assert len(res.unsupported_claims) == 1
    assert 0.0 < res.confidence < 0.80

def test_numeric_mismatch_detection():
    evidence = [
        {
            "chunk_id": "chk-1",
            "text": "The primary cluster heartbeat interval is set to 250 milliseconds.",
            "score": 0.85
        }
    ]
    # Claim asserts 500 milliseconds instead of 250 milliseconds
    answer = "The primary cluster heartbeat interval is set to 500 milliseconds."
    res = grounding_service.verify_answer(
        query="What is the heartbeat interval?",
        answer=answer,
        evidence_chunks=evidence
    )
    assert res.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert len(res.unsupported_claims) == 1
    assert len(res.supported_claims) == 0

def test_numeric_and_unit_compatible_match():
    evidence = [
        {
            "chunk_id": "chk-1",
            "text": "The primary cluster heartbeat interval is set to 250 milliseconds.",
            "score": 0.85
        }
    ]
    # '250 ms' should be recognized as compatible with '250 milliseconds'
    answer = "The primary cluster heartbeat interval is 250 ms."
    res = grounding_service.verify_answer(
        query="What is the heartbeat interval?",
        answer=answer,
        evidence_chunks=evidence
    )
    assert res.status == GroundingStatus.SUPPORTED
    assert len(res.supported_claims) == 1
    assert res.confidence > 0.70

def test_conflicting_evidence_detection():
    evidence = [
        {
            "chunk_id": "chk-a",
            "text": "Database backup retention policy requires keeping archive logs for 7 years.",
            "score": 0.90
        },
        {
            "chunk_id": "chk-b",
            "text": "Database backup retention policy requires keeping archive logs for 10 years.",
            "score": 0.88
        }
    ]
    query = "What is the database backup retention policy?"
    answer = "The backup retention policy requires keeping archive logs for 7 years."
    res = grounding_service.verify_answer(
        query=query,
        answer=answer,
        evidence_chunks=evidence
    )
    assert res.status == GroundingStatus.CONFLICTING_EVIDENCE
    assert res.conflicts is not None
    assert len(res.conflicts) >= 1
    assert "7 years" in res.conflicts[0] and "10 years" in res.conflicts[0]
    assert "chk-a" in res.source_chunk_ids and "chk-b" in res.source_chunk_ids

def test_empty_answer_and_empty_evidence():
    # Empty answer
    res1 = grounding_service.verify_answer("query", "", [{"chunk_id": "c1", "text": "evidence"}])
    assert res1.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert res1.confidence == 0.0

    # Empty evidence
    res2 = grounding_service.verify_answer("query", "Some answer text.", [])
    assert res2.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert res2.confidence == 0.0

def test_fallback_string_handling():
    fallback = "The answer could not be found in the provided documents."
    res = grounding_service.verify_answer("query", fallback, [{"chunk_id": "c1", "text": "evidence"}])
    assert res.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert res.confidence == 0.0
    assert len(res.supported_claims) == 0

def test_deterministic_confidence_bounds():
    evidence = [
        {
            "chunk_id": "chk-1",
            "text": "Audit logs must be retained for seven years under HIPAA compliance guidelines.",
            "score": 0.85
        }
    ]
    res = grounding_service.verify_answer(
        query="How long must audit logs be retained?",
        answer="Audit logs must be retained for seven years under HIPAA guidelines.",
        evidence_chunks=evidence
    )
    assert 0.0 <= res.confidence <= 1.0
    # Should be rounded to 2 decimal places
    assert res.confidence == round(res.confidence, 2)

def test_step_16_controlled_grounding_scenarios():
    """Verify all Step 16 controlled test cases explicitly."""
    evidence = [
        {
            "chunk_id": "chk-ctrl-1",
            "text": "The cluster sends heartbeats every 250 milliseconds. After three consecutive heartbeat failures, failover begins.",
            "score": 0.90
        }
    ]

    # Q1: Supported
    res_q1 = grounding_service.verify_answer(
        query="What is the heartbeat interval?",
        answer="The heartbeat interval is 250 milliseconds.",
        evidence_chunks=evidence
    )
    assert res_q1.status == GroundingStatus.SUPPORTED

    # Q2: Supported
    res_q2 = grounding_service.verify_answer(
        query="When does failover begin?",
        answer="Failover begins after three consecutive heartbeat failures.",
        evidence_chunks=evidence
    )
    assert res_q2.status == GroundingStatus.SUPPORTED

    # Q3: Intentionally incorrect number -> NOT SUPPORTED (INSUFFICIENT_EVIDENCE)
    res_q3 = grounding_service.verify_answer(
        query="What is the heartbeat interval?",
        answer="The heartbeat interval is 500 milliseconds.",
        evidence_chunks=evidence
    )
    assert res_q3.status in (GroundingStatus.INSUFFICIENT_EVIDENCE, GroundingStatus.PARTIALLY_SUPPORTED)
    assert len(res_q3.supported_claims) == 0

    # Q4: Out-of-context question -> INSUFFICIENT_EVIDENCE
    res_q4 = grounding_service.verify_answer(
        query="What is the capital of France?",
        answer="The answer could not be found in the provided documents.",
        evidence_chunks=evidence
    )
    assert res_q4.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert res_q4.confidence == 0.0

    # Q5: Conflicting evidence
    conflicting_ev = [
        {"chunk_id": "c-ret-7", "text": "Backup retention is 7 years.", "score": 0.88},
        {"chunk_id": "c-ret-10", "text": "Backup retention is 10 years.", "score": 0.88}
    ]
    res_q5 = grounding_service.verify_answer(
        query="What is the backup retention period?",
        answer="Backup retention is 7 years.",
        evidence_chunks=conflicting_ev
    )
    assert res_q5.status == GroundingStatus.CONFLICTING_EVIDENCE
