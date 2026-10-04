from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.qa import SourceChunk, GroundingMetadata

class DocumentInfo(BaseModel):
    id: str
    name: str
    category: Optional[str] = "General"
    chunk_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class CompareRequest(BaseModel):
    document_a_id: str = Field(..., min_length=1, description="ID of baseline document (Document A)")
    document_b_id: str = Field(..., min_length=1, description="ID of comparison document (Document B)")
    focus: Optional[str] = Field(None, description="Optional topic or query to focus the comparison on")

class AdditionItem(BaseModel):
    id: str
    topic: str
    content: str
    explanation: str
    sources_b: List[SourceChunk] = Field(default_factory=list)
    sources: List[SourceChunk] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class RemovalItem(BaseModel):
    id: str
    topic: str
    content: str
    explanation: str
    sources_a: List[SourceChunk] = Field(default_factory=list)
    sources: List[SourceChunk] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class ModificationItem(BaseModel):
    id: str
    topic: str
    document_a: str
    document_b: str
    explanation: str
    sources_a: List[SourceChunk] = Field(default_factory=list)
    sources_b: List[SourceChunk] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class ConflictItem(BaseModel):
    id: str
    topic: str
    document_a: str
    document_b: str
    explanation: str
    sources_a: List[SourceChunk] = Field(default_factory=list)
    sources_b: List[SourceChunk] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class CommonItem(BaseModel):
    id: str
    topic: str
    content: str
    explanation: str
    sources_a: List[SourceChunk] = Field(default_factory=list)
    sources_b: List[SourceChunk] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class ComparisonResponse(BaseModel):
    document_a: DocumentInfo
    document_b: DocumentInfo
    summary: str
    additions: List[AdditionItem] = Field(default_factory=list)
    removals: List[RemovalItem] = Field(default_factory=list)
    modifications: List[ModificationItem] = Field(default_factory=list)
    conflicts: List[ConflictItem] = Field(default_factory=list)
    common: List[CommonItem] = Field(default_factory=list)
    sources: List[SourceChunk] = Field(default_factory=list)
    grounding: Optional[GroundingMetadata] = None
    provider: Optional[str] = None
    model: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
