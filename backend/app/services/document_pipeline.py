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
from app.services.llm_service import llm_service
from app.ml.predictor import predict_category

logger = logging.getLogger("documind.pipeline")

def process_document(document_id: str, db: Optional[Session] = None) -> bool:
    """
    Executes the end-to-end NLP document intelligence pipeline:
    1. Fetch document from DB
    2. Set status = 'processing'
    3. Parse document file
    4. Clean text
    5. Calculate word count
    6. Chunk text
    7. Run local ML classifier (TF-IDF + Logistic Regression)
    8. Send text to LLM service for summary, findings, and entities
    9. Validate LLM response
    10. Persist analysis, findings, and entities (idempotent; replaces previous analysis if reprocessed)
    11. Update document status = 'analyzed'
    12. Commit transaction

    If any major step fails, sets status = 'failed' to prevent documents from being stuck in processing.
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
        chunks = chunk_document(doc.id, parsed_data)
        logger.info(f"[Pipeline] Generated {len(chunks)} chunks for document {doc.id}.")

        # 7. Run local ML classifier
        ml_result = predict_category(cleaned_text)
        predicted_category = ml_result.get("category", "General")
        confidence = ml_result.get("confidence", 0.0)

        # Update document's category to the ML prediction
        doc.category = predicted_category

        # 8 & 9. Send to LLM for summary, key findings, and entity extraction
        llm_result = llm_service.analyze_document(cleaned_text)

        # 10. Clean up any existing analysis records for this document to prevent duplicates
        if doc.analysis:
            db.delete(doc.analysis)
        db.query(DocumentFinding).filter(DocumentFinding.document_id == doc.id).delete()
        db.query(DocumentEntity).filter(DocumentEntity.document_id == doc.id).delete()
        db.flush()

        # Save analysis
        analysis_record = DocumentAnalysis(
            document_id=doc.id,
            summary=llm_result["summary"],
            category=predicted_category,
            classification_confidence=confidence,
            word_count=words
        )
        db.add(analysis_record)

        # 11. Save findings
        for f in llm_result.get("key_findings", []):
            finding_record = DocumentFinding(
                document_id=doc.id,
                finding_text=f["text"],
                priority=f.get("priority", "medium")
            )
            db.add(finding_record)

        # 12. Save entities
        for e in llm_result.get("entities", []):
            entity_record = DocumentEntity(
                document_id=doc.id,
                name=e["name"],
                entity_type=e.get("type", "CONCEPT")
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
        # Mark as failed in DB
        try:
            failed_doc = db.query(Document).filter(Document.id == document_id).first()
            if failed_doc:
                failed_doc.status = "failed"
                db.commit()
                logger.info(f"[Pipeline] Document {document_id} transitioned to FAILED.")
        except Exception as inner_err:
            logger.error(f"[Pipeline] Failed to set status to 'failed': {inner_err}")
        return False

    finally:
        if close_session_at_end:
            db.close()
