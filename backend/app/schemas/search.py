from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search query string")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to retrieve (between 1 and 50)")
    document_id: Optional[str] = Field(None, description="Optional document ID to scope retrieval")

class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    page_number: Optional[int] = None
    text: str
    similarity_score: float

    model_config = ConfigDict(from_attributes=True)

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]

    model_config = ConfigDict(from_attributes=True)
