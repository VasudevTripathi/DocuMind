from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, Union, Tuple
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
    mean_average_precision,
    grounded_answer_rate,
    unsupported_claim_rate,
    numeric_consistency_rate,
    no_context_rejection_rate,
    conflict_detection_rate,
    partial_support_detection_rate,
)
from app.services.grounding_service import grounding_service

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
      - phrase reranking
      - term coverage
      - context expansion
      - Phase 8.1 / 8.3 rerankers
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
class AnswerEvaluationResult:
    total_answers: int
    grounded_answer_rate: float
    unsupported_claim_rate: float
    numeric_consistency_rate: float
    no_context_rejection_rate: float
    conflict_detection_rate: float = 1.0
    partial_support_detection_rate: float = 1.0
    category_summary: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ComparisonResult:
    baseline: EvaluationResult
    enhanced: EvaluationResult
    delta_metrics_by_k: Dict[int, Dict[str, float]]
    delta_mrr: float
    delta_map: float
    category_deltas: Dict[str, Dict[str, float]]
    answer_evaluation: Optional[AnswerEvaluationResult] = None

@dataclass
class ThreeWayComparisonResult:
    baseline: EvaluationResult
    phase81: EvaluationResult
    phase83: EvaluationResult
    delta_81_vs_baseline: Dict[int, Dict[str, float]]
    delta_83_vs_baseline: Dict[int, Dict[str, float]]
    delta_83_vs_81: Dict[int, Dict[str, float]]
    delta_mrr_81_vs_baseline: float
    delta_mrr_83_vs_baseline: float
    delta_mrr_83_vs_81: float
    delta_map_81_vs_baseline: float
    delta_map_83_vs_baseline: float
    delta_map_83_vs_81: float
    category_deltas_81_vs_baseline: Dict[str, Dict[str, float]]
    category_deltas_83_vs_baseline: Dict[str, Dict[str, float]]
    category_deltas_83_vs_81: Dict[str, Dict[str, float]]
    answer_evaluation: Optional[AnswerEvaluationResult] = None

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

    def _calc_deltas(
        self,
        base_res: EvaluationResult,
        target_res: EvaluationResult
    ) -> Tuple[Dict[int, Dict[str, float]], float, float, Dict[str, Dict[str, float]]]:
        delta_metrics_by_k: Dict[int, Dict[str, float]] = {}
        for k in self.k_values:
            b_m = base_res.metrics_by_k.get(k, {})
            t_m = target_res.metrics_by_k.get(k, {})
            delta_metrics_by_k[k] = {
                "hit_rate": t_m.get("hit_rate", 0.0) - b_m.get("hit_rate", 0.0),
                "recall": t_m.get("recall", 0.0) - b_m.get("recall", 0.0),
                "precision": t_m.get("precision", 0.0) - b_m.get("precision", 0.0),
            }

        delta_mrr = target_res.mrr - base_res.mrr
        delta_map = target_res.map_score - base_res.map_score

        category_deltas: Dict[str, Dict[str, float]] = {}
        all_cats = set(base_res.category_metrics.keys()).union(target_res.category_metrics.keys())
        for cat in sorted(all_cats):
            b_cat = base_res.category_metrics.get(cat, {})
            t_cat = target_res.category_metrics.get(cat, {})
            cat_delta: Dict[str, float] = {}
            for k in self.k_values:
                cat_delta[f"hit_at_{k}"] = t_cat.get(f"hit_at_{k}", 0.0) - b_cat.get(f"hit_at_{k}", 0.0)
                cat_delta[f"recall_at_{k}"] = t_cat.get(f"recall_at_{k}", 0.0) - b_cat.get(f"recall_at_{k}", 0.0)
            cat_delta["mrr"] = t_cat.get("mrr", 0.0) - b_cat.get("mrr", 0.0)
            category_deltas[cat] = cat_delta

        return delta_metrics_by_k, delta_mrr, delta_map, category_deltas

    def compare(
        self,
        baseline_result: EvaluationResult,
        enhanced_result: EvaluationResult
    ) -> ComparisonResult:
        """2-way comparison for backwards compatibility."""
        delta_k, delta_mrr, delta_map, cat_deltas = self._calc_deltas(baseline_result, enhanced_result)
        return ComparisonResult(
            baseline=baseline_result,
            enhanced=enhanced_result,
            delta_metrics_by_k=delta_k,
            delta_mrr=delta_mrr,
            delta_map=delta_map,
            category_deltas=cat_deltas
        )

    def compare_three_way(
        self,
        baseline: EvaluationResult,
        phase81: EvaluationResult,
        phase83: EvaluationResult
    ) -> ThreeWayComparisonResult:
        """3-way comparison evaluating Baseline vs Phase 8.1 vs Phase 8.3."""
        d_k_81_b, d_mrr_81_b, d_map_81_b, c_81_b = self._calc_deltas(baseline, phase81)
        d_k_83_b, d_mrr_83_b, d_map_83_b, c_83_b = self._calc_deltas(baseline, phase83)
        d_k_83_81, d_mrr_83_81, d_map_83_81, c_83_81 = self._calc_deltas(phase81, phase83)

        return ThreeWayComparisonResult(
            baseline=baseline,
            phase81=phase81,
            phase83=phase83,
            delta_81_vs_baseline=d_k_81_b,
            delta_83_vs_baseline=d_k_83_b,
            delta_83_vs_81=d_k_83_81,
            delta_mrr_81_vs_baseline=d_mrr_81_b,
            delta_mrr_83_vs_baseline=d_mrr_83_b,
            delta_mrr_83_vs_81=d_mrr_83_81,
            delta_map_81_vs_baseline=d_map_81_b,
            delta_map_83_vs_baseline=d_map_83_b,
            delta_map_83_vs_81=d_map_83_81,
            category_deltas_81_vs_baseline=c_81_b,
            category_deltas_83_vs_baseline=c_83_b,
            category_deltas_83_vs_81=c_83_81
        )

    def evaluate_answers(
        self,
        rag_service: Any,
        db: Session,
        dataset: EvaluationDataset
    ) -> AnswerEvaluationResult:
        """
        Evaluates answer-level grounding, claim support, numeric consistency,
        and no-context rejection across dataset cases.
        """
        statuses: List[str] = []
        supported_counts: List[int] = []
        unsupported_counts: List[int] = []
        consistent_numeric_claims: List[int] = []
        total_numeric_claims: List[int] = []

        total_no_context = 0
        rejected_no_context = 0
        total_contradictions = 0
        detected_contradictions = 0
        total_partial = 0
        detected_partial = 0
        cat_summary: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "supported": 0})

        for case in dataset.cases:
            ans_res = rag_service.answer_question(db=db, query=case.query, top_k=5)
            grounding = ans_res.get("grounding", {})
            status = grounding.get("status", "INSUFFICIENT_EVIDENCE")

            cat_summary[case.category]["count"] += 1
            if status == "SUPPORTED":
                cat_summary[case.category]["supported"] += 1

            if case.category in ("no_context", "abstention"):
                total_no_context += 1
                if status == "INSUFFICIENT_EVIDENCE" or "could not be found" in ans_res.get("answer", "").lower():
                    rejected_no_context += 1
            elif case.category == "contradiction":
                total_contradictions += 1
                if status == "CONFLICTING_EVIDENCE" or len(grounding.get("contradictions", [])) > 0:
                    detected_contradictions += 1
            elif case.category == "partial_support":
                total_partial += 1
                if status == "PARTIALLY_SUPPORTED":
                    detected_partial += 1
                statuses.append(status)
                sup = len(grounding.get("supported_claims", []))
                unsup = len(grounding.get("unsupported_claims", []))
                supported_counts.append(sup)
                unsupported_counts.append(unsup)
            else:
                statuses.append(status)
                sup = len(grounding.get("supported_claims", []))
                unsup = len(grounding.get("unsupported_claims", []))
                supported_counts.append(sup)
                unsupported_counts.append(unsup)

                num_ents = grounding_service.extract_numeric_entities(ans_res.get("answer", ""))
                if num_ents:
                    total_numeric_claims.append(len(num_ents))
                    if status == "SUPPORTED":
                        consistent_numeric_claims.append(len(num_ents))
                    else:
                        consistent_numeric_claims.append(0)

        gar = grounded_answer_rate(statuses)
        ucr = unsupported_claim_rate(supported_counts, unsupported_counts)
        ncr = numeric_consistency_rate(consistent_numeric_claims, total_numeric_claims)
        nrr = no_context_rejection_rate(rejected_no_context, total_no_context)
        cdr = conflict_detection_rate(detected_contradictions, total_contradictions)
        psr = partial_support_detection_rate(detected_partial, total_partial)

        return AnswerEvaluationResult(
            total_answers=len(dataset.cases),
            grounded_answer_rate=gar,
            unsupported_claim_rate=ucr,
            numeric_consistency_rate=ncr,
            no_context_rejection_rate=nrr,
            conflict_detection_rate=cdr,
            partial_support_detection_rate=psr,
            category_summary=dict(cat_summary)
        )
