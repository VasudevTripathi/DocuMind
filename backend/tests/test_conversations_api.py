from unittest.mock import patch
import pytest

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services import vector_store as vs_module

def test_conversations_crud_api(client, test_db):
    """Test full CRUD endpoints for conversations."""
    doc = Document(
        id="doc-api-conv",
        name="Manual.pdf",
        original_filename="Manual.pdf",
        file_path="data/uploads/manual.pdf",
        file_type="PDF",
        size_bytes=4096,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    # 1. Create conversation with document_id
    res_create = client.post(
        "/api/conversations",
        json={"document_id": doc.id, "title": "Manual Discussion"}
    )
    assert res_create.status_code == 201
    conv_data = res_create.json()
    conv_id = conv_data["id"]
    assert conv_data["document_id"] == doc.id
    assert conv_data["title"] == "Manual Discussion"
    assert conv_data["message_count"] == 0

    # 2. Create invalid conversation with non-existent document_id
    res_invalid_doc = client.post(
        "/api/conversations",
        json={"document_id": "nonexistent-doc-999"}
    )
    assert res_invalid_doc.status_code == 404

    # 3. List conversations
    res_list = client.get("/api/conversations")
    assert res_list.status_code == 200
    conv_list = res_list.json()
    assert any(c["id"] == conv_id for c in conv_list)

    # 4. List conversations filtered by document_id
    res_filtered = client.get(f"/api/conversations?document_id={doc.id}")
    assert res_filtered.status_code == 200
    filtered_list = res_filtered.json()
    assert len(filtered_list) == 1
    assert filtered_list[0]["id"] == conv_id

    # 5. Get conversation detail
    res_get = client.get(f"/api/conversations/{conv_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["id"] == conv_id
    assert detail["title"] == "Manual Discussion"
    assert detail["messages"] == []

    # 6. Delete conversation
    res_del = client.delete(f"/api/conversations/{conv_id}")
    assert res_del.status_code == 200

    # Verify 404 after deletion
    res_get_del = client.get(f"/api/conversations/{conv_id}")
    assert res_get_del.status_code == 404

    # Delete non-existent returns 404
    res_del_404 = client.delete("/api/conversations/nonexistent-conv-id")
    assert res_del_404.status_code == 404

def test_conversations_messaging_api(client, test_db):
    """Test sending conversational messages, grounding, follow-ups, and sources."""
    doc = Document(
        id="doc-api-chat",
        name="Handbook.txt",
        original_filename="Handbook.txt",
        file_path="data/uploads/handbook.txt",
        file_type="TXT",
        size_bytes=2048,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk1 = DocumentChunk(
        id="chk-api-1",
        document_id=doc.id,
        chunk_index=0,
        text="The annual equipment maintenance audit is scheduled on November 15 every year.",
        page_number=1,
        word_count=11
    )
    test_db.add(chunk1)
    test_db.commit()

    vecs = embedding_service.embed_chunks([chunk1.text])
    vs_module.vector_store.add_document_chunks(doc.id, [chunk1.id], vecs)

    # Create conversation
    res_conv = client.post("/api/conversations", json={"document_id": doc.id})
    conv_id = res_conv.json()["id"]

    # 1. Validation errors
    # Empty content
    res_empty = client.post(f"/api/conversations/{conv_id}/messages", json={"content": ""})
    assert res_empty.status_code in [400, 422]

    # Invalid top_k
    res_topk = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Hello", "top_k": 0})
    assert res_topk.status_code == 422

    # Nonexistent conversation
    res_no_conv = client.post("/api/conversations/invalid-id/messages", json={"content": "Hello"})
    assert res_no_conv.status_code == 404

    # 2. Send valid message with mocked LLM
    with patch("app.services.conversation_service.llm_service.answer_conversational_question") as mock_llm:
        mock_llm.return_value = "The maintenance audit is scheduled on November 15 [Source 1]."

        res_msg = client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "When is the annual equipment maintenance audit scheduled?"}
        )

        assert res_msg.status_code == 200
        msg_data = res_msg.json()
        assert msg_data["role"] == "assistant"
        assert "November 15" in msg_data["content"]
        assert len(msg_data["sources"]) == 1
        assert msg_data["sources"][0]["chunk_id"] == "chk-api-1"
        assert msg_data["sources"][0]["score"] > 0.0

    # 3. Follow-up turn
    with patch("app.services.conversation_service.llm_service.answer_conversational_question") as mock_llm:
        mock_llm.return_value = "Yes, it happens every year on November 15."

        res_followup = client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "Does it repeat annually?"}
        )

        assert res_followup.status_code == 200
        assert "every year" in res_followup.json()["content"]

    # 4. Check conversation detail shows both turns (4 messages total)
    res_detail = client.get(f"/api/conversations/{conv_id}")
    assert res_detail.status_code == 200
    msgs = res_detail.json()["messages"]
    assert len(msgs) == 4
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user"
    assert msgs[3]["role"] == "assistant"

def test_conversations_api_no_context_guard(client, test_db):
    """Test conversational API returns no-context message when retrieval yields no matches."""
    res_conv = client.post("/api/conversations", json={"title": "Unrelated Chat"})
    conv_id = res_conv.json()["id"]

    res_msg = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Who won the 1994 FIFA World Cup?"}
    )

    assert res_msg.status_code == 200
    data = res_msg.json()
    assert data["content"] == "The answer could not be found in the provided documents."
    assert data["sources"] == []
