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


# =========================================================================
# Phase 8.5 Task 7: 20 Adversarial Grounding Tests
# =========================================================================

def test_adversarial_01_correct_number_vs_wrong_number():
    evidence = [{"chunk_id": "c1", "text": "Cluster heartbeat interval is 250 milliseconds.", "score": 0.85}]
    res_correct = grounding_service.verify_answer("heartbeat", "Heartbeat interval is 250 milliseconds.", evidence)
    assert res_correct.status == GroundingStatus.SUPPORTED

    res_wrong = grounding_service.verify_answer("heartbeat", "Heartbeat interval is 500 milliseconds.", evidence)
    assert res_wrong.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert len(res_wrong.unsupported_claims) == 1

def test_adversarial_02_correct_unit_vs_wrong_unit():
    evidence = [{"chunk_id": "c1", "text": "Log archives are retained for 7 years.", "score": 0.85}]
    res_unit_err = grounding_service.verify_answer("retention", "Log archives are retained for 7 days.", evidence)
    assert res_unit_err.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert len(res_unit_err.unsupported_claims) == 1

def test_adversarial_03_two_numbers_in_one_claim():
    evidence = [{
        "chunk_id": "c1",
        "text": "Heartbeat interval is set to 250 milliseconds with a timeout threshold of 1500 milliseconds.",
        "score": 0.90
    }]
    # Both numbers correct
    res_both_ok = grounding_service.verify_answer(
        "heartbeat timeout",
        "Heartbeat interval is 250 ms with a timeout threshold of 1500 ms.",
        evidence
    )
    assert res_both_ok.status == GroundingStatus.SUPPORTED

    # One number wrong
    res_one_wrong = grounding_service.verify_answer(
        "heartbeat timeout",
        "Heartbeat interval is 250 ms with a timeout threshold of 3000 ms.",
        evidence
    )
    assert res_one_wrong.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert len(res_one_wrong.unsupported_claims) == 1

def test_adversarial_04_same_unit_different_attributes():
    # 250 ms (interval) vs 1500 ms (timeout) - both use milliseconds but are distinct attributes
    evidence = [{
        "chunk_id": "c1",
        "text": "The primary cluster heartbeat interval is set to 250 milliseconds with a timeout threshold of 1500 milliseconds across all controller nodes.",
        "score": 0.90
    }]
    conflicts = grounding_service.detect_evidence_conflicts("What is the heartbeat interval and timeout?", evidence)
    assert conflicts is None

def test_adversarial_05_same_attribute_conflicting_values():
    evidence = [
        {"chunk_id": "doc1", "text": "Mandatory archive retention is 7 years.", "score": 0.90},
        {"chunk_id": "doc2", "text": "Mandatory archive retention is 10 years.", "score": 0.90}
    ]
    res = grounding_service.verify_answer(
        "What is the mandatory archive retention?",
        "Archive retention is 7 years.",
        evidence
    )
    assert res.status == GroundingStatus.CONFLICTING_EVIDENCE
    assert res.conflicts is not None
    assert len(res.conflicts) >= 1

def test_adversarial_06_support_distributed_across_two_chunks():
    evidence = [
        {"chunk_id": "c1", "text": "Database snapshots are scheduled weekly on Sundays at 02:00 UTC.", "score": 0.85},
        {"chunk_id": "c2", "text": "Recovery Time Objective for restoration is guaranteed under 15 minutes.", "score": 0.80}
    ]
    # Compound claim combining information from both chunks
    claim = "Database snapshots are scheduled weekly at 02:00 UTC and recovery time objective is under 15 minutes."
    res = grounding_service.verify_answer("snapshots and rto", claim, evidence)
    assert res.status == GroundingStatus.SUPPORTED
    assert "c1" in res.source_chunk_ids and "c2" in res.source_chunk_ids

def test_adversarial_07_unsupported_second_sentence():
    evidence = [{"chunk_id": "c1", "text": "Heartbeat interval is set to 250 milliseconds.", "score": 0.85}]
    answer = "Heartbeat interval is set to 250 milliseconds. Failover activates after two consecutive missed heartbeats."
    res = grounding_service.verify_answer("heartbeat", answer, evidence)
    assert res.status == GroundingStatus.PARTIALLY_SUPPORTED
    assert len(res.supported_claims) == 1
    assert len(res.unsupported_claims) == 1
    assert "250 milliseconds" in res.supported_claims[0]

def test_adversarial_08_partially_supported_answer():
    evidence = [{"chunk_id": "c1", "text": "Audit logs must be retained for seven years under HIPAA guidelines.", "score": 0.88}]
    answer = "Audit logs must be retained for seven years. Logs are uploaded to an unencrypted public FTP server."
    res = grounding_service.verify_answer("audit logs", answer, evidence)
    assert res.status == GroundingStatus.PARTIALLY_SUPPORTED
    assert len(res.supported_claims) == 1
    assert len(res.unsupported_claims) == 1

def test_adversarial_09_paraphrased_supported_answer():
    evidence = [{"chunk_id": "c1", "text": "The network gateway uses an interval timer of 250 milliseconds to probe upstream BGP peer routers.", "score": 0.85}]
    paraphrase = "The network gateway router probes upstream BGP peers with a 250 ms timer."
    res = grounding_service.verify_answer("bgp gateway probe", paraphrase, evidence)
    assert res.status == GroundingStatus.SUPPORTED

def test_adversarial_10_distractor_chunk_with_overlapping_vocabulary():
    evidence = [
        {"chunk_id": "target", "text": "The primary cluster heartbeat interval is set to 250 milliseconds across all controller nodes.", "score": 0.90},
        {"chunk_id": "distractor", "text": "The network gateway uses an interval timer of 250 milliseconds to probe upstream BGP peer routers.", "score": 0.60}
    ]
    answer = "The primary cluster controller heartbeat interval is 250 milliseconds."
    res = grounding_service.verify_answer("cluster controller heartbeat", answer, evidence)
    assert res.status == GroundingStatus.SUPPORTED
    assert "target" in res.source_chunk_ids

def test_adversarial_11_empty_answer():
    evidence = [{"chunk_id": "c1", "text": "Sample text", "score": 0.80}]
    res = grounding_service.verify_answer("test query", "", evidence)
    assert res.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert res.confidence == 0.0

def test_adversarial_12_very_short_answer():
    evidence = [{"chunk_id": "c1", "text": "Audit logs must be retained for seven years under HIPAA guidelines.", "score": 0.90}]
    res = grounding_service.verify_answer("retention", "Seven years under HIPAA guidelines.", evidence)
    assert res.status == GroundingStatus.SUPPORTED
    assert res.confidence >= 0.60

def test_adversarial_13_bullet_point_answer():
    evidence = [
        {"chunk_id": "c1", "text": "Heartbeat interval is set to 250 milliseconds.", "score": 0.90},
        {"chunk_id": "c2", "text": "Leadership election uses Raft consensus protocol.", "score": 0.85}
    ]
    answer = (
        "### Cluster Settings\n"
        "- Heartbeat interval is set to 250 milliseconds\n"
        "- Leadership election uses Raft consensus protocol"
    )
    res = grounding_service.verify_answer("cluster settings", answer, evidence)
    assert res.status == GroundingStatus.SUPPORTED
    assert len(res.supported_claims) == 2

def test_adversarial_14_multi_sentence_answer():
    evidence = [
        {"chunk_id": "c1", "text": "The incremental backup job executes every 6 hours using WAL archiving to an immutable S3 storage bucket.", "score": 0.88},
        {"chunk_id": "c2", "text": "Full database snapshots are scheduled weekly on Sundays at 02:00 UTC with point-in-time recovery retention guaranteed for 35 days.", "score": 0.86}
    ]
    answer = (
        "Incremental backups execute every 6 hours using WAL archiving. "
        "Full database snapshots are scheduled weekly on Sundays at 02:00 UTC. "
        "Point-in-time recovery retention is guaranteed for 35 days."
    )
    res = grounding_service.verify_answer("backup schedule", answer, evidence)
    assert res.status == GroundingStatus.SUPPORTED
    assert len(res.supported_claims) >= 2

def test_adversarial_15_no_context_question():
    evidence = [{"chunk_id": "c1", "text": "Heartbeat interval is 250 ms.", "score": 0.85}]
    res = grounding_service.verify_answer(
        "Who won the 1998 World Cup?",
        "The answer could not be found in the provided documents.",
        evidence
    )
    assert res.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert res.confidence == 0.0

def test_adversarial_16_duplicate_source_chunks():
    evidence = [
        {"chunk_id": "c1", "text": "Retention period is 7 years.", "score": 0.85},
        {"chunk_id": "c1", "text": "Retention period is 7 years.", "score": 0.85}
    ]
    res = grounding_service.verify_answer("retention", "Retention period is 7 years.", evidence)
    assert res.status == GroundingStatus.SUPPORTED
    assert res.conflicts is None

def test_adversarial_17_conflicting_evidence_with_one_irrelevant_numerical_value():
    evidence = [
        {"chunk_id": "c_ret1", "text": "Mandatory archive retention is 7 years.", "score": 0.90},
        {"chunk_id": "c_ret2", "text": "Mandatory archive retention is 10 years.", "score": 0.88},
        {"chunk_id": "c_port", "text": "Cluster broadcasts over UDP port 7946.", "score": 0.40}
    ]
    res = grounding_service.verify_answer(
        "What is the mandatory archive retention?",
        "Archive retention is 7 years.",
        evidence
    )
    assert res.status == GroundingStatus.CONFLICTING_EVIDENCE
    assert "7946" not in str(res.conflicts)

def test_adversarial_18_dates_with_different_values():
    evidence = [
        {"chunk_id": "d1", "text": "Cold storage compliance policy established on 2024-01-15.", "score": 0.90},
        {"chunk_id": "d2", "text": "Cold storage compliance policy established on 2025-06-01.", "score": 0.88}
    ]
    res = grounding_service.verify_answer(
        "When was the cold storage compliance policy established?",
        "The policy was established on 2024-01-15.",
        evidence
    )
    assert res.status == GroundingStatus.CONFLICTING_EVIDENCE

def test_adversarial_19_percentage_mismatch():
    evidence = [{"chunk_id": "c1", "text": "Daily cache buffer allocation is configured to 25% of total system RAM.", "score": 0.90}]
    res_wrong = grounding_service.verify_answer(
        "What percentage of RAM is allocated to cache?",
        "Cache buffer allocation is configured to 50% of system RAM.",
        evidence
    )
    assert res_wrong.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert len(res_wrong.unsupported_claims) == 1

def test_adversarial_20_storage_size_mismatch():
    evidence = [{"chunk_id": "c1", "text": "Active transaction logs are allocated 500 GB of NVMe SSD storage.", "score": 0.90}]
    # 2 TB instead of 500 GB
    res_wrong = grounding_service.verify_answer(
        "How much storage is allocated for transaction logs?",
        "Active transaction logs are allocated 2 TB of storage.",
        evidence
    )
    assert res_wrong.status == GroundingStatus.INSUFFICIENT_EVIDENCE
    assert len(res_wrong.unsupported_claims) == 1

