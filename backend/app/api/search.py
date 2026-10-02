from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.retrieval_service import retrieve_chunks

router = APIRouter(prefix="/api/search", tags=["Search"])


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: Optional[str] = None


@router.post("")
def semantic_search(payload: SemanticSearchRequest, db: Session = Depends(get_db)):
    results = retrieve_chunks(
        db,
        query=payload.query,
        top_k=payload.top_k,
        document_id=payload.document_id,
    )
    return {
        "query": payload.query,
        "count": len(results),
        "results": results,
    }
