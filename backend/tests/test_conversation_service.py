from unittest.mock import patch, MagicMock
import pytest
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.models.conversation import Conversation, ConversationMessage
from app.services.conversation_service import (
    conversation_service,
    ConversationNotFoundError,
    NO_CONTEXT_FALLBACK
)
from app.services.retrieval_service import DocumentNotFoundError
from app.services.embedding_service import embedding_service
from app.services import vector_store as vs_module
from app.services.document_service import DocumentService

def test_create_and_list_conversations(test_db):
    """Test conversation creation (scoped & global) and listing with filters."""
    doc = Document(
        id="doc-conv-1",
        name="Contract.pdf",
        original_filename="Contract.pdf",
        file_path="data/uploads/contract.pdf",
        file_type="PDF",
        size_bytes=1024,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    # 1. Create document-scoped conversation
    c1 = conversation_service.create_conversation(test_db, document_id="doc-conv-1", title="Contract Review")
    assert c1.id.startswith("conv-")
    assert c1.document_id == "doc-conv-1"
    assert c1.title == "Contract Review"

    # 2. Create global conversation (no document_id)
    c2 = conversation_service.create_conversation(test_db, document_id=None)
    assert c2.id.startswith("conv-")
    assert c2.document_id is None
    assert c2.title == "New Conversation"

    # 3. List all conversations
    all_convs = conversation_service.list_conversations(test_db)
    assert len(all_convs) >= 2

    # 4. List scoped conversations
    scoped = conversation_service.list_conversations(test_db, document_id="doc-conv-1")
    assert len(scoped) == 1
    assert scoped[0].id == c1.id

    # 5. Nonexistent document raises DocumentNotFoundError
    with pytest.raises(DocumentNotFoundError):
        conversation_service.create_conversation(test_db, document_id="nonexistent-doc")

def test_get_and_delete_conversation(test_db):
    """Test retrieving and deleting conversations with message cascading."""
    c = conversation_service.create_conversation(test_db, title="To Delete")
    conv_id = c.id

    # Add message
    msg = ConversationMessage(conversation_id=conv_id, role="user", content="Hello")
    test_db.add(msg)
    test_db.commit()

    # Retrieve
    fetched = conversation_service.get_conversation(test_db, conv_id)
    assert fetched is not None
    assert len(fetched.messages) == 1

    # Delete
    deleted = conversation_service.delete_conversation(test_db, conv_id)
    assert deleted is True

    # Verify conversation and message are deleted
    assert conversation_service.get_conversation(test_db, conv_id) is None
    assert test_db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv_id).count() == 0

    # Deleting again returns False
    assert conversation_service.delete_conversation(test_db, conv_id) is False

def test_conversational_answering_multi_turn_and_history(test_db):
    """
    Test sending initial question and follow-up question:
    - user and assistant messages are persisted in chronological order
    - relevant chunks are retrieved and provided to LLM
    - history is passed to LLM
    - sources are attributed correctly
    """
    doc = Document(
        id="doc-conv-flow",
        name="Specs.txt",
        original_filename="Specs.txt",
        file_path="data/uploads/specs.txt",
        file_type="TXT",
        size_bytes=1024,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk1 = DocumentChunk(
        id="chk-conv-1",
        document_id=doc.id,
        chunk_index=0,
        text="The reactor operating temperature is calibrated strictly at 450 degrees Celsius.",
        page_number=1,
        word_count=10
    )
    chunk2 = DocumentChunk(
        id="chk-conv-2",
        document_id=doc.id,
        chunk_index=1,
        text="When the reactor temperature reaches 500 degrees Celsius, the emergency shutdown coolant valves open automatically.",
        page_number=1,
        word_count=13
    )
    test_db.add_all([chunk1, chunk2])
    test_db.commit()

    # Add vectors
    vecs = embedding_service.embed_chunks([chunk1.text, chunk2.text])
    vs_module.vector_store.add_document_chunks(doc.id, [chunk1.id, chunk2.id], vecs)

    conv = conversation_service.create_conversation(test_db, document_id=doc.id)

    # Turn 1: Initial Question
    with patch("app.services.conversation_service.llm_service.answer_conversational_question") as mock_llm:
        mock_llm.return_value = "The reactor operating temperature is 450 degrees Celsius [Source 1]."

        res1 = conversation_service.post_message(
            db=test_db,
            conversation_id=conv.id,
            content="What is the reactor operating temperature?"
        )

        assert res1["role"] == "assistant"
        assert "450 degrees" in res1["content"]
        assert len(res1["sources"]) > 0
        assert res1["sources"][0]["chunk_id"] == "chk-conv-1"

        # Check LLM call arguments: no history for first turn
        args, kwargs = mock_llm.call_args
        assert kwargs["question"] == "What is the reactor operating temperature?"
        assert "450 degrees Celsius" in kwargs["context"]
        assert kwargs["history"] == []

    # Turn 2: Follow-up question referring to "it" / "temperature"
    with patch("app.services.conversation_service.llm_service.answer_conversational_question") as mock_llm:
        mock_llm.return_value = "The emergency shutdown coolant valves open when it reaches 500 degrees Celsius [Source 1]."

        res2 = conversation_service.post_message(
            db=test_db,
            conversation_id=conv.id,
            content="When do the emergency shutdown coolant valves open?"
        )

        assert res2["role"] == "assistant"
        assert "500 degrees" in res2["content"]
        assert len(res2["sources"]) > 0

        # Check LLM received the history of Turn 1
        args, kwargs = mock_llm.call_args
        history = kwargs["history"]
        assert len(history) == 2  # Turn 1 user + Turn 1 assistant
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "What is the reactor operating temperature?"
        assert history[1]["role"] == "assistant"

    # Verify DB records
    conv_refreshed = conversation_service.get_conversation(test_db, conv.id)
    assert len(conv_refreshed.messages) == 4  # 2 user + 2 assistant
    assert [m.role for m in conv_refreshed.messages] == ["user", "assistant", "user", "assistant"]

def test_no_context_guard_does_not_call_llm(test_db):
    """
    Test no-context behavior:
    When retrieval returns no usable chunks, the system must NOT call LLM.
    The fallback message must be returned and persisted as assistant message.
    """
    conv = conversation_service.create_conversation(test_db, title="No Context Test")

    with patch("app.services.conversation_service.llm_service.answer_conversational_question") as mock_llm:
        res = conversation_service.post_message(
            db=test_db,
            conversation_id=conv.id,
            content="What is the secret recipe of Coca-Cola?"
        )

        # LLM must NOT be called
        mock_llm.assert_not_called()

        assert res["content"] == NO_CONTEXT_FALLBACK
        assert res["sources"] == []

    # Verify persisted in conversation
    conv_refreshed = conversation_service.get_conversation(test_db, conv.id)
    assert len(conv_refreshed.messages) == 2
    assert conv_refreshed.messages[0].role == "user"
    assert conv_refreshed.messages[1].role == "assistant"
    assert conv_refreshed.messages[1].content == NO_CONTEXT_FALLBACK

def test_document_deletion_removes_conversations(test_db):
    """
    Test that deleting a document safely cascades and deletes associated conversations and messages.
    """
    doc = Document(
        id="doc-conv-cascade",
        name="Temporary.txt",
        original_filename="Temporary.txt",
        file_path="data/uploads/temp.txt",
        file_type="TXT",
        size_bytes=100,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    conv = conversation_service.create_conversation(test_db, document_id=doc.id, title="Doc Temp Chat")
    msg = ConversationMessage(conversation_id=conv.id, role="user", content="Hello")
    test_db.add(msg)
    test_db.commit()

    conv_id = conv.id

    # Verify conversation exists
    assert conversation_service.get_conversation(test_db, conv_id) is not None

    # Delete the document through DocumentService
    deleted = DocumentService.delete_document(test_db, doc.id)
    assert deleted is True

    # Verify conversation and messages are gone
    assert conversation_service.get_conversation(test_db, conv_id) is None
    assert test_db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv_id).count() == 0

def test_previous_assistant_answers_not_treated_as_evidence(test_db):
    """
    Test requirement 15: Previous assistant answers are NOT treated as authoritative evidence
    when current retrieval produces no usable supporting context for a follow-up question.
    """
    conv = conversation_service.create_conversation(test_db, title="Evidence Test")

    # Manually add previous turn where assistant said something
    msg1 = ConversationMessage(conversation_id=conv.id, role="user", content="Tell me about the secret.")
    msg2 = ConversationMessage(conversation_id=conv.id, role="assistant", content="The secret code is 12345.")
    test_db.add_all([msg1, msg2])
    test_db.commit()

    # User asks follow-up about that secret code, but document library has no context for it
    with patch("app.services.conversation_service.llm_service.answer_conversational_question") as mock_llm:
        res = conversation_service.post_message(
            db=test_db,
            conversation_id=conv.id,
            content="Can you confirm what the secret code was?"
        )

        # Even though previous assistant message said '12345', because retrieval has no chunks,
        # LLM must NOT be called to hallucinate or treat previous answer as evidence!
        mock_llm.assert_not_called()
        assert res["content"] == NO_CONTEXT_FALLBACK
        assert res["sources"] == []
