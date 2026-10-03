import sys
import shutil
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.services.embedding_service import embedding_service
from app.services.reranker import reranker
from app.services.retrieval_service import RetrievalService
from app.services.vector_store import VectorStore
from app.evaluation.dataset import get_evaluation_dataset
from app.evaluation.evaluator import BaselineRetriever, RAGEvaluator
from app.evaluation.report import format_evaluation_report

def run_evaluation() -> int:
    """
    Local CLI execution entry point for DocuMind RAG Evaluation.
    1. Initializes an isolated in-memory SQLite database and temporary VectorStore
    2. Seeds the synthetic multi-document evaluation dataset
    3. Evaluates Baseline Semantic Retrieval vs Phase 8.1 Enhanced Retrieval
    4. Computes comparative metrics and deltas
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

        # Baseline retriever (Semantic search only, no reranking, no expansion)
        baseline_retriever = BaselineRetriever(
            store=eval_vector_store,
            embedder=embedding_service
        )

        # Current Phase 8.1 retriever (Candidate retrieval + Context expansion + Lexical/Semantic reranking)
        enhanced_retriever = RetrievalService(
            store=eval_vector_store,
            embedder=embedding_service,
            rerank_service=reranker
        )

        evaluator = RAGEvaluator(k_values=[1, 3, 5])

        baseline_result = evaluator.evaluate(
            retriever=baseline_retriever,
            retriever_name="Baseline (Semantic Only)",
            db=db,
            dataset=dataset
        )

        enhanced_result = evaluator.evaluate(
            retriever=enhanced_retriever,
            retriever_name="Phase 8.1 (Enhanced Retrieval)",
            db=db,
            dataset=dataset
        )

        comparison = evaluator.compare(baseline_result, enhanced_result)
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
