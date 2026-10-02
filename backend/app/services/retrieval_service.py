import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.embedding_service import embedding_service, BaseEmbeddingService
from app.services.vector_store import vector_store, VectorStore

logger = logging.getLogger("documind.retrieval")

class DocumentNotFoundError(Exception):
    """Raised when a requested document ID does not exist in SQLite."""
    pass

class RetrievalService:
    """
    Coordinates semantic search:
    1. Embeds query text locally
    2. Searches FAISS vector index (with optional document scoping)
    3. Looks up chunk records and document metadata in SQLite
    4. Formats structured retrieval results ordered by similarity score
    """

    def __init__(
        self,
        store: VectorStore = vector_store,
        embedder: BaseEmbeddingService = embedding_service
    ):
        self.vector_store = store
        self.embedding_service = embedder

    def search(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic retrieval.
        Raises ValueError if query is empty.
        Raises DocumentNotFoundError if document_id is provided but not found in the DB.
        """
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            raise ValueError("Query string cannot be empty.")

        # If scoped to a document, verify document exists in DB
        if document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise DocumentNotFoundError(f"Document with ID '{document_id}' was not found.")

        # 1. Embed query
        query_vector = self.embedding_service.embed_text(cleaned_query)

        # 2. FAISS similarity search
        hits = self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            document_id=document_id
        )

        if not hits:
            return []

        # 3. Retrieve chunks from SQLite
        chunk_ids = [chunk_id for chunk_id, _ in hits]
        chunks = (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.id.in_(chunk_ids))
            .all()
        )
        chunk_map = {c.id: c for c in chunks}

        # 4. Assemble ordered results
        results: List[Dict[str, Any]] = []
        for chunk_id, score in hits:
            chunk = chunk_map.get(chunk_id)
            if not chunk:
                continue

            doc_name = chunk.document.name if chunk.document else "Unknown"
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": doc_name,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "similarity_score": score,
                "score": score
            })

        logger.info(f"[RetrievalService] Query '{cleaned_query[:40]}' returned {len(results)} results (scoped to: {document_id}).")
        return results

retrieval_service = RetrievalService()
