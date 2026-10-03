"""
DocuMind RAG Evaluation Package.
Provides local, deterministic evaluation datasets, metrics, evaluators, and reporting.
"""

from app.evaluation.dataset import EvaluationCase, EvaluationDataset, get_evaluation_dataset
from app.evaluation.metrics import (
    hit_rate_at_k,
    recall_at_k,
    precision_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
    average_precision_at_k,
    mean_average_precision,
)
from app.evaluation.evaluator import (
    BaselineRetriever,
    RAGEvaluator,
    CaseResult,
    EvaluationResult,
    ComparisonResult,
)
from app.evaluation.report import format_evaluation_report

__all__ = [
    "EvaluationCase",
    "EvaluationDataset",
    "get_evaluation_dataset",
    "hit_rate_at_k",
    "recall_at_k",
    "precision_at_k",
    "reciprocal_rank",
    "mean_reciprocal_rank",
    "average_precision_at_k",
    "mean_average_precision",
    "BaselineRetriever",
    "RAGEvaluator",
    "CaseResult",
    "EvaluationResult",
    "ComparisonResult",
    "format_evaluation_report",
]
