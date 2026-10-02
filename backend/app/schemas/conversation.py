from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.qa import SourceChunk

class ConversationCreate(BaseModel):
    document_id: Optional[str] = Field(None, description="Optional document ID to scope conversation")
    title: Optional[str] = Field(None, max_length=255, description="Optional custom title for the conversation")

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="User question or follow-up question")
    top_k: int = Field(5, ge=1, le=50, description="Number of context chunks to retrieve")

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: Optional[List[SourceChunk]] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationResponse(BaseModel):
    id: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class ConversationDetailResponse(BaseModel):
    id: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
