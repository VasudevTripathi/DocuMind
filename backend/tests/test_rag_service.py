from unittest.mock import MagicMock
import pytest

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStore
from app.services.retrieval_service import RetrievalService, DocumentNotFoundError
from app.services.rag_service import RAGService, NO_CONTEXT_FALLBACK
from app.services.llm_service import LLMService

def test_rag_service_answering_flow(test_db, tmp_path):
    """
    Test A: RAG service retrieves relevant chunks, passes retrieved context to LLM,
    and returns answer and sources.
    """
    store_dir = tmp_path / "vec_rag_test"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    mock_llm = MagicMock(spec=LLMService)
    mock_llm.answer_question.return_value = "Self-attention replaces recurrence by computing direct pairwise connections."

    rag = RAGService(retrieval=rservice, llm=mock_llm)

    # Ingest test document and chunk
    doc = Document(
        id="doc-rag-1",
        name="Attention_Paper.pdf",
        original_filename="Attention_Paper.pdf",
        file_path="data/uploads/attention.pdf",
        file_type="PDF",
        size_bytes=1000,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk = DocumentChunk(
        id="chk-rag-1",
        document_id=doc.id,
        chunk_index=0,
        text="The Transformer relies entirely on self-attention to compute representations without recurrence.",
        page_number=1,
        word_count=13
    )
    test_db.add(chunk)
    test_db.commit()

    emb = embedding_service.embed_chunks([chunk.text])
    vstore.add_document_chunks(doc.id, [chunk.id], emb)

    # Query
    result = rag.answer_question(
        db=test_db,
        query="How does the transformer replace recurrence?",
        top_k=3
    )

    assert result["query"] == "How does the transformer replace recurrence?"
    assert result["answer"] == "Self-attention replaces recurrence by computing direct pairwise connections."
    assert len(result["sources"]) == 1
    assert result["sources"][0]["chunk_id"] == "chk-rag-1"
    assert result["sources"][0]["document_id"] == "doc-rag-1"
    assert result["sources"][0]["document_name"] == "Attention_Paper.pdf"

    # Verify mock LLM was called with the retrieved text in context
    mock_llm.answer_question.assert_called_once()
    call_args = mock_llm.answer_question.call_args[1]
    assert call_args["question"] == "How does the transformer replace recurrence?"
    assert "The Transformer relies entirely on self-attention" in call_args["context"]
    assert "[Source 1]" in call_args["context"]

def test_rag_service_document_scoped_answering(test_db, tmp_path):
    """
    Test B: document_id restricts retrieval and context assembly strictly to that document.
    """
    store_dir = tmp_path / "vec_rag_scoped"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.answer_question.return_value = "Tenant payment is due on the first day of each month."

    rag = RAGService(retrieval=rservice, llm=mock_llm)

    docA = Document(id="doc-A", name="Lease.pdf", original_filename="Lease.pdf", file_path="data/a.pdf", file_type="PDF", size_bytes=500, status="analyzed")
    docB = Document(id="doc-B", name="TechSpec.pdf", original_filename="TechSpec.pdf", file_path="data/b.pdf", file_type="PDF", size_bytes=500, status="analyzed")
    test_db.add_all([docA, docB])
    test_db.commit()

    chunkA = DocumentChunk(id="chk-A", document_id="doc-A", chunk_index=0, text="Monthly rent payment of $2,000 is due on the 1st.", page_number=1, word_count=10)
    chunkB = DocumentChunk(id="chk-B", document_id="doc-B", chunk_index=0, text="Payment processing latency must not exceed 200 milliseconds.", page_number=2, word_count=9)
    test_db.add_all([chunkA, chunkB])
    test_db.commit()

    vstore.add_document_chunks("doc-A", ["chk-A"], embedding_service.embed_chunks([chunkA.text]))
    vstore.add_document_chunks("doc-B", ["chk-B"], embedding_service.embed_chunks([chunkB.text]))

    result = rag.answer_question(
        db=test_db,
        query="What is the payment rule?",
        document_id="doc-A",
        top_k=5
    )

    assert len(result["sources"]) == 1
    assert result["sources"][0]["document_id"] == "doc-A"
    assert result["sources"][0]["chunk_id"] == "chk-A"

    # Context sent to LLM should ONLY contain doc-A
    call_args = mock_llm.answer_question.call_args[1]
    assert "Monthly rent payment" in call_args["context"]
    assert "latency must not exceed" not in call_args["context"]

def test_rag_service_no_context_behavior(test_db, tmp_path):
    """
    Test C: When no relevant chunks exist, LLM is NEVER called and a controlled
    fallback message is returned immediately.
    """
    store_dir = tmp_path / "vec_rag_empty"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)
    mock_llm = MagicMock(spec=LLMService)

    rag = RAGService(retrieval=rservice, llm=mock_llm)

    # Empty store, no documents
    result = rag.answer_question(
        db=test_db,
        query="What is the architecture?",
        top_k=5
    )

    # LLM must NOT be called
    mock_llm.answer_question.assert_not_called()
    assert result["answer"] == NO_CONTEXT_FALLBACK
    assert result["sources"] == []

def test_grounded_prompt_structure():
    """
    Test D: Verify that LLMService uses the dedicated RAG system prompt with strict grounding
    rules rather than the document analysis prompt.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Grounded response citing [Source 1]."
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    service = LLMService(api_key="sk-test-fake-key")
    service._client = mock_client

    context = "[Source 1]\nDocument: Sample.pdf\nContent: The server runs on port 8000."
    answer = service.answer_question(
        question="Which port does the server run on?",
        context=context
    )

    assert answer == "Grounded response citing [Source 1]."
    mock_client.chat.completions.create.assert_called_once()
    create_args = mock_client.chat.completions.create.call_args[1]

    messages = create_args["messages"]
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    user_msg = next(m["content"] for m in messages if m["role"] == "user")

    # Grounding instructions
    assert "Answer using ONLY the supplied document context" in system_msg
    assert "Do not fabricate" in system_msg
    assert "The answer could not be found in the provided documents" in system_msg

    # User message contains context and question
    assert "QUESTION:\nWhich port does the server run on?" in user_msg
    assert "RETRIEVED DOCUMENT CONTEXT:\n" in user_msg
    assert "The server runs on port 8000" in user_msg
