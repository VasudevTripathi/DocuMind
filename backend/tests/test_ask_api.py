from unittest.mock import patch
import pytest

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services import vector_store as vs_module

def test_ask_api_successful_response(client, test_db):
    """
    Test E: Valid /api/ask request returns grounded answer and source list.
    """
    doc = Document(
        id="doc-ask-1",
        name="Security_Policy.pdf",
        original_filename="Security_Policy.pdf",
        file_path="data/uploads/security.pdf",
        file_type="PDF",
        size_bytes=2048,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk = DocumentChunk(
        id="chk-ask-1",
        document_id=doc.id,
        chunk_index=0,
        text="Password expiration is enforced every 90 days for all administrative accounts.",
        page_number=2,
        word_count=11
    )
    test_db.add(chunk)
    test_db.commit()

    # Index into vector store
    vec = embedding_service.embed_chunks([chunk.text])
    vs_module.vector_store.add_document_chunks(doc.id, [chunk.id], vec)

    # Mock the LLM answer to return predictable output
    with patch("app.services.rag_service.llm_service.answer_question") as mock_answer:
        mock_answer.return_value = "Passwords expire every 90 days for administrative accounts [Source 1]."

        response = client.post(
            "/api/ask",
            json={
                "query": "How often do admin passwords expire?",
                "top_k": 3,
                "document_id": None
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "How often do admin passwords expire?"
        assert "90 days" in data["answer"]
        assert "sources" in data
        assert len(data["sources"]) == 1

        source = data["sources"][0]
        assert source["document_id"] == "doc-ask-1"
        assert source["chunk_id"] == "chk-ask-1"
        assert source["chunk_index"] == 0
        assert source["score"] > 0.0
        assert "score_breakdown" in source

        # Phase 8.4 Grounding Metadata
        assert "grounding" in data
        assert data["grounding"] is not None
        assert data["grounding"]["status"] == "SUPPORTED"
        assert data["grounding"]["confidence"] > 0.60
        assert len(data["grounding"]["supported_claims"]) >= 1
        assert "chk-ask-1" in data["grounding"]["source_chunk_ids"]

def test_ask_api_validation_errors(client, test_db):
    """
    Test validation errors: empty query, invalid top_k, nonexistent document.
    """
    # 1. Empty query
    resp_empty = client.post("/api/ask", json={"query": "", "top_k": 5})
    assert resp_empty.status_code in [400, 422]

    # 2. top_k too large (> 50)
    resp_large_k = client.post("/api/ask", json={"query": "test query", "top_k": 100})
    assert resp_large_k.status_code == 422

    # 3. top_k too small (< 1)
    resp_zero_k = client.post("/api/ask", json={"query": "test query", "top_k": 0})
    assert resp_zero_k.status_code == 422

    # 4. Nonexistent document ID
    resp_missing_doc = client.post(
        "/api/ask",
        json={"query": "test query", "document_id": "nonexistent-doc-id"}
    )
    assert resp_missing_doc.status_code == 404

def test_ask_api_no_context_graceful_handling(client, test_db):
    """
    When no matching chunks are found in the library, the endpoint responds with
    the controlled fallback message, an empty sources array, and INSUFFICIENT_EVIDENCE grounding.
    """
    response = client.post(
        "/api/ask",
        json={"query": "What is the secret passphrase?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The answer could not be found in the provided documents."
    assert data["sources"] == []
    assert "grounding" in data
    assert data["grounding"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert data["grounding"]["confidence"] == 0.0

def test_ask_api_numeric_mismatch_grounding(client, test_db):
    """
    Test that hallucinated numeric answers are detected as unsupported claims by grounding.
    """
    doc = Document(
        id="doc-ask-num",
        name="Retention_Policy.pdf",
        original_filename="Retention_Policy.pdf",
        file_path="data/uploads/retention.pdf",
        file_type="PDF",
        size_bytes=1024,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk = DocumentChunk(
        id="chk-ask-num-1",
        document_id=doc.id,
        chunk_index=0,
        text="All customer transaction logs must be retained for 7 years.",
        page_number=1,
        word_count=10
    )
    test_db.add(chunk)
    test_db.commit()

    vec = embedding_service.embed_chunks([chunk.text])
    vs_module.vector_store.add_document_chunks(doc.id, [chunk.id], vec)

    # Mock LLM answering with an incorrect number (10 years instead of 7 years)
    with patch("app.services.rag_service.llm_service.answer_question") as mock_answer:
        mock_answer.return_value = "Customer transaction logs must be retained for 10 years."

        response = client.post(
            "/api/ask",
            json={"query": "What is the transaction log retention period?", "top_k": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["grounding"]["status"] == "INSUFFICIENT_EVIDENCE"
        assert len(data["grounding"]["unsupported_claims"]) == 1
        assert len(data["grounding"]["supported_claims"]) == 0

def test_ask_api_conflicting_evidence_grounding(client, test_db):
    """
    Test that contradictory chunks in evidence produce CONFLICTING_EVIDENCE status.
    """
    doc = Document(
        id="doc-ask-conflict",
        name="Conflicting_Policy.pdf",
        original_filename="Conflicting_Policy.pdf",
        file_path="data/uploads/conflict.pdf",
        file_type="PDF",
        size_bytes=1024,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk1 = DocumentChunk(
        id="chk-ask-c1",
        document_id=doc.id,
        chunk_index=0,
        text="The mandatory server backup retention period is 7 years.",
        page_number=1,
        word_count=9
    )
    chunk2 = DocumentChunk(
        id="chk-ask-c2",
        document_id=doc.id,
        chunk_index=1,
        text="The mandatory server backup retention period is 10 years.",
        page_number=2,
        word_count=9
    )
    test_db.add_all([chunk1, chunk2])
    test_db.commit()

    vecs = embedding_service.embed_chunks([chunk1.text, chunk2.text])
    vs_module.vector_store.add_document_chunks(doc.id, [chunk1.id, chunk2.id], vecs)

    with patch("app.services.rag_service.llm_service.answer_question") as mock_answer:
        mock_answer.return_value = "The backup retention period is 7 years."

        response = client.post(
            "/api/ask",
            json={"query": "What is the server backup retention period?", "top_k": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["grounding"]["status"] == "CONFLICTING_EVIDENCE"
        assert "chk-ask-c1" in data["grounding"]["source_chunk_ids"]
        assert "chk-ask-c2" in data["grounding"]["source_chunk_ids"]
        assert data["grounding"]["conflicts"] is not None
