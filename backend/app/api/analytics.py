from typing import Dict, Any, List
from collections import Counter
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.models.entity import DocumentEntity
from app.services.vector_store import vector_store

router = APIRouter(tags=["analytics"])

@router.get("/analytics", status_code=status.HTTP_200_OK)
def get_library_analytics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Computes library-wide metrics, distribution analytics, and extracted concepts
    across all uploaded documents.
    """
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    total_docs = len(docs)

    status_counts = Counter((d.status or "unknown").lower() for d in docs)
    category_counts = Counter(d.category or "General" for d in docs)
    type_counts = Counter((d.file_type or "OTHER").upper() for d in docs)
    total_size_bytes = sum(d.size_bytes or 0 for d in docs)

    total_chunks = db.query(func.count(DocumentChunk.id)).scalar() or 0
    total_words = db.query(func.sum(DocumentChunk.word_count)).scalar() or 0

    # Top entities aggregated across documents
    entities = (
        db.query(DocumentEntity.name, DocumentEntity.entity_type, func.count(DocumentEntity.id).label("count"))
        .group_by(DocumentEntity.name, DocumentEntity.entity_type)
        .order_by(func.count(DocumentEntity.id).desc())
        .limit(25)
        .all()
    )

    top_entities = [
        {"name": name, "type": entity_type, "count": count}
        for name, entity_type, count in entities
    ]

    docs_summary = []
    for d in docs:
        c_count = len(d.chunks)
        w_count = sum(c.word_count for c in d.chunks)
        docs_summary.append({
            "id": d.id,
            "name": d.name,
            "category": d.category or "General",
            "file_type": (d.file_type or "TXT").upper(),
            "size_bytes": d.size_bytes or 0,
            "status": (d.status or "pending").lower(),
            "chunk_count": c_count,
            "word_count": w_count,
            "summary": d.analysis.summary if d.analysis else None,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
        })

    return {
        "total_documents": total_docs,
        "analyzed_count": status_counts.get("analyzed", 0),
        "processing_count": status_counts.get("processing", 0) + status_counts.get("pending", 0),
        "failed_count": status_counts.get("failed", 0),
        "total_chunks": total_chunks,
        "total_words": total_words,
        "total_size_bytes": total_size_bytes,
        "vector_count": vector_store.count(),
        "categories": dict(category_counts),
        "file_types": dict(type_counts),
        "statuses": dict(status_counts),
        "top_entities": top_entities,
        "documents": docs_summary
    }
