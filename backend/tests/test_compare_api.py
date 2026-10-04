import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services import vector_store as vs_module


def create_api_test_doc(test_db: Session, doc_id: str, name: str, chunk_texts: list[str]) -> Document:
    doc = Document(
        id=doc_id,
        name=name,
        original_filename=name,
        file_path=f"data/uploads/{name}",
        file_type="PDF",
        size_bytes=sum(len(t) for t in chunk_texts),
        status="completed",
        category="Engineering"
    )
    test_db.add(doc)
    test_db.flush()

    for idx, text in enumerate(chunk_texts):
        chunk = DocumentChunk(
            id=f"{doc_id}-chk-{idx}",
            document_id=doc_id,
            chunk_index=idx,
            text=text,
            page_number=1,
            word_count=len(text.split())
        )
        test_db.add(chunk)
    test_db.commit()
    return doc


def test_compare_api_successful_comparison(client, test_db):
    """POST /api/compare returns structured comparison result."""
    doc_a = create_api_test_doc(
        test_db, "doc-api-a", "cluster_v1.pdf",
        ["Storage is 500 GB. Cluster heartbeat interval is 250 milliseconds."]
    )
    doc_b = create_api_test_doc(
        test_db, "doc-api-b", "cluster_v2.pdf",
        ["Storage is 1 TB. Cluster heartbeat interval is 250 milliseconds. Backup retention is 30 days."]
    )

    response = client.post(
        "/api/compare",
        json={
            "document_a_id": doc_a.id,
            "document_b_id": doc_b.id
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert data["document_a"]["id"] == doc_a.id
    assert data["document_b"]["id"] == doc_b.id
    assert "summary" in data
    assert len(data["summary"]) > 0

    # Common
    assert "common" in data
    assert len(data["common"]) >= 1

    # Conflict / Modification
    assert "conflicts" in data
    assert len(data["conflicts"]) >= 1
    conf = data["conflicts"][0]
    assert "500" in conf["document_a"]
    assert "1" in conf["document_b"]
    assert len(conf["sources_a"]) >= 1
    assert len(conf["sources_b"]) >= 1

    # Addition
    assert "additions" in data
    assert len(data["additions"]) >= 1
    assert any("30 days" in a["content"].lower() for a in data["additions"])

    # Sources
    assert "sources" in data
    assert len(data["sources"]) >= 1

    # Grounding
    assert "grounding" in data
    assert data["grounding"]["status"] in ("SUPPORTED", "CONFLICTING_EVIDENCE")


def test_compare_api_identical_documents(client, test_db):
    """POST /api/compare with identical documents returns zero differences."""
    text = "Encryption uses AES-256 with key rotation every 30 days."
    doc_a = create_api_test_doc(test_db, "doc-ident-a", "doc1.txt", [text])
    doc_b = create_api_test_doc(test_db, "doc-ident-b", "doc2.txt", [text])

    response = client.post(
        "/api/compare",
        json={
            "document_a_id": doc_a.id,
            "document_b_id": doc_b.id
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["additions"]) == 0
    assert len(data["removals"]) == 0
    assert len(data["modifications"]) == 0
    assert len(data["conflicts"]) == 0
    assert len(data["common"]) >= 1
    assert "identical" in data["summary"].lower()


def test_compare_api_missing_document_404(client, test_db):
    """POST /api/compare with non-existent document ID returns 404."""
    doc_a = create_api_test_doc(test_db, "doc-exists", "doc1.txt", ["Some content."])

    response = client.post(
        "/api/compare",
        json={
            "document_a_id": doc_a.id,
            "document_b_id": "non-existent-doc-id"
        }
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_compare_api_same_document_400(client, test_db):
    """POST /api/compare with identical IDs for A and B returns 400."""
    doc_a = create_api_test_doc(test_db, "doc-same", "doc1.txt", ["Some content."])

    response = client.post(
        "/api/compare",
        json={
            "document_a_id": doc_a.id,
            "document_b_id": doc_a.id
        }
    )

    assert response.status_code == 400
    assert "must be different documents" in response.json()["detail"].lower()


def test_compare_api_empty_content_400(client, test_db):
    """POST /api/compare with a document having empty chunks returns 400."""
    doc_a = create_api_test_doc(test_db, "doc-empty-chunks", "doc1.txt", ["   "])
    doc_b = create_api_test_doc(test_db, "doc-with-chunks", "doc2.txt", ["Valid text content."])

    response = client.post(
        "/api/compare",
        json={
            "document_a_id": doc_a.id,
            "document_b_id": doc_b.id
        }
    )

    assert response.status_code == 400
    assert "no usable indexed content" in response.json()["detail"].lower()


def test_ask_api_regression_with_compare(client, test_db):
    """Scenario 15: Existing /api/ask continues working normally alongside /api/compare."""
    doc = Document(
        id="doc-reg-ask",
        name="Network_Config.pdf",
        original_filename="Network_Config.pdf",
        file_path="data/uploads/network.pdf",
        file_type="PDF",
        size_bytes=1024,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk = DocumentChunk(
        id="chk-reg-ask-1",
        document_id=doc.id,
        chunk_index=0,
        text="The primary DNS resolver IP is configured as 10.0.0.53.",
        page_number=1,
        word_count=9
    )
    test_db.add(chunk)
    test_db.commit()

    vec = embedding_service.embed_chunks([chunk.text])
    vs_module.vector_store.add_document_chunks(doc.id, [chunk.id], vec)

    response = client.post(
        "/api/ask",
        json={
            "query": "What is the primary DNS resolver IP?",
            "top_k": 3
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "10.0.0.53" in data["answer"]
    assert len(data["sources"]) >= 1
