import logging
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.embedding_service import embedding_service, BaseEmbeddingService
from app.services.vector_store import vector_store, VectorStore
from app.services.reranker import reranker, RetrievalReranker

logger = logging.getLogger("documind.retrieval")

class DocumentNotFoundError(Exception):
    """Raised when a requested document ID does not exist in SQLite."""
    pass

class RetrievalService:
    """
    Coordinates upgraded semantic retrieval and reranking:
    1. Embeds query text locally via sentence-transformers
    2. Searches FAISS vector index for initial candidates (with document scoping)
    3. Fetches candidate chunks from SQLite
    4. Performs document-scoped context expansion (including neighboring chunks within radius)
    5. Applies deterministic lexical + semantic reranking
    6. Filters candidates using relevance guard
    7. Returns top-k evidence chunks
    """

    def __init__(
        self,
        store: VectorStore = vector_store,
        embedder: BaseEmbeddingService = embedding_service,
        rerank_service: RetrievalReranker = reranker
    ):
        self.vector_store = store
        self.embedding_service = embedder
        self.reranker = rerank_service

    def _expand_context(
        self,
        db: Session,
        candidate_chunks: List[DocumentChunk],
        chunk_similarity_scores: Dict[str, float],
        radius: int,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Conditionally expands context by adding neighboring chunks strictly within
        the same document boundaries.

        Rules (Part 10):
        - High confidence direct hit (>= 0.75) without sequence indicators: use direct chunk only.
        - Medium confidence hit (0.25 to 0.75) or questions/content needing surrounding context: expand.
        - Low confidence hit (< 0.25): do not expand to prevent noise accumulation.
        - Never crosses document boundaries, never produces negative indices, deduplicates results.
        """
        if radius <= 0 or not candidate_chunks:
            # No expansion requested
            results = []
            for c in candidate_chunks:
                score = chunk_similarity_scores.get(c.id, 0.0)
                doc_name = c.document.name if c.document else "Unknown"
                results.append({
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "document_name": doc_name,
                    "chunk_index": c.chunk_index,
                    "page_number": c.page_number,
                    "text": c.text,
                    "similarity_score": score,
                    "semantic_score": score,
                    "is_expanded": False,
                    "context_distance": 0
                })
            return results

        # Evaluate query and context triggers
        import re
        context_triggers = {
            "before", "after", "next", "following", "preceding", "context",
            "surrounding", "continue", "sequence", "procedure", "process",
            "workflow", "step", "steps", "phase", "overview"
        }
        q_tokens = set(re.findall(r"\b\w+\b", (query or "").lower()))
        query_needs_surrounding = bool(q_tokens & context_triggers)

        # Track loaded chunks and needed indices per document
        loaded_by_doc_index: Dict[Tuple[str, int], DocumentChunk] = {}
        target_indices_by_doc: Dict[str, Set[int]] = defaultdict(set)
        parent_scores_by_doc_index: Dict[Tuple[str, int], float] = {}

        for c in candidate_chunks:
            doc_id = c.document_id
            idx = c.chunk_index
            score = chunk_similarity_scores.get(c.id, 0.0)

            loaded_by_doc_index[(doc_id, idx)] = c
            parent_scores_by_doc_index[(doc_id, idx)] = score

            # Evaluate whether expansion is warranted for this candidate
            c_text_lower = (c.text or "").lower()
            chunk_has_sequence = bool(re.search(
                r"\b(step\s+\d+|phase\s+\d+|section\s+\d+|first\s+step|second\s+step|third\s+step)\b",
                c_text_lower
            ))

            is_high_confidence = score >= 0.75
            is_low_confidence = score < 0.25

            should_expand = False
            if not is_low_confidence:
                if not is_high_confidence or query_needs_surrounding or chunk_has_sequence:
                    should_expand = True

            if should_expand:
                # Collect neighbor targets within radius
                for offset in range(-radius, radius + 1):
                    target_idx = idx + offset
                    if target_idx >= 0:  # Do not produce negative chunk indexes
                        target_indices_by_doc[doc_id].add(target_idx)
                        neighbor_key = (doc_id, target_idx)
                        discount_rate = getattr(settings, "RAG_CONTEXT_DISCOUNT", 0.80)
                        discounted_score = max(0.0, score * (discount_rate ** abs(offset)))
                        if neighbor_key not in parent_scores_by_doc_index or discounted_score > parent_scores_by_doc_index[neighbor_key]:
                            parent_scores_by_doc_index[neighbor_key] = discounted_score

        # Query missing neighbor chunks from SQLite
        for doc_id, indices in target_indices_by_doc.items():
            missing_indices = [idx for idx in indices if (doc_id, idx) not in loaded_by_doc_index]
            if missing_indices:
                neighbors = (
                    db.query(DocumentChunk)
                    .options(joinedload(DocumentChunk.document))
                    .filter(
                        DocumentChunk.document_id == doc_id,
                        DocumentChunk.chunk_index.in_(missing_indices)
                    )
                    .all()
                )
                for nc in neighbors:
                    loaded_by_doc_index[(nc.document_id, nc.chunk_index)] = nc

        # Assemble deduplicated candidate list
        assembled_candidates: List[Dict[str, Any]] = []
        seen_chunk_ids: Set[str] = set()

        for (doc_id, idx), chunk in loaded_by_doc_index.items():
            if chunk.id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.id)

            # Direct FAISS hit score takes precedence over discounted parent score
            final_sim_score = chunk_similarity_scores.get(
                chunk.id,
                parent_scores_by_doc_index.get((doc_id, idx), 0.0)
            )
            doc_name = chunk.document.name if chunk.document else "Unknown"

            is_direct_hit = chunk.id in chunk_similarity_scores
            assembled_candidates.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": doc_name,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "similarity_score": final_sim_score,
                "semantic_score": final_sim_score,
                "is_expanded": not is_direct_hit,
                "context_distance": 0 if is_direct_hit else 1
            })

        return assembled_candidates

    def search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        document_id: Optional[str] = None,
        candidate_k: Optional[int] = None,
        context_radius: Optional[int] = None,
        min_similarity: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes upgraded semantic retrieval:
        1. Embed query
        2. Candidate retrieval from FAISS
        3. Context expansion (neighboring chunks within radius) strictly within document
        4. Lightweight deterministic reranking (semantic + lexical overlap)
        5. Relevance threshold guard (if min_similarity is set or by default for evidence)
        6. Returns top-k evidence chunks
        """
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            raise ValueError("Query string cannot be empty.")

        # If scoped to a document, verify document exists in DB
        if document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise DocumentNotFoundError(f"Document with ID '{document_id}' was not found.")

        final_k = top_k if top_k is not None else settings.RAG_FINAL_K
        eff_candidate_k = candidate_k if candidate_k is not None else max(settings.RAG_CANDIDATE_K, final_k)
        eff_radius = context_radius if context_radius is not None else settings.RAG_CONTEXT_RADIUS

        # 1. Embed query
        query_vector = self.embedding_service.embed_text(cleaned_query)

        # 2. FAISS candidate similarity search
        hits = self.vector_store.search(
            query_vector=query_vector,
            top_k=eff_candidate_k,
            document_id=document_id
        )

        if not hits:
            return []

        # 3. Retrieve initial candidate chunks from SQLite
        chunk_ids = [chunk_id for chunk_id, _ in hits]
        chunk_similarity_scores = {chunk_id: score for chunk_id, score in hits}

        chunks = (
            db.query(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .filter(DocumentChunk.id.in_(chunk_ids))
            .all()
        )
        if not chunks:
            return []

        # 4. Context expansion (neighboring chunks within radius, scoped strictly to document)
        expanded_candidates = self._expand_context(
            db=db,
            candidate_chunks=chunks,
            chunk_similarity_scores=chunk_similarity_scores,
            radius=eff_radius,
            query=cleaned_query
        )

        # 5. Deterministic reranking (semantic + lexical overlap)
        reranked_results = self.reranker.rerank(cleaned_query, expanded_candidates)

        # 6. Relevance guard: if min_similarity specified, filter out candidates below threshold
        if min_similarity is not None:
            usable_results = [
                r for r in reranked_results
                if r["similarity_score"] >= min_similarity and r["rerank_score"] >= min_similarity
            ]
        else:
            usable_results = reranked_results

        # 7. Select final top-k evidence chunks
        final_results = usable_results[:final_k]

        logger.info(
            f"[RetrievalService] Query '{cleaned_query[:40]}' retrieved {len(hits)} candidates, "
            f"expanded to {len(expanded_candidates)}, reranked to {len(final_results)} final evidence chunks."
        )
        return final_results

retrieval_service = RetrievalService()
