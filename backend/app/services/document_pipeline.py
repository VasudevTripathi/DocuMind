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
from app.services.chunk_service import replace_document_chunks
from app.services.vector_store import vector_store
from app.services.llm_service import llm_service
from app.ml.predictor import predict_category

logger = logging.getLogger("documind.pipeline")

def process_document(document_id: str, db: Optional[Session] = None) -> bool:
    """Execute extraction, chunking, local classification, indexing and semantic analysis."""
    close_session_at_end = False
    if db is None:
        db = SessionLocal()
        close_session_at_end = True

    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error("[Pipeline] Document with ID '%s' not found.", document_id)
            return False

        doc.status = "processing"
        db.commit()

        file_path = DocumentService.get_physical_file_path(doc)
        parsed_data = parse_document(file_path, doc.file_type)
        cleaned_text = clean_text(parsed_data.get("text", ""))
        if not cleaned_text:
            raise ValueError("Extracted document text is empty after cleaning.")

        words = count_words(cleaned_text)
        chunks = chunk_document(doc.id, parsed_data)
        if not chunks:
            raise ValueError("No usable text chunks were generated.")

        # SQLite is the authoritative chunk store; reprocessing replaces old chunks.
        replace_document_chunks(db, doc.id, chunks)
        db.commit()

        # Rebuild the local FAISS index from all persisted chunks.
        vector_store.rebuild(db)
        logger.info("[Pipeline] Indexed %d chunks for document %s.", len(chunks), doc.id)

        ml_result = predict_category(cleaned_text)
        predicted_category = ml_result.get("category", "General")
        confidence = ml_result.get("confidence", 0.0)
        doc.category = predicted_category

        llm_result = llm_service.analyze_document(cleaned_text)

        if doc.analysis:
            db.delete(doc.analysis)
        db.query(DocumentFinding).filter(DocumentFinding.document_id == doc.id).delete()
        db.query(DocumentEntity).filter(DocumentEntity.document_id == doc.id).delete()
        db.flush()

        db.add(DocumentAnalysis(
            document_id=doc.id,
            summary=llm_result["summary"],
            category=predicted_category,
            classification_confidence=confidence,
            word_count=words,
        ))

        for finding in llm_result.get("key_findings", []):
            db.add(DocumentFinding(
                document_id=doc.id,
                finding_text=finding["text"],
                priority=finding.get("priority", "medium"),
            ))

        for entity in llm_result.get("entities", []):
            db.add(DocumentEntity(
                document_id=doc.id,
                name=entity["name"],
                entity_type=entity.get("type", "CONCEPT"),
            ))

        doc.status = "analyzed"
        db.commit()
        logger.info("[Pipeline] Document %s successfully analyzed.", doc.id)
        return True

    except Exception as exc:
        logger.error("[Pipeline] Processing failed for '%s': %s", document_id, exc, exc_info=True)
        db.rollback()
        try:
            failed_doc = db.query(Document).filter(Document.id == document_id).first()
            if failed_doc:
                failed_doc.status = "failed"
                db.commit()
        except Exception as inner_exc:
            logger.error("[Pipeline] Failed to set failed status: %s", inner_exc)
        return False

    finally:
        if close_session_at_end:
            db.close()
