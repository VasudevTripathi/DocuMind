import json
import logging
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embed_query, embed_texts, get_embedding_model

logger = logging.getLogger("documind.vector_store")


class VectorStore:
    """Persistent local FAISS index backed by SQLite chunk metadata."""

    def __init__(self) -> None:
        self.root = Path(settings.resolved_upload_dir).parent / "vector"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.faiss"
        self.metadata_path = self.root / "metadata.json"
        self._lock = RLock()
        self._index: Optional[faiss.Index] = None
        self._metadata: List[str] = []

    def _load(self) -> None:
        if self._index is not None:
            return
        if self.index_path.exists() and self.metadata_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        else:
            self._index = None
            self._metadata = []

    def _persist(self) -> None:
        if self._index is None:
            if self.index_path.exists():
                self.index_path.unlink()
            if self.metadata_path.exists():
                self.metadata_path.unlink()
            return
        faiss.write_index(self._index, str(self.index_path))
        self.metadata_path.write_text(json.dumps(self._metadata), encoding="utf-8")

    def rebuild(self, db: Session) -> int:
        """Rebuild the complete vector index from authoritative SQLite chunks."""
        with self._lock:
            chunks = db.query(DocumentChunk).order_by(DocumentChunk.document_id, DocumentChunk.chunk_index).all()
            if not chunks:
                self._index = None
                self._metadata = []
                self._persist()
                return 0

            texts = [chunk.text for chunk in chunks]
            vectors = np.asarray(embed_texts(texts), dtype="float32")
            dimension = vectors.shape[1]
            index = faiss.IndexFlatIP(dimension)
            index.add(vectors)
            self._index = index
            self._metadata = [chunk.id for chunk in chunks]
            self._persist()
            logger.info("Rebuilt FAISS index with %d chunks", len(chunks))
            return len(chunks)

    def ensure_ready(self, db: Session) -> None:
        with self._lock:
            self._load()
            expected = db.query(DocumentChunk).count()
            if expected != len(self._metadata):
                self.rebuild(db)

    def search(self, db: Session, query: str, top_k: int = 5, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        top_k = max(1, min(top_k, 20))

        with self._lock:
            self.ensure_ready(db)
            if self._index is None or not self._metadata:
                return []

            query_vector = np.asarray([embed_query(query)], dtype="float32")
            candidate_k = min(max(top_k * 5, top_k), len(self._metadata))
            scores, positions = self._index.search(query_vector, candidate_k)

            chunk_ids = []
            score_by_id: Dict[str, float] = {}
            for score, position in zip(scores[0], positions[0]):
                if position < 0 or position >= len(self._metadata):
                    continue
                chunk_id = self._metadata[position]
                chunk_ids.append(chunk_id)
                score_by_id[chunk_id] = float(score)

            if document_id:
                allowed = {
                    row.id
                    for row in db.query(DocumentChunk.id).filter(DocumentChunk.document_id == document_id).all()
                }
                chunk_ids = [cid for cid in chunk_ids if cid in allowed]

            chunk_ids = chunk_ids[:top_k]
            if not chunk_ids:
                return []

            rows = db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()
            by_id = {row.id: row for row in rows}

            return [
                {
                    "chunk_id": row.id,
                    "document_id": row.document_id,
                    "text": row.text,
                    "page_number": row.page_number,
                    "chunk_index": row.chunk_index,
                    "word_count": row.word_count,
                    "score": round(score_by_id.get(row.id, 0.0), 6),
                }
                for cid in chunk_ids
                if (row := by_id.get(cid)) is not None
            ]


vector_store = VectorStore()
