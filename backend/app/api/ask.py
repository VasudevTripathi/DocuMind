import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.qa import QuestionRequest, AnswerResponse, SourceChunk, GroundingMetadata
from app.services.retrieval_service import DocumentNotFoundError
from app.services.rag_service import rag_service

logger = logging.getLogger("documind.api.ask")

router = APIRouter(tags=["Q&A"])

@router.post("/ask", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
def ask_question(
    payload: QuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Document-grounded question answering:
    1. Retrieves top-k relevant chunks from FAISS vector store.
    2. Constructs structured context.
    3. Generates grounded answer using LLM.
    4. Returns answer and source attribution.
    """
    try:
        result = rag_service.answer_question(
            db=db,
            query=payload.query,
            document_id=payload.document_id,
            top_k=payload.top_k
        )

        return AnswerResponse(
            query=result["query"],
            answer=result["answer"],
            sources=[SourceChunk(**s) for s in result["sources"]],
            document_id=result.get("document_id"),
            grounding=GroundingMetadata(**result["grounding"]) if result.get("grounding") else None
        )

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
        logger.error(f"[AskAPI] Answering failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grounded answering failed: {str(e)}"
        )
