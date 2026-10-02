import pytest
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStore
from app.services.retrieval_service import RetrievalService

def test_context_expansion_radius_and_boundary_guards(test_db, tmp_path):
    """
    Test context expansion radius=1:
    - Chunk index 0 does NOT produce negative index -1.
    - Final chunk index does NOT exceed document chunk count.
    - Intermediate chunk expands to neighbors (N-1, N, N+1).
    - Duplicates are consolidated.
    """
    store_dir = tmp_path / "vec_exp_test"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    doc = Document(
        id="doc-exp-1",
        name="Sequential.txt",
        original_filename="Sequential.txt",
        file_path="data/uploads/seq.txt",
        file_type="TXT",
        size_bytes=1000,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk_texts = [
        "First step: Initialize the primary database node.",          # index 0
        "Second step: Synchronize replicas with write-ahead log.",    # index 1
        "Third step: Enable external client traffic through gateway." # index 2
    ]

    chunks = []
    for i, t in enumerate(chunk_texts):
        c = DocumentChunk(
            id=f"chk-seq-{i}",
            document_id=doc.id,
            chunk_index=i,
            text=t,
            page_number=1,
            word_count=len(t.split())
        )
        test_db.add(c)
        chunks.append(c)
    test_db.commit()

    # Index ONLY chunk 0 and chunk 2 into vector store in a single call (chunk 1 not in FAISS index)
    vstore.add_document_chunks(
        doc.id,
        ["chk-seq-0", "chk-seq-2"],
        embedding_service.embed_chunks([chunk_texts[0], chunk_texts[2]])
    )

    # 1. Search for chunk 0 with radius=1
    # FAISS retrieves chunk 0. Neighbors within radius=1 are -1 (skipped!) and +1 (chunk 1).
    # It must NOT produce negative chunk index -1.
    results_0 = rservice.search(
        db=test_db,
        query="Initialize primary database node",
        top_k=5,
        context_radius=1
    )
    retrieved_indices_0 = [r["chunk_index"] for r in results_0]
    assert -1 not in retrieved_indices_0
    assert 0 in retrieved_indices_0
    assert 1 in retrieved_indices_0
    # No duplicate chunk IDs
    assert len(results_0) == len(set(r["chunk_id"] for r in results_0))

    # 2. Search for chunk 2 with radius=1
    # FAISS retrieves chunk 2. Neighbors are 1 and 3 (index 3 does not exist in DB, so safely omitted).
    results_2 = rservice.search(
        db=test_db,
        query="external client traffic gateway",
        top_k=5,
        context_radius=1
    )
    retrieved_indices_2 = [r["chunk_index"] for r in results_2]
    assert 2 in retrieved_indices_2
    assert 1 in retrieved_indices_2
    assert 3 not in retrieved_indices_2

def test_expansion_strictly_document_scoped(test_db, tmp_path):
    """
    Ensure context expansion never crosses document boundaries:
    Retrieving chunk 0 of Document A must never expand to chunk 1 of Document B.
    """
    store_dir = tmp_path / "vec_scope_test"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    docA = Document(id="doc-A-scope", name="DocA.txt", original_filename="DocA.txt", file_path="A.txt", file_type="TXT", size_bytes=100, status="analyzed")
    docB = Document(id="doc-B-scope", name="DocB.txt", original_filename="DocB.txt", file_path="B.txt", file_type="TXT", size_bytes=100, status="analyzed")
    test_db.add_all([docA, docB])
    test_db.commit()

    chunkA0 = DocumentChunk(id="chk-A-0", document_id=docA.id, chunk_index=0, text="Document A introductory section.", page_number=1, word_count=5)
    chunkA1 = DocumentChunk(id="chk-A-1", document_id=docA.id, chunk_index=1, text="Document A conclusion section.", page_number=1, word_count=5)
    chunkB0 = DocumentChunk(id="chk-B-0", document_id=docB.id, chunk_index=0, text="Document B completely unrelated content.", page_number=1, word_count=5)
    chunkB1 = DocumentChunk(id="chk-B-1", document_id=docB.id, chunk_index=1, text="Document B appendix details.", page_number=1, word_count=5)
    test_db.add_all([chunkA0, chunkA1, chunkB0, chunkB1])
    test_db.commit()

    vstore.add_document_chunks(docA.id, [chunkA0.id], embedding_service.embed_chunks([chunkA0.text]))
    vstore.add_document_chunks(docB.id, [chunkB0.id], embedding_service.embed_chunks([chunkB0.text]))

    # Search scoped to docA
    results = rservice.search(
        db=test_db,
        query="introductory section",
        top_k=5,
        document_id=docA.id,
        context_radius=1
    )

    # Every retrieved chunk must strictly belong to docA
    for r in results:
        assert r["document_id"] == "doc-A-scope"
        assert r["document_id"] != "doc-B-scope"

def test_candidate_k_and_final_k_bounds(test_db, tmp_path):
    """Verify candidate_k >= final_k and final results are bounded by final_k (top_k)."""
    store_dir = tmp_path / "vec_k_bounds"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    doc = Document(id="doc-k", name="DocK.txt", original_filename="DocK.txt", file_path="K.txt", file_type="TXT", size_bytes=500, status="analyzed")
    test_db.add(doc)
    test_db.commit()

    chunks = []
    chunk_ids = []
    for i in range(10):
        c = DocumentChunk(
            id=f"chk-k-{i}",
            document_id=doc.id,
            chunk_index=i,
            text=f"System operation step {i} details and protocols.",
            page_number=1,
            word_count=7
        )
        test_db.add(c)
        chunks.append(c)
        chunk_ids.append(c.id)
    test_db.commit()

    embeddings = embedding_service.embed_chunks([c.text for c in chunks])
    vstore.add_document_chunks(doc.id, chunk_ids, embeddings)

    # Request top_k = 3
    results = rservice.search(
        db=test_db,
        query="System operation step protocols",
        top_k=3,
        candidate_k=8,
        context_radius=1
    )

    assert len(results) == 3

def test_reranking_prioritizes_lexical_overlap_in_evidence(test_db, tmp_path):
    """
    Verify that reranking prioritizes chunks with relevant lexical matches
    before final evidence selection.
    """
    store_dir = tmp_path / "vec_rerank_evidence"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    doc = Document(id="doc-re", name="DocRE.txt", original_filename="DocRE.txt", file_path="RE.txt", file_type="TXT", size_bytes=200, status="analyzed")
    test_db.add(doc)
    test_db.commit()

    # Chunk 0 has general concept, Chunk 1 has exact specific terms
    c0 = DocumentChunk(id="chk-re-0", document_id=doc.id, chunk_index=0, text="General server parameters and settings.", page_number=1, word_count=5)
    c1 = DocumentChunk(id="chk-re-1", document_id=doc.id, chunk_index=1, text="The critical telemetry threshold is calibrated at ninety percent.", page_number=1, word_count=9)
    test_db.add_all([c0, c1])
    test_db.commit()

    vstore.add_document_chunks(doc.id, [c0.id, c1.id], embedding_service.embed_chunks([c0.text, c1.text]))

    results = rservice.search(
        db=test_db,
        query="critical telemetry threshold calibrated",
        top_k=1
    )

    assert len(results) == 1
    assert results[0]["chunk_id"] == "chk-re-1"
    assert results[0]["lexical_score"] > 0.5
    assert results[0]["rerank_score"] > 0.0
