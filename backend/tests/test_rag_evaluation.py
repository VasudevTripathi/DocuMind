import pytest
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.services.vector_store import VectorStore
from app.services.embedding_service import embedding_service
from app.services.reranker import reranker
from app.services.retrieval_service import RetrievalService
from app.evaluation.dataset import (
    EvaluationCase,
    EvaluationDataset,
    get_evaluation_dataset,
    EVALUATION_CASES,
    EVALUATION_DOCUMENTS
)
from app.evaluation.evaluator import (
    BaselineRetriever,
    RAGEvaluator,
    CaseResult,
    EvaluationResult,
    ComparisonResult
)
from app.evaluation.report import format_evaluation_report

class StubRetriever:
    """Deterministic stub retriever for testing evaluator mechanics without model inference."""
    def __init__(self, return_map: Dict[str, List[str]]):
        self.return_map = return_map

    def search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = 5,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        cids = self.return_map.get(query, [])
        limit = top_k if top_k is not None else len(cids)
        return [{"chunk_id": cid, "score": 0.9} for cid in cids[:limit]]

def test_evaluation_dataset_structure_and_categories():
    dataset = get_evaluation_dataset()
    assert len(dataset.documents) >= 4
    assert len(dataset.cases) >= 10

    categories = {case.category for case in dataset.cases}
    required_categories = {
        "direct_fact",
        "semantic_match",
        "lexical_match",
        "contextual_question",
        "adjacent_chunk",
        "no_context"
    }
    assert required_categories.issubset(categories)

    for case in dataset.cases:
        assert isinstance(case.case_id, str) and case.case_id
        assert isinstance(case.query, str) and case.query
        assert isinstance(case.category, str) and case.category
        assert isinstance(case.relevant_chunk_ids, list)
        assert isinstance(case.expected_answer_facts, list)
        if case.category == "no_context":
            assert len(case.relevant_chunk_ids) == 0

def test_evaluator_aggregation_and_comparison_logic():
    cases = [
        EvaluationCase(
            case_id="case-1",
            query="query 1",
            relevant_document_id="doc-1",
            relevant_chunk_ids=["chk-1", "chk-2"],
            expected_answer_facts=["fact 1"],
            category="direct_fact"
        ),
        EvaluationCase(
            case_id="case-2",
            query="query 2",
            relevant_document_id="doc-2",
            relevant_chunk_ids=["chk-3"],
            expected_answer_facts=["fact 2"],
            category="lexical_match"
        )
    ]
    test_ds = EvaluationDataset(cases=cases)

    # Baseline retriever finds chk-1 for query 1, and fails query 2
    baseline_stub = StubRetriever({
        "query 1": ["chk-1", "other-1", "other-2"],
        "query 2": ["other-3", "other-4", "other-5"]
    })

    # Enhanced retriever finds chk-1 and chk-2 for query 1, and chk-3 for query 2
    enhanced_stub = StubRetriever({
        "query 1": ["chk-1", "chk-2", "other-2"],
        "query 2": ["chk-3", "other-4", "other-5"]
    })

    evaluator = RAGEvaluator(k_values=[1, 3, 5])
    db_dummy = None  # StubRetriever doesn't touch DB

    b_res = evaluator.evaluate(baseline_stub, "Baseline", db_dummy, test_ds)
    e_res = evaluator.evaluate(enhanced_stub, "Enhanced", db_dummy, test_ds)

    assert b_res.total_cases == 2
    assert e_res.total_cases == 2

    # Query 1: relevant=["chk-1", "chk-2"]. Baseline has ["chk-1", "other-1", "other-2"] -> Recall@3 = 1/2 = 0.5
    # Query 2: relevant=["chk-3"]. Baseline has 0 hits -> Recall@3 = 0.0
    # Mean Recall@3 for baseline = (0.5 + 0.0) / 2 = 0.25
    assert b_res.metrics_by_k[3]["recall"] == 0.25

    # Enhanced: Query 1 Recall@3 = 2/2 = 1.0; Query 2 Recall@3 = 1/1 = 1.0 -> Mean = 1.0
    assert e_res.metrics_by_k[3]["recall"] == 1.0

    # Comparison / delta calculation
    comparison = evaluator.compare(b_res, e_res)
    assert comparison.delta_metrics_by_k[3]["recall"] == 0.75
    assert comparison.delta_mrr > 0.0

    # Verify report formatting
    report = format_evaluation_report(comparison)
    assert "RAG EVALUATION REPORT" in report
    assert "BASELINE — Semantic Retrieval" in report
    assert "PHASE 8.1 — Enhanced Retrieval" in report
    assert "DELTA (Phase 8.1 - Baseline)" in report
    assert "CATEGORY RESULTS" in report

    # Verify no subjective words
    for subjective in ["excellent", "poor", "best", "bad", "superior"]:
        assert subjective not in report.lower()

def test_baseline_retriever_scoping_and_behavior(test_db, tmp_path):
    store_dir = tmp_path / "vec_baseline_test"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    base_retriever = BaselineRetriever(store=vstore, embedder=embedding_service)

    doc = Document(id="doc-base", name="TestDoc.txt", original_filename="TestDoc.txt", file_path="t.txt", file_type="TXT", size_bytes=100, status="analyzed")
    test_db.add(doc)
    test_db.commit()

    chunk1 = DocumentChunk(id="chk-b-1", document_id="doc-base", chunk_index=0, text="Redis cache cluster configuration.", word_count=4)
    chunk2 = DocumentChunk(id="chk-b-2", document_id="doc-base", chunk_index=1, text="PostgreSQL replica sync settings.", word_count=4)
    test_db.add_all([chunk1, chunk2])
    test_db.commit()

    vstore.add_document_chunks("doc-base", ["chk-b-1", "chk-b-2"], embedding_service.embed_chunks([chunk1.text, chunk2.text]))

    results = base_retriever.search(db=test_db, query="Redis cache", top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "chk-b-1"
    # Ensure baseline does NOT expand neighbor chunk_index=1
    assert len(results) == 1

def test_full_dataset_population_and_evaluation(test_db, tmp_path):
    """Integration test populating the synthetic dataset and running evaluation."""
    store_dir = tmp_path / "vec_full_eval_test"
    vstore = VectorStore(vector_store_dir=store_dir, dimension=384)
    dataset = get_evaluation_dataset()

    # Populate
    dataset.populate(db=test_db, vector_store=vstore, embedding_service=embedding_service)

    # Verify documents and chunks exist in test_db
    total_docs = test_db.query(Document).filter(Document.id.like("doc-eval-%")).count()
    assert total_docs == len(dataset.documents)

    base_retriever = BaselineRetriever(store=vstore, embedder=embedding_service)
    enhanced_retriever = RetrievalService(store=vstore, embedder=embedding_service, rerank_service=reranker)

    evaluator = RAGEvaluator(k_values=[1, 3, 5])
    base_res = evaluator.evaluate(base_retriever, "Baseline", test_db, dataset)
    enh_res = evaluator.evaluate(enhanced_retriever, "Phase 8.1", test_db, dataset)

    assert base_res.total_cases == len(dataset.cases)
    assert enh_res.total_cases == len(dataset.cases)

    comp = evaluator.compare(base_res, enh_res)
    assert comp is not None
    assert 1 in comp.delta_metrics_by_k
    assert 3 in comp.delta_metrics_by_k
    assert 5 in comp.delta_metrics_by_k

def test_three_way_comparison_evaluation():
    """Verify three-way comparison logic and report output."""
    cases = [
        EvaluationCase(
            case_id="c-1",
            query="test query",
            relevant_document_id="doc-1",
            relevant_chunk_ids=["chk-target"],
            expected_answer_facts=["target fact"],
            category="phrase_match"
        )
    ]
    test_ds = EvaluationDataset(cases=cases)

    # Baseline ranks target at rank 3
    b_stub = StubRetriever({"test query": ["chk-dist-1", "chk-dist-2", "chk-target"]})
    # Phase 8.1 ranks target at rank 2
    p81_stub = StubRetriever({"test query": ["chk-dist-1", "chk-target", "chk-dist-2"]})
    # Phase 8.3 ranks target at rank 1 due to phrase match
    p83_stub = StubRetriever({"test query": ["chk-target", "chk-dist-1", "chk-dist-2"]})

    evaluator = RAGEvaluator(k_values=[1, 3, 5])
    b_res = evaluator.evaluate(b_stub, "Baseline", None, test_ds)
    p81_res = evaluator.evaluate(p81_stub, "Phase 8.1", None, test_ds)
    p83_res = evaluator.evaluate(p83_stub, "Phase 8.3", None, test_ds)

    comp3 = evaluator.compare_three_way(b_res, p81_res, p83_res)
    assert comp3.phase83.mrr == 1.0
    assert comp3.phase81.mrr == 0.5
    assert round(comp3.baseline.mrr, 4) == round(1.0 / 3.0, 4)

    assert comp3.delta_mrr_83_vs_81 == 0.5
    assert comp3.delta_83_vs_81[1]["hit_rate"] == 1.0

    report = format_evaluation_report(comp3)
    assert "BASELINE — Semantic Retrieval" in report
    assert "PHASE 8.1 — Semantic + Lexical Retrieval" in report
    assert "PHASE 8.3 — Advanced Multi-Signal Retrieval" in report
    assert "DELTA (Phase 8.3 - Phase 8.1)" in report
    assert "phrase_match" in report
