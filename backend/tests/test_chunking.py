import pytest
from sqlalchemy.exc import IntegrityError
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.chunker import chunk_document
from app.services.chunk_service import ChunkService

def test_chunking_contract_alpha_beta_gamma_delta(test_db):
    """
    Test 1: Chunk persistence
    Given: 'alpha beta gamma delta'
    with chunk size 2 and overlap 1:
    Expected: 3 chunks
    """
    doc = Document(
        id="doc-test-1",
        name="test.txt",
        original_filename="test.txt",
        file_path="data/uploads/test.txt",
        file_type="TXT",
        size_bytes=100,
        status="pending"
    )
    test_db.add(doc)
    test_db.commit()

    parsed_data = {
        "text": "alpha beta gamma delta",
        "pages": []
    }

    # Generate chunks using canonical chunker
    chunks = chunk_document(
        document_id=doc.id,
        parsed_data=parsed_data,
        chunk_size_words=2,
        overlap_words=1
    )

    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert chunks[0]["text"] == "alpha beta"
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["text"] == "beta gamma"
    assert chunks[1]["chunk_index"] == 1
    assert chunks[2]["text"] == "gamma delta"
    assert chunks[2]["chunk_index"] == 2

    # Persist in SQLite
    persisted = ChunkService.persist_chunks(test_db, doc.id, chunks)
    test_db.commit()

    assert len(persisted) == 3
    retrieved = ChunkService.get_chunks_by_document_id(test_db, doc.id)
    assert len(retrieved) == 3
    assert [c.chunk_index for c in retrieved] == [0, 1, 2]
    assert [c.text for c in retrieved] == ["alpha beta", "beta gamma", "gamma delta"]

def test_chunk_duplicate_ordering_prevention(test_db):
    """Verify that duplicate (document_id, chunk_index) is prevented by DB constraints."""
    doc = Document(
        id="doc-test-dup",
        name="test_dup.txt",
        original_filename="test_dup.txt",
        file_path="data/uploads/test_dup.txt",
        file_type="TXT",
        size_bytes=50,
        status="pending"
    )
    test_db.add(doc)
    test_db.commit()

    c1 = DocumentChunk(document_id=doc.id, chunk_index=0, text="first chunk", word_count=2)
    test_db.add(c1)
    test_db.commit()

    c2 = DocumentChunk(document_id=doc.id, chunk_index=0, text="duplicate index chunk", word_count=3)
    test_db.add(c2)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()

def test_chunk_replace_and_delete(test_db):
    """Verify replace_chunks and delete_chunks_by_document."""
    doc = Document(
        id="doc-test-rep",
        name="test_rep.txt",
        original_filename="test_rep.txt",
        file_path="data/uploads/test_rep.txt",
        file_type="TXT",
        size_bytes=50,
        status="pending"
    )
    test_db.add(doc)
    test_db.commit()

    initial_chunks = [
        {"chunk_index": 0, "text": "initial 1", "word_count": 2},
        {"chunk_index": 1, "text": "initial 2", "word_count": 2},
    ]
    ChunkService.persist_chunks(test_db, doc.id, initial_chunks)
    test_db.commit()
    assert len(ChunkService.get_chunks_by_document_id(test_db, doc.id)) == 2

    # Replace with single new chunk
    new_chunks = [
        {"chunk_index": 0, "text": "replacement chunk", "word_count": 2}
    ]
    replaced = ChunkService.replace_chunks(test_db, doc.id, new_chunks)
    test_db.commit()

    assert len(replaced) == 1
    chunks = ChunkService.get_chunks_by_document_id(test_db, doc.id)
    assert len(chunks) == 1
    assert chunks[0].text == "replacement chunk"

    # Delete chunks
    deleted_count = ChunkService.delete_chunks_by_document(test_db, doc.id)
    test_db.commit()
    assert deleted_count == 1
    assert len(ChunkService.get_chunks_by_document_id(test_db, doc.id)) == 0
