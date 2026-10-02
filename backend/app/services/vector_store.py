import json
import logging
import os
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import faiss
import numpy as np

from app.core.config import settings

logger = logging.getLogger("documind.vector_store")

class VectorStore:
    """
    Local FAISS vector store with cosine similarity semantics (IndexFlatIP with normalized vectors).
    Maintains a 1-to-1 position mapping from FAISS vector positions to DocumentChunk IDs.
    Persists:
      - index.faiss
      - metadata.json (stores chunk_id and document_id per position)
    """

    def __init__(self, vector_store_dir: Optional[Path] = None, dimension: int = 384):
        self.vector_store_dir = vector_store_dir or settings.resolved_vector_store_dir
        self.dimension = dimension
        self.index_file = self.vector_store_dir / "index.faiss"
        self.metadata_file = self.vector_store_dir / "metadata.json"
        self._lock = threading.Lock()
        self.index: Optional[faiss.IndexFlatIP] = None
        self.records: List[Dict[str, str]] = []  # Index i -> {"chunk_id": ..., "document_id": ...}
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        """Loads index and metadata from disk if available, otherwise initializes an empty index."""
        with self._lock:
            self.vector_store_dir.mkdir(parents=True, exist_ok=True)
            if self.index_file.exists() and self.metadata_file.exists():
                try:
                    loaded_index = faiss.read_index(str(self.index_file))
                    with open(self.metadata_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    records = meta.get("records", [])
                    dim = meta.get("dimension", loaded_index.d)

                    if loaded_index.ntotal != len(records):
                        logger.warning(
                            f"[VectorStore] Mismatch between index vectors ({loaded_index.ntotal}) "
                            f"and metadata records ({len(records)}). Initializing clean index."
                        )
                        self._reset_index(dim)
                    else:
                        self.index = loaded_index
                        self.dimension = dim
                        self.records = records
                        logger.info(
                            f"[VectorStore] Loaded index with {self.index.ntotal} vectors "
                            f"(dimension={self.dimension}) from {self.vector_store_dir}."
                        )
                        return
                except Exception as e:
                    logger.error(f"[VectorStore] Error loading vector store from disk: {e}. Reinitializing.", exc_info=True)

            self._reset_index(self.dimension)

    def _reset_index(self, dimension: int) -> None:
        """Initializes a fresh empty IndexFlatIP and persists it."""
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.records = []
        self._persist_locked()

    def _persist_locked(self) -> None:
        """Persists the current FAISS index and metadata.json (must be called inside self._lock)."""
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))

        meta = {
            "dimension": self.dimension,
            "total_vectors": len(self.records),
            "records": self.records
        }
        tmp_meta = self.metadata_file.with_suffix(".tmp")
        with open(tmp_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        tmp_meta.replace(self.metadata_file)

    def count(self) -> int:
        """Returns total vectors stored in the index."""
        with self._lock:
            return self.index.ntotal if self.index else 0

    def add_document_chunks(
        self,
        document_id: str,
        chunk_ids: List[str],
        vectors: np.ndarray
    ) -> int:
        """
        Idempotently adds chunks and their embedding vectors for a document.
        If vectors for document_id already exist, they are removed first to prevent duplicates.
        """
        if len(chunk_ids) == 0:
            return 0

        if vectors.shape[0] != len(chunk_ids):
            raise ValueError(f"Vector count ({vectors.shape[0]}) does not match chunk count ({len(chunk_ids)}).")

        with self._lock:
            # 1. Remove existing document vectors if present (idempotent replacement)
            self._remove_document_locked(document_id)

            # Ensure correct dimension and type
            if self.index.d != vectors.shape[1]:
                # If index was empty and dimension changed, reconfigure index dimension
                if self.index.ntotal == 0:
                    self.dimension = vectors.shape[1]
                    self.index = faiss.IndexFlatIP(self.dimension)
                else:
                    raise ValueError(
                        f"Vector dimension {vectors.shape[1]} does not match index dimension {self.index.d}."
                    )

            # Ensure float32 and normalized
            float_vecs = np.ascontiguousarray(vectors, dtype=np.float32)
            norms = np.linalg.norm(float_vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            float_vecs = float_vecs / norms

            # 2. Add vectors to FAISS
            self.index.add(float_vecs)

            # 3. Append to records mapping
            for cid in chunk_ids:
                self.records.append({
                    "chunk_id": cid,
                    "document_id": document_id
                })

            # 4. Persist to disk
            self._persist_locked()
            logger.info(f"[VectorStore] Added {len(chunk_ids)} vectors for document '{document_id}'. Total: {self.index.ntotal}")
            return len(chunk_ids)

    def remove_document(self, document_id: str) -> int:
        """Removes all vectors belonging to a given document ID."""
        with self._lock:
            count = self._remove_document_locked(document_id)
            if count > 0:
                self._persist_locked()
            return count

    def _remove_document_locked(self, document_id: str) -> int:
        """Internal helper to remove document vectors without re-acquiring lock."""
        indices_to_remove = [
            i for i, rec in enumerate(self.records)
            if rec.get("document_id") == document_id
        ]

        if not indices_to_remove:
            return 0

        # If removing all items, reset cleanly
        if len(indices_to_remove) == len(self.records):
            count = len(self.records)
            self.index.reset()
            self.records = []
            logger.info(f"[VectorStore] Removed all {count} vectors from index for document '{document_id}'.")
            return count

        # FAISS remove_ids removes specific indices and shifts subsequent indices down
        remove_arr = np.array(indices_to_remove, dtype=np.int64)
        self.index.remove_ids(remove_arr)

        # Update records mapping by filtering out the removed indices
        remove_set = set(indices_to_remove)
        self.records = [rec for i, rec in enumerate(self.records) if i not in remove_set]

        logger.info(f"[VectorStore] Removed {len(indices_to_remove)} vectors for document '{document_id}'. Remaining: {self.index.ntotal}")
        return len(indices_to_remove)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Executes similarity search on the FAISS index.
        Returns list of (chunk_id, similarity_score) tuples, sorted by similarity descending.
        """
        with self._lock:
            if self.index is None or self.index.ntotal == 0 or not self.records:
                return []

            # Normalize query vector
            q = np.ascontiguousarray(query_vector.reshape(1, -1), dtype=np.float32)
            norm = np.linalg.norm(q)
            if norm > 0:
                q = q / norm

            # Document scoping
            if document_id:
                matching_indices = [
                    i for i, rec in enumerate(self.records)
                    if rec.get("document_id") == document_id
                ]
                if not matching_indices:
                    return []

                sel = faiss.IDSelectorArray(np.array(matching_indices, dtype=np.int64))
                params = faiss.SearchParameters(sel=sel)
                k = min(top_k, len(matching_indices))
                distances, indices = self.index.search(q, k, params=params)
            else:
                k = min(top_k, self.index.ntotal)
                distances, indices = self.index.search(q, k)

            results: List[Tuple[str, float]] = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.records):
                    continue
                chunk_id = self.records[idx]["chunk_id"]
                score = round(float(dist), 4)
                results.append((chunk_id, score))

            return results

    def rebuild_index(self, items: List[Tuple[str, str, np.ndarray]]) -> int:
        """
        Rebuilds the entire index from scratch using provided list of (chunk_id, document_id, vector).
        Useful for recovery, testing, or migration.
        """
        with self._lock:
            dim = self.dimension
            if items:
                dim = items[0][2].shape[0]

            self.index = faiss.IndexFlatIP(dim)
            self.dimension = dim
            self.records = []

            if items:
                chunk_ids = [it[0] for it in items]
                doc_ids = [it[1] for it in items]
                vectors = np.array([it[2] for it in items], dtype=np.float32)

                # Normalize
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                vectors = vectors / norms

                self.index.add(vectors)
                for cid, did in zip(chunk_ids, doc_ids):
                    self.records.append({"chunk_id": cid, "document_id": did})

            self._persist_locked()
            logger.info(f"[VectorStore] Rebuilt index with {len(items)} vectors.")
            return len(items)

    def rebuild_from_db(self, db, embedder=None) -> int:
        """
        Authoritatively rebuilds the FAISS index and metadata directly from SQLite document chunks.
        Ensures perfect synchronization between SQLite and FAISS.
        """
        from app.models.chunk import DocumentChunk
        if embedder is None:
            from app.services.embedding_service import embedding_service
            embedder = embedding_service

        chunks = (
            db.query(DocumentChunk)
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            .all()
        )

        if not chunks:
            self.clear()
            return 0

        texts = [c.text for c in chunks]
        vectors = embedder.embed_chunks(texts)
        items = [(c.id, c.document_id, vectors[i]) for i, c in enumerate(chunks)]
        return self.rebuild_index(items)

    def clear(self) -> None:
        """Clears all vectors and resets the index files."""
        with self._lock:
            self._reset_index(self.dimension)

vector_store = VectorStore()
