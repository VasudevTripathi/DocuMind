from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.document import DocumentResponse

class EntityResponse(BaseModel):
    id: str
    name: str
    type: str

    model_config = ConfigDict(from_attributes=True)

class FindingResponse(BaseModel):
    id: str
    text: str
    priority: str

    model_config = ConfigDict(from_attributes=True)

class AnalysisDetailResponse(BaseModel):
    document: DocumentResponse
    summary: str
    category: str
    classificationConfidence: float
    wordCount: int
    keyFindings: List[FindingResponse]
    entities: List[EntityResponse]
    createdAt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
