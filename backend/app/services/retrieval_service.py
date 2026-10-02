from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.vector_store import vector_store


def retrieve_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    document_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve the most semantically similar persisted chunks."""
    return vector_store.search(db, query=query, top_k=top_k, document_id=document_id)
