from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk


def replace_document_chunks(db: Session, document_id: str, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Replace all persisted chunks for a document atomically within the caller's transaction."""
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)

    records = [
        DocumentChunk(
            document_id=document_id,
            chunk_index=chunk["chunk_index"],
            text=chunk["text"],
            page_number=chunk.get("page_number"),
            word_count=chunk["word_count"],
        )
        for chunk in chunks
        if chunk.get("text")
    ]
    db.add_all(records)
    db.flush()
    return records
