import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.analysis import DocumentAnalysis
from app.models.finding import DocumentFinding
from app.models.entity import DocumentEntity
from app.schemas.document import DocumentResponse
from app.schemas.analysis import AnalysisDetailResponse, FindingResponse, EntityResponse
from app.services.document_service import DocumentService
from app.services.document_parser import parse_document
from app.services.text_processor import clean_text, count_words
from app.services.llm_service import llm_service
from app.ml.predictor import predict_category

logger = logging.getLogger("documind.analysis")

router = APIRouter(prefix="/documents", tags=["Analysis"])

@router.get("/{document_id}/analysis", response_model=AnalysisDetailResponse)
def get_document_analysis(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns structured analysis for a document:
    - Executive summary
    - Predicted category and confidence score
    - Word count
    - Key findings (with priorities)
    - Extracted entities (with types)
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    analysis = db.query(DocumentAnalysis).filter(DocumentAnalysis.document_id == document_id).first()
    
    # If the document is marked analyzed but the analysis record is missing, generate it dynamically
    if not analysis and doc.status == "analyzed":
        try:
            chunks = doc.chunks
            combined_text = " ".join([c.text for c in chunks if c.text]) if chunks else ""
            if not combined_text:
                file_path = DocumentService.get_physical_file_path(doc)
                parsed_data = parse_document(file_path, doc.file_type)
                combined_text = clean_text(parsed_data.get("text", ""))

            if combined_text:
                words = count_words(combined_text)
                ml_result = predict_category(combined_text)
                cat = ml_result.get("category", doc.category or "General")
                conf = ml_result.get("confidence", 0.0)
                llm_res = llm_service.analyze_document(combined_text)

                summary_text = llm_res.get("summary") if isinstance(llm_res, dict) else ""
                if not summary_text or not summary_text.strip():
                    summary_text = "Executive summary unavailable."

                analysis = DocumentAnalysis(
                    document_id=doc.id,
                    summary=summary_text,
                    category=cat,
                    classification_confidence=conf,
                    word_count=words
                )
                db.add(analysis)

                raw_findings = llm_res.get("key_findings", []) if isinstance(llm_res, dict) else []
                for f in raw_findings:
                    if isinstance(f, dict):
                        f_text = f.get("text") or f.get("finding") or str(f)
                        f_pri = f.get("priority", "medium")
                    else:
                        f_text = str(f).strip()
                        f_pri = "medium"
                    if f_text:
                        db.add(DocumentFinding(document_id=doc.id, finding_text=f_text, priority=f_pri))

                raw_entities = llm_res.get("entities", []) if isinstance(llm_res, dict) else []
                for e in raw_entities:
                    if isinstance(e, dict):
                        e_name = e.get("name") or e.get("entity") or ""
                        e_type = e.get("type") or e.get("entity_type") or "CONCEPT"
                    else:
                        e_name = str(e).strip()
                        e_type = "CONCEPT"
                    if e_name:
                        db.add(DocumentEntity(document_id=doc.id, name=e_name, entity_type=e_type))

                db.commit()
                db.refresh(analysis)
                db.refresh(doc)
        except Exception as ex:
            logger.error(f"[AnalysisAPI] On-the-fly analysis generation failed for document '{document_id}': {ex}", exc_info=True)
            db.rollback()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis for document '{document_id}' does not exist yet. Document status is currently '{doc.status}'."
        )

    findings = [
        FindingResponse(
            id=f.id,
            text=f.finding_text,
            priority=f.priority
        ) for f in doc.findings
    ]

    entities = [
        EntityResponse(
            id=e.id,
            name=e.name,
            type=e.entity_type,
            entity_type=e.entity_type
        ) for e in doc.entities
    ]

    is_quota = bool(
        getattr(analysis, "quota_exceeded", False)
        or getattr(analysis, "provider", "") == "quota_exhausted"
        or "429" in analysis.summary
        or "quota limit" in analysis.summary.lower()
        or "quota exceeded" in analysis.summary.lower()
    )
    warning_msg = (
        "Google Gemini API daily quota limit was reached (429 RESOURCE_EXHAUSTED). "
        "Showing local offline extractive analysis until quota resets."
        if is_quota else None
    )

    return AnalysisDetailResponse(
        document=DocumentResponse.from_model(doc),
        summary=analysis.summary,
        category=analysis.category,
        classificationConfidence=analysis.classification_confidence,
        classification_confidence=analysis.classification_confidence,
        wordCount=analysis.word_count,
        word_count=analysis.word_count,
        keyFindings=findings,
        findings=findings,
        entities=entities,
        createdAt=analysis.created_at.isoformat() if analysis.created_at else None,
        provider=getattr(analysis, "provider", "gemini") or ("quota_exhausted" if is_quota else "gemini"),
        quotaExceeded=is_quota,
        quota_exceeded=is_quota,
        warning=warning_msg
    )
