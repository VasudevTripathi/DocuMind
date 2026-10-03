import sys
import shutil
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.services.embedding_service import embedding_service
from app.services.reranker import RetrievalReranker
from app.services.retrieval_service import RetrievalService
from app.services.rag_service import RAGService
from app.services.vector_store import VectorStore
from app.evaluation.dataset import get_evaluation_dataset
from app.evaluation.evaluator import BaselineRetriever, RAGEvaluator
from app.evaluation.report import format_evaluation_report

def run_evaluation() -> int:
    """
    Local CLI execution entry point for DocuMind RAG Evaluation (Phase 8.3).
    1. Initializes an isolated in-memory SQLite database and temporary VectorStore
    2. Seeds the synthetic multi-document evaluation dataset (24 cases across 5 docs)
    3. Evaluates 3 retrieval architectures:
       - BASELINE: Semantic-only retrieval (FAISS similarity)
       - PHASE 8.1: Semantic + unigram lexical reranking + context expansion
       - PHASE 8.3: Enhanced multi-signal reranking (semantic + lexical + exact phrase + query coverage + context)
    4. Computes comparative metrics and deltas:
       - Phase 8.1 vs Baseline
       - Phase 8.3 vs Baseline
       - Phase 8.3 vs Phase 8.1
    5. Prints formatted human-readable report
    6. Ensures clean teardown with zero persistent side-effects
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="documind_eval_vector_"))
    try:
        # Isolated in-memory SQLite database
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # Isolated VectorStore
        eval_vector_store = VectorStore(vector_store_dir=temp_dir, dimension=384)

        # Populate dataset
        dataset = get_evaluation_dataset()
        dataset.populate(
            db=db,
            vector_store=eval_vector_store,
            embedding_service=embedding_service
        )

        # 1. Baseline retriever (Semantic search only, no reranking, no expansion)
        baseline_retriever = BaselineRetriever(
            store=eval_vector_store,
            embedder=embedding_service
        )

        # 2. Phase 8.1 retriever (Context expansion + unigram lexical reranking)
        phase81_reranker = RetrievalReranker(semantic_weight=0.75, lexical_weight=0.25)
        phase81_retriever = RetrievalService(
            store=eval_vector_store,
            embedder=embedding_service,
            rerank_service=phase81_reranker
        )

        # 3. Phase 8.3 retriever (Multi-signal reranking: semantic + lexical + phrase + coverage + context)
        phase83_reranker = RetrievalReranker()
        phase83_retriever = RetrievalService(
            store=eval_vector_store,
            embedder=embedding_service,
            rerank_service=phase83_reranker
        )

        evaluator = RAGEvaluator(k_values=[1, 3, 5])

        baseline_result = evaluator.evaluate(
            retriever=baseline_retriever,
            retriever_name="Baseline (Semantic Only)",
            db=db,
            dataset=dataset
        )

        phase81_result = evaluator.evaluate(
            retriever=phase81_retriever,
            retriever_name="Phase 8.1 (Enhanced Retrieval)",
            db=db,
            dataset=dataset
        )

        phase83_result = evaluator.evaluate(
            retriever=phase83_retriever,
            retriever_name="Phase 8.3 (Multi-Signal Retrieval)",
            db=db,
            dataset=dataset
        )

        comparison = evaluator.compare_three_way(
            baseline=baseline_result,
            phase81=phase81_result,
            phase83=phase83_result
        )

        # 4. Evaluate Answer Grounding (Phase 8.4)
        rag_svc = RAGService(retrieval=phase83_retriever)
        answer_eval = evaluator.evaluate_answers(
            rag_service=rag_svc,
            db=db,
            dataset=dataset
        )
        comparison.answer_evaluation = answer_eval

        report_text = format_evaluation_report(comparison)
        print(report_text)
        return 0

    except Exception as e:
        print(f"Error during RAG evaluation execution: {e}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(run_evaluation())
