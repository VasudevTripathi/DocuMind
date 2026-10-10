import os
import time
import random
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, is_sqlite_locked_error
from app.models.document import Document
from app.models.analysis import DocumentAnalysis
from app.models.finding import DocumentFinding
from app.models.entity import DocumentEntity
from app.services.document_service import DocumentService
from app.services.document_parser import parse_document
from app.services.text_processor import clean_text, count_words
from app.services.chunker import chunk_document
from app.services.chunk_service import ChunkService
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.ml.predictor import predict_category

logger = logging.getLogger("documind.pipeline")

@contextmanager
def _get_pipeline_session(passed_db: Optional[Session] = None):
    """
    Yields the provided session (for test isolation) or creates a scoped,
    isolated SessionLocal() that commits and closes cleanly per pipeline phase.
    """
    if passed_db is not None:
        yield passed_db
    else:
        session = SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

def _execute_phase_with_retry(fn, phase_name: str, max_retries: int = 3, initial_delay: float = 0.05):
    """
    Executes a database phase with bounded retry and jitter strictly for transient SQLite locks.
    Logs structured phase timing, transaction status, and lock outcomes.
    """
    delay = initial_delay
    for attempt in range(max_retries + 1):
        t0 = time.perf_counter()
        try:
            result = fn()
            dur_ms = (time.perf_counter() - t0) * 1000
            logger.info(
                f"[Pipeline:{phase_name}] pid={os.getpid()} duration_ms={dur_ms:.2f} "
                f"attempt={attempt + 1} outcome=success"
            )
            return result
        except Exception as e:
            dur_ms = (time.perf_counter() - t0) * 1000
            if is_sqlite_locked_error(e) and attempt < max_retries:
                logger.warning(
                    f"[Pipeline:{phase_name}] Transient SQLite lock after {dur_ms:.2f}ms on attempt {attempt + 1}/{max_retries + 1}. "
                    f"Retrying in {delay:.3f}s: {e}"
                )
                time.sleep(delay + random.uniform(0.01, 0.05))
                delay = min(delay * 2, 0.5)
                continue
            logger.error(f"[Pipeline:{phase_name}] Failed after {dur_ms:.2f}ms: {e}", exc_info=True)
            raise

def process_document(document_id: str, db: Optional[Session] = None) -> bool:
    """
    Executes the end-to-end NLP document intelligence and RAG indexing pipeline:
    - Phase 1 (DB): Set status = 'processing', fetch detached file metadata (< 3ms)
    - Phase 2 (CPU): Parse file, clean text, compute word count, chunk text (NO DB SESSION)
    - Phase 3 (DB): Persist chunks in SQLite, commit, and close session (< 5ms)
    - Phase 4 (CPU/Network): Local embeddings, FAISS indexing, ML predictor, and external LLM API calls (ZERO DB SESSION OPEN)
    - Phase 5 (DB): Persist analysis, findings, and entities, set status = 'analyzed' (< 5ms)

    Because database sessions are strictly scoped to short microsecond phases,
    no database connection or transaction is held open during embedding generation,
    vector store indexing, classification, or external LLM network calls.
    """
    total_start = time.perf_counter()
    logger.info(f"[Pipeline] Starting processing for document '{document_id}' (pid={os.getpid()}).")

    try:
        # Phase 1: Mark as 'processing' and fetch detached metadata
        def phase1():
            with _get_pipeline_session(db) as session:
                doc = session.query(Document).filter(Document.id == document_id).first()
                if not doc:
                    return None
                doc.status = "processing"
                session.commit()
                return {
                    "name": doc.name,
                    "file_type": doc.file_type,
                    "physical_path": DocumentService.get_physical_file_path(doc)
                }

        doc_info = _execute_phase_with_retry(phase1, "Stage1:MarkProcessing")
        if not doc_info:
            logger.error(f"[Pipeline] Document with ID '{document_id}' not found.")
            return False

        logger.info(f"[Pipeline] Document '{doc_info['name']}' ({document_id}) transitioned to PROCESSING.")

        # Phase 2: In-memory CPU text parsing and chunking (NO DB SESSION OPEN)
        p2_start = time.perf_counter()
        parsed_data = parse_document(doc_info["physical_path"], doc_info["file_type"])
        raw_text = parsed_data.get("text", "")
        cleaned_text = clean_text(raw_text)

        if not cleaned_text:
            raise ValueError("Extracted document text is empty after cleaning.")

        words = count_words(cleaned_text)
        raw_chunks = chunk_document(document_id, parsed_data)
        p2_ms = (time.perf_counter() - p2_start) * 1000
        logger.info(
            f"[Pipeline:Stage2:ParseAndChunk] Generated {len(raw_chunks)} chunks ({words} words) in {p2_ms:.2f}ms for document '{document_id}'."
        )

        # Phase 3: Persist chunks to SQLite and commit immediately
        def phase3():
            with _get_pipeline_session(db) as session:
                persisted_chunks = ChunkService.replace_chunks(session, document_id, raw_chunks)
                chunk_texts = [c.text for c in persisted_chunks]
                chunk_ids = [c.id for c in persisted_chunks]
                session.commit()
                return chunk_texts, chunk_ids

        chunk_texts, chunk_ids = _execute_phase_with_retry(phase3, "Stage3:PersistChunks")

        # Phase 4: Heavy computations (Local embeddings, FAISS indexing, ML predictor, and external LLM API calls)
        # ZERO DATABASE CONNECTION IS HELD DURING THIS ENTIRE PHASE!
        p4_start = time.perf_counter()
        embeddings = embedding_service.embed_chunks(chunk_texts)
        vector_store.add_document_chunks(document_id, chunk_ids, embeddings)
        logger.info(f"[Pipeline:Stage4:FAISS] Indexed {len(chunk_ids)} chunk vectors in FAISS for document '{document_id}'.")

        ml_result = predict_category(cleaned_text)
        predicted_category = ml_result.get("category", "General")
        confidence = ml_result.get("confidence", 0.0)

        llm_result = llm_service.analyze_document(cleaned_text)
        p4_ms = (time.perf_counter() - p4_start) * 1000
        logger.info(
            f"[Pipeline:Stage4:EmbeddingAndLLM] Completed in {p4_ms:.2f}ms (Category: '{predicted_category}', Conf: {confidence:.2f})."
        )

        # Phase 5: Persist analysis, findings, entities, and update status to 'analyzed'
        def phase5():
            with _get_pipeline_session(db) as session:
                doc = session.query(Document).filter(Document.id == document_id).first()
                if not doc:
                    logger.error(f"[Pipeline] Document '{document_id}' was removed before analysis could be saved.")
                    return False

                doc.category = predicted_category

                # Clean up any existing analysis records for this document to prevent duplicates
                if doc.analysis:
                    session.delete(doc.analysis)
                session.query(DocumentFinding).filter(DocumentFinding.document_id == document_id).delete()
                session.query(DocumentEntity).filter(DocumentEntity.document_id == document_id).delete()
                session.flush()

                summary_text = llm_result.get("summary") if isinstance(llm_result, dict) else ""
                if not summary_text or not summary_text.strip():
                    summary_text = "Executive summary unavailable."

                analysis_record = DocumentAnalysis(
                    document_id=document_id,
                    summary=summary_text,
                    category=predicted_category,
                    classification_confidence=confidence,
                    word_count=words,
                    provider=llm_result.get("provider", "gemini"),
                    quota_exceeded=llm_result.get("quota_exceeded", False)
                )
                session.add(analysis_record)

                raw_findings = llm_result.get("key_findings", []) if isinstance(llm_result, dict) else []
                for f in raw_findings:
                    if isinstance(f, dict):
                        f_text = f.get("text") or f.get("finding") or str(f)
                        f_priority = f.get("priority", "medium")
                    else:
                        f_text = str(f).strip()
                        f_priority = "medium"
                    if f_text:
                        session.add(DocumentFinding(document_id=document_id, finding_text=f_text, priority=f_priority))

                raw_entities = llm_result.get("entities", []) if isinstance(llm_result, dict) else []
                for e in raw_entities:
                    if isinstance(e, dict):
                        e_name = e.get("name") or e.get("entity") or ""
                        e_type = e.get("type") or e.get("entity_type") or "CONCEPT"
                    else:
                        e_name = str(e).strip()
                        e_type = "CONCEPT"
                    if e_name:
                        session.add(DocumentEntity(document_id=document_id, name=e_name, entity_type=e_type))

                doc.status = "analyzed"
                session.commit()
                return True

        success = _execute_phase_with_retry(phase5, "Stage5:PersistAnalysis")
        total_ms = (time.perf_counter() - total_start) * 1000
        logger.info(
            f"[Pipeline] Document '{document_id}' successfully ANALYZED in {total_ms:.2f}ms total (pid={os.getpid()})."
        )
        return bool(success)

    except Exception as e:
        logger.error(f"[Pipeline] Processing failed for document '{document_id}': {e}", exc_info=True)

        # Cleanup any partial vector store entries
        try:
            vector_store.remove_document(document_id)
        except Exception as ve_err:
            logger.warning(f"[Pipeline] Vector store cleanup error on failure: {ve_err}")

        # Mark document as failed in DB using a clean session
        try:
            def mark_failed():
                with _get_pipeline_session(db) as session:
                    failed_doc = session.query(Document).filter(Document.id == document_id).first()
                    if failed_doc:
                        ChunkService.delete_chunks_by_document(session, document_id)
                        failed_doc.status = "failed"
                        session.commit()

            _execute_phase_with_retry(mark_failed, "MarkFailed")
            logger.info(f"[Pipeline] Document '{document_id}' transitioned to FAILED.")
        except Exception as inner_err:
            logger.error(f"[Pipeline] Failed to set status to 'failed': {inner_err}")

        return False
