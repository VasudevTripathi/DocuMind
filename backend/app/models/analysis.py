import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_analysis_id():
    return f"an-{uuid.uuid4().hex[:12]}"

class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"

    id = Column(String(36), primary_key=True, default=generate_analysis_id, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    summary = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    classification_confidence = Column(Float, nullable=False, default=0.0)
    word_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="analysis")

    def __repr__(self):
        return f"<DocumentAnalysis id={self.id} doc_id={self.document_id} category='{self.category}'>"
