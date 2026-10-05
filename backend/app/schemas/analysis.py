from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.document import DocumentResponse

class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    entity_type: Optional[str] = None

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
    classification_confidence: Optional[float] = None
    wordCount: int
    word_count: Optional[int] = None
    keyFindings: List[FindingResponse]
    findings: Optional[List[FindingResponse]] = None
    entities: List[EntityResponse]
    createdAt: Optional[str] = None
    provider: Optional[str] = "gemini"
    quotaExceeded: Optional[bool] = False
    quota_exceeded: Optional[bool] = False
    warning: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
