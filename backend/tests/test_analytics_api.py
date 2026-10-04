import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_library_analytics(client):
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "analyzed_count" in data
    assert "processing_count" in data
    assert "failed_count" in data
    assert "total_chunks" in data
    assert "total_words" in data
    assert "total_size_bytes" in data
    assert "vector_count" in data
    assert "categories" in data
    assert "file_types" in data
    assert "top_entities" in data
    assert "documents" in data
    assert isinstance(data["categories"], dict)
    assert isinstance(data["top_entities"], list)
    assert isinstance(data["documents"], list)

def test_get_document_chunks(client):
    # Retrieve documents to find an existing one
    docs_resp = client.get("/api/documents")
    assert docs_resp.status_code == 200
    docs = docs_resp.json().get("documents", [])
    if docs:
        doc_id = docs[0]["id"]
        chunks_resp = client.get(f"/api/documents/{doc_id}/chunks")
        assert chunks_resp.status_code == 200
        assert isinstance(chunks_resp.json(), list)

    # 404 on nonexistent doc
    non_existent_resp = client.get("/api/documents/non-existent-id/chunks")
    assert non_existent_resp.status_code == 404
