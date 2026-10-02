import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.chunk import DocumentChunk

logger = logging.getLogger("documind.chunks")

class ChunkService:
    @staticmethod
    def persist_chunks(
        db: Session,
        document_id: str,
        chunks_data: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """
        Persists a list of chunk data dictionaries for a document into SQLite.
        Expects chunk dictionaries matching chunk_document() output:
        - chunk_index
        - text
        - page_number
        - word_count
        """
        created_chunks: List[DocumentChunk] = []
        for item in chunks_data:
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=item["chunk_index"],
                text=item["text"],
                page_number=item.get("page_number"),
                word_count=item.get("word_count", 0)
            )
            db.add(chunk)
            created_chunks.append(chunk)

        db.flush()
        logger.info(f"[ChunkService] Persisted {len(created_chunks)} chunks for document '{document_id}'.")
        return created_chunks

    @staticmethod
    def get_chunks_by_document_id(db: Session, document_id: str) -> List[DocumentChunk]:
        """Returns all chunks for a document ordered by chunk_index ascending."""
        return (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

    @staticmethod
    def get_chunk_by_id(db: Session, chunk_id: str) -> Optional[DocumentChunk]:
        """Returns a single chunk by chunk ID."""
        return db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()

    @staticmethod
    def get_chunks_by_ids(db: Session, chunk_ids: List[str]) -> List[DocumentChunk]:
        """Returns chunks matching a list of chunk IDs."""
        if not chunk_ids:
            return []
        return db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()

    @staticmethod
    def delete_chunks_by_document(db: Session, document_id: str) -> int:
        """Deletes all chunks belonging to a document. Returns count of deleted chunks."""
        count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)
        db.flush()
        logger.info(f"[ChunkService] Deleted {count} chunks for document '{document_id}'.")
        return count

    @classmethod
    def replace_chunks(
        cls,
        db: Session,
        document_id: str,
        chunks_data: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """
        Idempotently deletes existing chunks for a document and persists new chunks.
        """
        cls.delete_chunks_by_document(db, document_id)
        return cls.persist_chunks(db, document_id, chunks_data)
