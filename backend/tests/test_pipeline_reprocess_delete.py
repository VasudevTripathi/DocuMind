import os
from pathlib import Path
import pytest

from app.core.config import settings
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.chunk_service import ChunkService
from app.services.vector_store import VectorStore
from app.services.document_service import DocumentService
from app.services.document_pipeline import process_document

def test_pipeline_reprocessing_and_deletion(test_db, monkeypatch, tmp_path):
    """
    Test 6 & 7: Reprocessing idempotency and clean deletion.
    """
    # Configure test directories
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    vector_dir = tmp_path / "vector_store"
    vector_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(uploads_dir))
    monkeypatch.setattr(settings, "VECTOR_STORE_DIR", str(vector_dir))

    from app.services import vector_store as vs_module
    test_vs = VectorStore(vector_store_dir=vector_dir, dimension=384)
    monkeypatch.setattr(vs_module, "vector_store", test_vs)
    from app.services import document_pipeline as dp_module
    monkeypatch.setattr(dp_module, "vector_store", test_vs)
    from app.services import document_service as ds_module
    monkeypatch.setattr(ds_module, "vector_store", test_vs)

    # Create dummy text file
    sample_filename = "reprocess_sample.txt"
    sample_file_path = uploads_dir / sample_filename
    sample_content = (
        "DocuMind provides advanced document intelligence and local vector retrieval. "
        "The system processes documents into semantic chunks and generates embeddings. "
        "SQLite acts as the source of truth while FAISS accelerates retrieval."
    )
    with open(sample_file_path, "w", encoding="utf-8") as f:
        f.write(sample_content)

    doc = Document(
        id="doc-reprocess-test",
        name=sample_filename,
        original_filename=sample_filename,
        file_path=str(sample_file_path),
        file_type="TXT",
        size_bytes=len(sample_content.encode("utf-8")),
        status="pending"
    )
    test_db.add(doc)
    test_db.commit()

    # 1. Process document first time
    success_1 = process_document(doc.id, db=test_db)
    assert success_1 is True

    test_db.refresh(doc)
    assert doc.status == "analyzed"
    chunks_1 = ChunkService.get_chunks_by_document_id(test_db, doc.id)
    initial_chunk_count = len(chunks_1)
    assert initial_chunk_count > 0
    assert test_vs.count() == initial_chunk_count

    # 2. Process document second time (Reprocessing)
    success_2 = process_document(doc.id, db=test_db)
    assert success_2 is True

    test_db.refresh(doc)
    assert doc.status == "analyzed"
    chunks_2 = ChunkService.get_chunks_by_document_id(test_db, doc.id)
    assert len(chunks_2) == initial_chunk_count
    # Verify no vector duplication
    assert test_vs.count() == initial_chunk_count

    # 3. Document Deletion
    deleted = DocumentService.delete_document(test_db, doc.id)
    assert deleted is True

    # Verify: Chunks gone
    remaining_chunks = test_db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    assert len(remaining_chunks) == 0

    # Verify: Vectors removed
    assert test_vs.count() == 0

    # Verify: Document gone from SQLite
    remaining_doc = test_db.query(Document).filter(Document.id == doc.id).first()
    assert remaining_doc is None

    # Verify: Physical file gone
    assert not sample_file_path.exists()
