import pytest
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.vector_store import VectorStore
from app.services.retrieval_service import RetrievalService, DocumentNotFoundError

def test_semantic_retrieval_transformer_example(test_db, tmp_path):
    """
    Test 4: Semantic retrieval
    Create several chunks:
    - 'The transformer architecture uses self-attention.'
    - 'Quarterly revenue increased by 18 percent.'
    - 'Tenant agrees to arbitration.'
    Query: 'How does the transformer architecture work?'
    The transformer chunk should be retrieved as top result.
    """
    store_dir = tmp_path / "vec_retrieval"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    doc = Document(
        id="doc-ret-1",
        name="ai_paper.pdf",
        original_filename="ai_paper.pdf",
        file_path="data/uploads/ai_paper.pdf",
        file_type="PDF",
        size_bytes=5000,
        status="analyzed"
    )
    test_db.add(doc)
    test_db.commit()

    chunk_texts = [
        "The transformer architecture uses self-attention.",
        "Quarterly revenue increased by 18 percent.",
        "Tenant agrees to arbitration."
    ]

    chunks = []
    for i, t in enumerate(chunk_texts):
        c = DocumentChunk(
            id=f"chk-ret-{i}",
            document_id=doc.id,
            chunk_index=i,
            text=t,
            page_number=1,
            word_count=len(t.split())
        )
        test_db.add(c)
        chunks.append(c)
    test_db.commit()

    # Embed and index
    embeddings = embedding_service.embed_chunks(chunk_texts)
    vstore.add_document_chunks(doc.id, [c.id for c in chunks], embeddings)

    # Execute semantic search
    results = rservice.search(
        db=test_db,
        query="How does the transformer architecture work?",
        top_k=3
    )

    assert len(results) == 3
    top_hit = results[0]
    assert top_hit["chunk_id"] == "chk-ret-0"
    assert "transformer architecture" in top_hit["text"].lower()
    assert top_hit["document_name"] == "ai_paper.pdf"
    assert top_hit["similarity_score"] > 0.4
    assert top_hit["similarity_score"] > results[1]["similarity_score"]

def test_document_scoped_retrieval(test_db, tmp_path):
    """
    Test 5: Document-scoped retrieval
    Ensure a query scoped to document A cannot return chunks from document B.
    """
    store_dir = tmp_path / "vec_scoped"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    rservice = RetrievalService(store=vstore, embedder=embedding_service)

    docA = Document(
        id="doc-A",
        name="Contract_A.pdf",
        original_filename="Contract_A.pdf",
        file_path="data/uploads/contract_a.pdf",
        file_type="PDF",
        size_bytes=2000,
        status="analyzed"
    )
    docB = Document(
        id="doc-B",
        name="Financial_Report_B.pdf",
        original_filename="Financial_Report_B.pdf",
        file_path="data/uploads/report_b.pdf",
        file_type="PDF",
        size_bytes=3000,
        status="analyzed"
    )
    test_db.add_all([docA, docB])
    test_db.commit()

    chunkA = DocumentChunk(
        id="chk-A-0",
        document_id=docA.id,
        chunk_index=0,
        text="Tenant agrees to pay monthly rent by the first calendar day.",
        page_number=1,
        word_count=10
    )
    chunkB = DocumentChunk(
        id="chk-B-0",
        document_id=docB.id,
        chunk_index=0,
        text="Total enterprise recurring revenue grew by 24 percent year over year.",
        page_number=1,
        word_count=11
    )
    test_db.add_all([chunkA, chunkB])
    test_db.commit()

    embA = embedding_service.embed_chunks([chunkA.text])
    embB = embedding_service.embed_chunks([chunkB.text])

    vstore.add_document_chunks(docA.id, [chunkA.id], embA)
    vstore.add_document_chunks(docB.id, [chunkB.id], embB)

    # Scoped search to docA
    results_A = rservice.search(
        db=test_db,
        query="What is the revenue growth rate?",
        top_k=5,
        document_id=docA.id
    )

    # Even though query is financial (matches docB better), scoping to docA MUST only return docA
    assert len(results_A) == 1
    assert results_A[0]["document_id"] == "doc-A"
    assert results_A[0]["chunk_id"] == "chk-A-0"

    # Scoped search to nonexistent doc should raise DocumentNotFoundError
    with pytest.raises(DocumentNotFoundError):
        rservice.search(
            db=test_db,
            query="test query",
            document_id="nonexistent-doc-999"
        )
