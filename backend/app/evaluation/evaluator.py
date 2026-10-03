from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk
from app.services.vector_store import VectorStore
from app.services.embedding_service import BaseEmbeddingService, embedding_service
from app.services.retrieval_service import RetrievalService, retrieval_service
from app.evaluation.dataset import EvaluationCase, EvaluationDataset
from app.evaluation.metrics import (
    hit_rate_at_k,
    recall_at_k,
    precision_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
    average_precision_at_k,
    mean_average_precision
)

class SearchableRetriever(Protocol):
    def search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        document_id: Optional[str] = None,
        min_similarity: Optional[float] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        ...

class BaselineRetriever:
    """
    Semantic-only retriever representing retrieval before Phase 8.1.
    Query -> embedding -> FAISS semantic search -> top K.
    Strictly avoids:
      - lexical reranking
      - context expansion
      - Phase 8.1 reranker
    """
    def __init__(
        self,
        store: VectorStore,
        embedder: BaseEmbeddingService = embedding_service
    ):
        self.vector_store = store
        self.embedding_service = embedder

    def search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = 5,
        document_id: Optional[str] = None,
        min_similarity: Optional[float] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        final_k = top_k if top_k is not None else 5
        query_vector = self.embedding_service.embed_text(cleaned_query)

        hits = self.vector_store.search(
            query_vector=query_vector,
            top_k=final_k,
            document_id=document_id
        )
        if not hits:
            return []

        if min_similarity is not None:
            hits = [(cid, score) for cid, score in hits if score >= min_similarity]

        if not hits:
            return []

        chunk_ids = [cid for cid, _ in hits]
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.id.in_(chunk_ids))
            .all()
        )
        chunks_by_id = {c.id: c for c in chunks}

        results: List[Dict[str, Any]] = []
        for cid, score in hits:
            chunk = chunks_by_id.get(cid)
            if chunk:
                results.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "text": chunk.text,
                    "similarity_score": score,
                    "semantic_score": score
                })
        return results

@dataclass
class CaseResult:
    case_id: str
    query: str
    category: str
    retrieved_chunk_ids: List[str]
    relevant_chunk_ids: List[str]
    hit: float
    reciprocal_rank: float
    recall: float
    precision: float
    hit_at_k: Dict[int, float] = field(default_factory=dict)
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    precision_at_k: Dict[int, float] = field(default_factory=dict)

@dataclass
class EvaluationResult:
    retriever_name: str
    total_cases: int
    metrics_by_k: Dict[int, Dict[str, float]]
    mrr: float
    map_score: float
    category_metrics: Dict[str, Dict[str, Any]]
    case_results: List[CaseResult]

@dataclass
class ComparisonResult:
    baseline: EvaluationResult
    enhanced: EvaluationResult
    delta_metrics_by_k: Dict[int, Dict[str, float]]
    delta_mrr: float
    delta_map: float
    category_deltas: Dict[str, Dict[str, float]]

class RAGEvaluator:
    """Runs deterministic evaluation across evaluation cases for any given retriever."""

    def __init__(self, k_values: Sequence[int] = (1, 3, 5)):
        self.k_values = sorted(list(k_values))
        self.max_k = max(self.k_values) if self.k_values else 5

    def evaluate(
        self,
        retriever: SearchableRetriever,
        retriever_name: str,
        db: Session,
        dataset: EvaluationDataset,
        min_similarity: Optional[float] = None
    ) -> EvaluationResult:
        case_results: List[CaseResult] = []
        rr_scores: List[float] = []
        ap_scores: List[float] = []

        hits_by_k: Dict[int, List[float]] = {k: [] for k in self.k_values}
        recalls_by_k: Dict[int, List[float]] = {k: [] for k in self.k_values}
        precisions_by_k: Dict[int, List[float]] = {k: [] for k in self.k_values}

        cat_cases: Dict[str, List[CaseResult]] = defaultdict(list)

        for case in dataset.cases:
            results = retriever.search(
                db=db,
                query=case.query,
                top_k=self.max_k,
                min_similarity=min_similarity
            )
            retrieved_chunk_ids = [r["chunk_id"] for r in results]

            case_hits: Dict[int, float] = {}
            case_recalls: Dict[int, float] = {}
            case_precisions: Dict[int, float] = {}

            for k in self.k_values:
                h = hit_rate_at_k(retrieved_chunk_ids, case.relevant_chunk_ids, k)
                r = recall_at_k(retrieved_chunk_ids, case.relevant_chunk_ids, k)
                p = precision_at_k(retrieved_chunk_ids, case.relevant_chunk_ids, k)

                case_hits[k] = h
                case_recalls[k] = r
                case_precisions[k] = p

                hits_by_k[k].append(h)
                recalls_by_k[k].append(r)
                precisions_by_k[k].append(p)

            rr = reciprocal_rank(retrieved_chunk_ids, case.relevant_chunk_ids)
            ap = average_precision_at_k(retrieved_chunk_ids, case.relevant_chunk_ids, k=self.max_k)
            rr_scores.append(rr)
            ap_scores.append(ap)

            c_res = CaseResult(
                case_id=case.case_id,
                query=case.query,
                category=case.category,
                retrieved_chunk_ids=retrieved_chunk_ids,
                relevant_chunk_ids=case.relevant_chunk_ids,
                hit=case_hits.get(self.max_k, 0.0),
                reciprocal_rank=rr,
                recall=case_recalls.get(self.max_k, 0.0),
                precision=case_precisions.get(self.max_k, 0.0),
                hit_at_k=case_hits,
                recall_at_k=case_recalls,
                precision_at_k=case_precisions
            )
            case_results.append(c_res)
            cat_cases[case.category].append(c_res)

        total_cases = len(case_results)
        metrics_by_k: Dict[int, Dict[str, float]] = {}
        for k in self.k_values:
            metrics_by_k[k] = {
                "hit_rate": sum(hits_by_k[k]) / float(total_cases) if total_cases > 0 else 0.0,
                "recall": sum(recalls_by_k[k]) / float(total_cases) if total_cases > 0 else 0.0,
                "precision": sum(precisions_by_k[k]) / float(total_cases) if total_cases > 0 else 0.0,
            }

        mrr = mean_reciprocal_rank(rr_scores)
        map_score = mean_average_precision(ap_scores)

        # Category breakdowns
        category_metrics: Dict[str, Dict[str, Any]] = {}
        for cat, cases in cat_cases.items():
            cat_total = len(cases)
            cat_metrics: Dict[str, Any] = {"count": cat_total}
            for k in self.k_values:
                cat_metrics[f"hit_at_{k}"] = sum(c.hit_at_k.get(k, 0.0) for c in cases) / float(cat_total)
                cat_metrics[f"recall_at_{k}"] = sum(c.recall_at_k.get(k, 0.0) for c in cases) / float(cat_total)
                cat_metrics[f"precision_at_{k}"] = sum(c.precision_at_k.get(k, 0.0) for c in cases) / float(cat_total)
            cat_metrics["mrr"] = sum(c.reciprocal_rank for c in cases) / float(cat_total)
            category_metrics[cat] = cat_metrics

        return EvaluationResult(
            retriever_name=retriever_name,
            total_cases=total_cases,
            metrics_by_k=metrics_by_k,
            mrr=mrr,
            map_score=map_score,
            category_metrics=category_metrics,
            case_results=case_results
        )

    def compare(
        self,
        baseline_result: EvaluationResult,
        enhanced_result: EvaluationResult
    ) -> ComparisonResult:
        """Computes deltas (enhanced - baseline) across all metrics and categories."""
        delta_metrics_by_k: Dict[int, Dict[str, float]] = {}
        for k in self.k_values:
            b_m = baseline_result.metrics_by_k.get(k, {})
            e_m = enhanced_result.metrics_by_k.get(k, {})
            delta_metrics_by_k[k] = {
                "hit_rate": e_m.get("hit_rate", 0.0) - b_m.get("hit_rate", 0.0),
                "recall": e_m.get("recall", 0.0) - b_m.get("recall", 0.0),
                "precision": e_m.get("precision", 0.0) - b_m.get("precision", 0.0),
            }

        delta_mrr = enhanced_result.mrr - baseline_result.mrr
        delta_map = enhanced_result.map_score - baseline_result.map_score

        category_deltas: Dict[str, Dict[str, float]] = {}
        all_cats = set(baseline_result.category_metrics.keys()).union(enhanced_result.category_metrics.keys())
        for cat in sorted(all_cats):
            b_cat = baseline_result.category_metrics.get(cat, {})
            e_cat = enhanced_result.category_metrics.get(cat, {})
            cat_delta: Dict[str, float] = {}
            for k in self.k_values:
                cat_delta[f"hit_at_{k}"] = e_cat.get(f"hit_at_{k}", 0.0) - b_cat.get(f"hit_at_{k}", 0.0)
                cat_delta[f"recall_at_{k}"] = e_cat.get(f"recall_at_{k}", 0.0) - b_cat.get(f"recall_at_{k}", 0.0)
            cat_delta["mrr"] = e_cat.get("mrr", 0.0) - b_cat.get("mrr", 0.0)
            category_deltas[cat] = cat_delta

        return ComparisonResult(
            baseline=baseline_result,
            enhanced=enhanced_result,
            delta_metrics_by_k=delta_metrics_by_k,
            delta_mrr=delta_mrr,
            delta_map=delta_map,
            category_deltas=category_deltas
        )
