import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services.retrieval_service import retrieval_service, DocumentNotFoundError

logger = logging.getLogger("documind.api.search")

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def search_documents(
    payload: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Semantic search across ingested document chunks using local FAISS vector retrieval.
    Optional scoping by document_id.
    """
    try:
        results = retrieval_service.search(
            db=db,
            query=payload.query,
            top_k=payload.top_k,
            document_id=payload.document_id
        )

        return SearchResponse(
            query=payload.query,
            total_results=len(results),
            results=[SearchResultItem(**r) for r in results]
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
        logger.error(f"[SearchAPI] Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic retrieval failed: {str(e)}"
        )
