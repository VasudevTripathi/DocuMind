import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.comparison import CompareRequest, ComparisonResponse
from app.services.retrieval_service import DocumentNotFoundError
from app.services.comparison_service import comparison_service

logger = logging.getLogger("documind.api.compare")

router = APIRouter(tags=["Comparison"])


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare two documents",
    description=(
        "Executes evidence-grounded document comparison between Document A and Document B. "
        "Deterministically identifies common elements, additions, removals, modifications, and conflicting values, "
        "with granular source chunk attribution and optional Gemini synthesis."
    )
)
def compare_documents(
    payload: CompareRequest,
    db: Session = Depends(get_db)
):
    """
    Evidence-grounded document comparison:
    1. Validates document IDs and distinctness.
    2. Retrieves chunks for both documents.
    3. Segments chunks into factual statements and aligns them semantically.
    4. Deterministically detects differences and conflicts.
    5. Synthesizes an executive summary via Gemini (or heuristic fallback).
    6. Returns structured differences with source attribution.
    """
    try:
        result = comparison_service.compare_documents(
            db=db,
            document_a_id=payload.document_a_id,
            document_b_id=payload.document_b_id,
            focus=payload.focus
        )
        return result

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except DocumentNotFoundError as de:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(de)
        )
    except Exception as e:
        logger.error(f"[CompareAPI] Document comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document comparison failed: {str(e)}"
        )
