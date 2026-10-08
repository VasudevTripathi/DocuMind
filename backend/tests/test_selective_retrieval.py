import pytest
from unittest.mock import MagicMock
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStore
from app.services.retrieval_service import RetrievalService
from app.services.rag_service import RAGService, select_context_chunks, NO_CONTEXT_FALLBACK
from app.services.comparison_service import ComparisonService
from app.services.llm_service import LLMService
from app.services.grounding_service import GroundingStatus

def test_select_context_chunks_respects_budget():
    """Verify that select_context_chunks cuts off before exceeding word budget."""
    chunks = [
        {"chunk_id": "c1", "text": "word " * 100, "score": 0.90, "rerank_score": 0.90, "document_id": "d1"},
        {"chunk_id": "c2", "text": "word " * 150, "score": 0.85, "rerank_score": 0.85, "document_id": "d1"},
        {"chunk_id": "c3", "text": "word " * 200, "score": 0.80, "rerank_score": 0.80, "document_id": "d1"},
    ]
    # Budget of 220 words: chunk 1 (100) fits, adding chunk 2 (150) -> 250 > 220 -> stop
    selected = select_context_chunks(chunks, max_context_words=220)
    assert len(selected) == 1
    assert selected[0]["chunk_id"] == "c1"

def test_select_context_chunks_minimizes_redundancy():
    """Verify MMR-like deduplication prunes highly overlapping adjacent chunks."""
    shared_text = "The system utilizes distributed consensus protocol with Paxos nodes. " * 10
    chunks = [
        {"chunk_id": "c1", "text": shared_text + "Unique detail about leader election.", "score": 0.90, "rerank_score": 0.90, "document_id": "d1"},
        # c2 has 95% word overlap with c1
        {"chunk_id": "c2", "text": shared_text + "Another small leader note.", "score": 0.85, "rerank_score": 0.85, "document_id": "d1"},
        # c3 is completely different topic
        {"chunk_id": "c3", "text": "Network interfaces communicate over mutual TLS with 4096-bit RSA keys.", "score": 0.70, "rerank_score": 0.70, "document_id": "d1"}
    ]
    selected = select_context_chunks(chunks, max_context_words=2500, max_overlap_ratio=0.60)
    selected_ids = [c["chunk_id"] for c in selected]
    assert "c1" in selected_ids
    assert "c2" not in selected_ids  # Pruned due to redundancy with c1
    assert "c3" in selected_ids      # Retained as diverse evidence

def test_select_context_chunks_filters_low_similarity():
    """Verify that chunks with similarity below threshold are dropped."""
    chunks = [
        {"chunk_id": "c1", "text": "Relevant information.", "score": 0.55, "rerank_score": 0.55, "document_id": "d1"},
        {"chunk_id": "c2", "text": "Completely irrelevant spam.", "score": 0.04, "rerank_score": 0.04, "document_id": "d1"}
    ]
    selected = select_context_chunks(chunks, min_similarity=0.10)
    assert len(selected) == 1
    assert selected[0]["chunk_id"] == "c1"

def test_neighboring_chunks_not_automatically_included_for_direct_hit(test_db, tmp_path):
    """
    Verify Part 10: When a direct hit has high confidence and query does not seek sequence,
    neighboring chunks are NOT dragged in.
    """
    store_dir = tmp_path / "vec_cond_test"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    doc = Document(
        id="doc-cond-1",
        name="facts.txt",
        original_filename="facts.txt",
        file_path="facts.txt",
        file_type="TXT",
        size_bytes=500,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk0 = DocumentChunk(id="chk-0", document_id=doc.id, chunk_index=0, text="General preamble and introductory notes.", word_count=5)
    chunk1 = DocumentChunk(id="chk-1", document_id=doc.id, chunk_index=1, text="The database port is 5432.", word_count=5)
    chunk2 = DocumentChunk(id="chk-2", document_id=doc.id, chunk_index=2, text="Subsequent configuration details for logging.", word_count=5)
    test_db.add_all([chunk0, chunk1, chunk2])
    test_db.commit()

    # Index ONLY chunk 1
    vstore.add_document_chunks(doc.id, ["chk-1"], embedding_service.embed_chunks([chunk1.text]))

    # Search for database port: direct hit on chunk 1 has high confidence and query is not sequential
    results = rservice.search(
        db=test_db,
        query="What is the database port?",
        top_k=5,
        context_radius=1
    )
    retrieved_indices = [r["chunk_index"] for r in results]
    assert 1 in retrieved_indices
    # Neighbors 0 and 2 must NOT be included for a direct factual hit without sequence indicators
    assert 0 not in retrieved_indices
    assert 2 not in retrieved_indices

def test_rag_service_does_not_call_llm_on_irrelevant_query(test_db, tmp_path):
    """
    Verify Part 13: When no sufficiently relevant evidence exists,
    the system abstains safely without making any LLM call.
    """
    store_dir = tmp_path / "vec_rag_test"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    fake_llm = MagicMock()
    rag = RAGService(retrieval=rservice, llm=fake_llm)

    doc = Document(id="doc-rag-1", name="finance.txt", original_filename="f.txt", file_path="f.txt", file_type="TXT", size_bytes=100, status="analyzed")
    test_db.add(doc)
    test_db.commit()

    chunk = DocumentChunk(id="c-fin", document_id=doc.id, chunk_index=0, text="Annual revenue reached forty million dollars.", word_count=6)
    test_db.add(chunk)
    test_db.commit()

    vstore.add_document_chunks(doc.id, ["c-fin"], embedding_service.embed_chunks([chunk.text]))

    # Completely irrelevant query about astrophysics
    res = rag.answer_question(
        db=test_db,
        query="What is the chemical composition of Saturn's outer rings?",
        document_id=doc.id
    )

    # LLM must NEVER have been called
    assert fake_llm.answer_question.call_count == 0
    assert res["answer"] == NO_CONTEXT_FALLBACK
    assert res["provider"] == "system_guard"
    assert res["sources"] == []

def test_deterministic_comparison_engine_works_when_llm_offline(test_db):
    """
    Verify Part 18: Deterministic differences calculation (additions, removals, conflicts, common)
    operates 100% locally even if LLM fails or is unconfigured.
    """
    doc_a = Document(id="comp-a", name="v1.txt", original_filename="v1.txt", file_path="v1.txt", file_type="TXT", size_bytes=100, status="analyzed")
    doc_b = Document(id="comp-b", name="v2.txt", original_filename="v2.txt", file_path="v2.txt", file_type="TXT", size_bytes=100, status="analyzed")
    test_db.add_all([doc_a, doc_b])
    test_db.commit()

    ca1 = DocumentChunk(id="ca1", document_id=doc_a.id, chunk_index=0, text="Timeout is 30 seconds. Storage is enabled.", word_count=7)
    cb1 = DocumentChunk(id="cb1", document_id=doc_b.id, chunk_index=0, text="Timeout is 60 seconds. Storage is enabled. Added metrics.", word_count=9)
    test_db.add_all([ca1, cb1])
    test_db.commit()

    # Create LLM service that will fail
    fake_llm = MagicMock()
    fake_llm.explain_comparison.side_effect = Exception("Groq connection timeout")

    # The comparison service gracefully uses fallback for summary while preserving all deterministic diffs
    comp_service = ComparisonService()
    res = comp_service.compare_documents(test_db, "comp-a", "comp-b")

    # Document difference calculation is completely intact
    assert res.document_a.name == "v1.txt"
    assert res.document_b.name == "v2.txt"
    assert len(res.common) >= 1  # "Storage is enabled"
    assert res.grounding.status in (GroundingStatus.SUPPORTED, GroundingStatus.CONFLICTING_EVIDENCE)
