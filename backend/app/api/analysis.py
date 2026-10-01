from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.analysis import DocumentAnalysis
from app.schemas.document import DocumentResponse
from app.schemas.analysis import AnalysisDetailResponse, FindingResponse, EntityResponse

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
            type=e.entity_type
        ) for e in doc.entities
    ]

    return AnalysisDetailResponse(
        document=DocumentResponse.from_model(doc),
        summary=analysis.summary,
        category=analysis.category,
        classificationConfidence=analysis.classification_confidence,
        wordCount=analysis.word_count,
        keyFindings=findings,
        entities=entities,
        createdAt=analysis.created_at.isoformat() if analysis.created_at else None
    )
