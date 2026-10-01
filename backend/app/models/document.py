import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_doc_id():
    return f"doc-{uuid.uuid4().hex[:12]}"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_doc_id, index=True)
    name = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False, index=True)
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    category = Column(String(100), nullable=False, default="General", index=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    analysis = relationship("DocumentAnalysis", back_populates="document", uselist=False, cascade="all, delete-orphan")
    entities = relationship("DocumentEntity", back_populates="document", cascade="all, delete-orphan")
    findings = relationship("DocumentFinding", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document id={self.id} name='{self.name}' status='{self.status}'>"
