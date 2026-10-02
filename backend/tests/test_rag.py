from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.chunk_service import replace_document_chunks
from app.services.chunker import chunk_document


def test_chunk_records_can_be_persisted(db_session):
    db_session.add(Document(
        id="doc-test",
        name="test.txt",
        original_filename="test.txt",
        file_path="test.txt",
        file_type="TXT",
        size_bytes=4,
    ))
    db_session.commit()

    chunks = chunk_document(
        "doc-test",
        {"text": "alpha beta gamma delta", "pages": []},
        chunk_size_words=2,
        overlap_words=1,
    )
    records = replace_document_chunks(db_session, "doc-test", chunks)
    assert len(records) == 3
    assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == "doc-test").count() == 3
