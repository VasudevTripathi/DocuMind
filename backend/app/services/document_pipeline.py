import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
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

def process_document(document_id: str, db: Optional[Session] = None) -> bool:
    """
    Executes the end-to-end NLP document intelligence and RAG indexing pipeline:
    1. Fetch document from DB
    2. Set status = 'processing'
    3. Parse document file
    4. Clean & normalize text
    5. Calculate word count
    6. Generate deterministic chunks
    7. Persist chunks in SQLite
    8. Generate local embeddings
    9. Store vectors in FAISS
    10. Run local ML classifier (TF-IDF + Logistic Regression)
    11. Send text to LLM service for summary, findings, and entities
    12. Persist analysis, findings, and entities (idempotent replacement)
    13. Set status = 'analyzed'
    14. Commit transaction

    If any fatal step fails, sets status = 'failed' and cleans up any partial/stale
    chunks and vectors for this document.
    """
    close_session_at_end = False
    if db is None:
        db = SessionLocal()
        close_session_at_end = True

    try:
        # 1. Fetch document
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"[Pipeline] Document with ID '{document_id}' not found.")
            return False

        # 2. Set status = 'processing'
        doc.status = "processing"
        db.commit()
        db.refresh(doc)
        logger.info(f"[Pipeline] Document '{doc.name}' ({doc.id}) transitioned to PROCESSING.")

        # 3. Parse document
        file_path = DocumentService.get_physical_file_path(doc)
        parsed_data = parse_document(file_path, doc.file_type)

        # 4. Clean text
        raw_text = parsed_data.get("text", "")
        cleaned_text = clean_text(raw_text)

        if not cleaned_text:
            raise ValueError("Extracted document text is empty after cleaning.")

        # 5. Calculate word count
        words = count_words(cleaned_text)

        # 6. Chunk text
        raw_chunks = chunk_document(doc.id, parsed_data)
        logger.info(f"[Pipeline] Generated {len(raw_chunks)} chunks for document {doc.id}.")

        # 7. Persist chunks in SQLite (idempotently replaces previous chunks if reprocessed)
        persisted_chunks = ChunkService.replace_chunks(db, doc.id, raw_chunks)

        # 8. Generate local embeddings
        chunk_texts = [c.text for c in persisted_chunks]
        embeddings = embedding_service.embed_chunks(chunk_texts)

        # 9. Update FAISS vector store
        chunk_ids = [c.id for c in persisted_chunks]
        vector_store.add_document_chunks(doc.id, chunk_ids, embeddings)
        logger.info(f"[Pipeline] Indexed {len(chunk_ids)} chunk vectors in FAISS for document {doc.id}.")

        # 10. Run local ML classifier
        ml_result = predict_category(cleaned_text)
        predicted_category = ml_result.get("category", "General")
        confidence = ml_result.get("confidence", 0.0)

        # Update document's category to the ML prediction
        doc.category = predicted_category

        # 11. Send to LLM for summary, key findings, and entity extraction
        llm_result = llm_service.analyze_document(cleaned_text)

        # 12. Clean up any existing analysis records for this document to prevent duplicates
        if doc.analysis:
            db.delete(doc.analysis)
        db.query(DocumentFinding).filter(DocumentFinding.document_id == doc.id).delete()
        db.query(DocumentEntity).filter(DocumentEntity.document_id == doc.id).delete()
        db.flush()

        # Save analysis
        summary_text = llm_result.get("summary") if isinstance(llm_result, dict) else ""
        if not summary_text or not summary_text.strip():
            summary_text = "Executive summary unavailable."

        analysis_record = DocumentAnalysis(
            document_id=doc.id,
            summary=summary_text,
            category=predicted_category,
            classification_confidence=confidence,
            word_count=words,
            provider=llm_result.get("provider", "gemini"),
            quota_exceeded=llm_result.get("quota_exceeded", False)
        )
        db.add(analysis_record)

        # Save findings
        raw_findings = llm_result.get("key_findings", []) if isinstance(llm_result, dict) else []
        for f in raw_findings:
            if isinstance(f, dict):
                f_text = f.get("text") or f.get("finding") or str(f)
                f_priority = f.get("priority", "medium")
            else:
                f_text = str(f).strip()
                f_priority = "medium"
            if f_text:
                finding_record = DocumentFinding(
                    document_id=doc.id,
                    finding_text=f_text,
                    priority=f_priority
                )
                db.add(finding_record)

        # Save entities
        raw_entities = llm_result.get("entities", []) if isinstance(llm_result, dict) else []
        for e in raw_entities:
            if isinstance(e, dict):
                e_name = e.get("name") or e.get("entity") or ""
                e_type = e.get("type") or e.get("entity_type") or "CONCEPT"
            else:
                e_name = str(e).strip()
                e_type = "CONCEPT"
            if e_name:
                entity_record = DocumentEntity(
                    document_id=doc.id,
                    name=e_name,
                    entity_type=e_type
                )
                db.add(entity_record)

        # 13. Set status = 'analyzed'
        doc.status = "analyzed"
        db.commit()
        db.refresh(doc)
        logger.info(f"[Pipeline] Document {doc.id} successfully ANALYZED (Category: {predicted_category}, Confidence: {confidence}).")
        return True

    except Exception as e:
        logger.error(f"[Pipeline] Processing failed for document '{document_id}': {e}", exc_info=True)
        db.rollback()

        # Cleanup any partial vector store entries
        try:
            vector_store.remove_document(document_id)
        except Exception as ve_err:
            logger.error(f"[Pipeline] Failed to clean up vector store on error: {ve_err}")

        # Mark as failed in DB and cleanup partial chunks
        try:
            failed_doc = db.query(Document).filter(Document.id == document_id).first()
            if failed_doc:
                ChunkService.delete_chunks_by_document(db, document_id)
                failed_doc.status = "failed"
                db.commit()
                logger.info(f"[Pipeline] Document {document_id} transitioned to FAILED.")
        except Exception as inner_err:
            logger.error(f"[Pipeline] Failed to set status to 'failed': {inner_err}")
            db.rollback()
        return False

    finally:
        if close_session_at_end:
            db.close()
