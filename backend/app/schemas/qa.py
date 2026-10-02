from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class QuestionRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language question to ask against the document library")
    document_id: Optional[str] = Field(None, description="Optional document ID to scope retrieval")
    top_k: int = Field(5, ge=1, le=50, description="Number of relevant chunks to retrieve for context assembly")

class SourceChunk(BaseModel):
    document_id: str
    document_name: Optional[str] = None
    chunk_id: str
    chunk_index: int
    page_number: Optional[int] = None
    score: float
    text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AnswerResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceChunk]
    document_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
