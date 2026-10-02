import pytest
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services import vector_store as vs_module

def test_search_api_endpoint(client, test_db):
    """
    Test 8: Search endpoint
    POST /api/search returns correctly structured results.
    """
    # Create document
    doc = Document(
        id="doc-api-1",
        name="Attention_Paper.pdf",
        original_filename="Attention_Paper.pdf",
        file_path="data/uploads/Attention_Paper.pdf",
        file_type="PDF",
        size_bytes=1024,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk = DocumentChunk(
        id="chk-api-1",
        document_id=doc.id,
        chunk_index=0,
        text="The feed-forward network consists of two linear transformations with a ReLU activation in between.",
        page_number=3,
        word_count=15
    )
    test_db.add(chunk)
    test_db.commit()

    # Index vector
    vec = embedding_service.embed_chunks([chunk.text])
    vs_module.vector_store.add_document_chunks(doc.id, [chunk.id], vec)

    # 1. Valid search request
    response = client.post(
        "/api/search",
        json={
            "query": "feed-forward linear transformations ReLU",
            "top_k": 5,
            "document_id": None
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "feed-forward linear transformations ReLU"
    assert "results" in data
    assert len(data["results"]) == 1

    first_res = data["results"][0]
    assert first_res["chunk_id"] == "chk-api-1"
    assert first_res["document_id"] == "doc-api-1"
    assert first_res["document_name"] == "Attention_Paper.pdf"
    assert first_res["chunk_index"] == 0
    assert first_res["page_number"] == 3
    assert "feed-forward" in first_res["text"]
    assert "similarity_score" in first_res
    assert isinstance(first_res["similarity_score"], float)

def test_search_api_validation(client, test_db):
    """Test validation errors for empty query, excessive top_k, and nonexistent document."""
    # Empty query -> 422 Unprocessable Entity or 400 Bad Request
    resp_empty = client.post("/api/search", json={"query": "", "top_k": 5})
    assert resp_empty.status_code in [400, 422]

    # top_k exceeds maximum 50 -> 422
    resp_max = client.post("/api/search", json={"query": "test query", "top_k": 500})
    assert resp_max.status_code == 422

    # Nonexistent document ID -> 404 Not Found
    resp_nonexistent = client.post("/api/search", json={"query": "test query", "document_id": "nonexistent-id"})
    assert resp_nonexistent.status_code == 404
