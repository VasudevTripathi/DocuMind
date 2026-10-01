import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_finding_id():
    return f"fnd-{uuid.uuid4().hex[:12]}"

class DocumentFinding(Base):
    __tablename__ = "document_findings"

    id = Column(String(36), primary_key=True, default=generate_finding_id, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_text = Column(Text, nullable=False)
    priority = Column(String(50), nullable=False, default="medium")

    document = relationship("Document", back_populates="findings")

    def __repr__(self):
        return f"<DocumentFinding id={self.id} priority='{self.priority}'>"
