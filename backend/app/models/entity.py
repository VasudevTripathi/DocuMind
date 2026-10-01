import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_entity_id():
    return f"ent-{uuid.uuid4().hex[:12]}"

class DocumentEntity(Base):
    __tablename__ = "document_entities"

    id = Column(String(36), primary_key=True, default=generate_entity_id, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    entity_type = Column(String(100), nullable=False)

    document = relationship("Document", back_populates="entities")

    def __repr__(self):
        return f"<DocumentEntity id={self.id} name='{self.name}' type='{self.entity_type}'>"
