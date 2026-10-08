import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    MessageCreate,
    MessageResponse
)
from app.schemas.qa import SourceChunk
from app.services.retrieval_service import DocumentNotFoundError
from app.services.conversation_service import conversation_service, ConversationNotFoundError

logger = logging.getLogger("documind.api.conversations")

router = APIRouter(tags=["Conversations"])

def _build_conv_response(conv) -> ConversationResponse:
    doc_name = conv.document.name if conv.document else None
    return ConversationResponse(
        id=conv.id,
        document_id=conv.document_id,
        document_name=doc_name,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages) if conv.messages else 0
    )

def _build_message_response(msg) -> MessageResponse:
    sources = [SourceChunk(**s) for s in msg.sources] if msg.sources is not None else []
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        sources=sources,
        created_at=msg.created_at,
        provider=getattr(msg, "provider", None),
        model=getattr(msg, "model", None)
    )

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db)
):
    """Creates a new conversation session, optionally scoped to a document."""
    try:
        conv = conversation_service.create_conversation(
            db=db,
            document_id=payload.document_id,
            title=payload.title
        )
        return _build_conv_response(conv)
    except DocumentNotFoundError as de:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(de))
    except Exception as e:
        logger.error(f"[ConversationsAPI] Creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get("/conversations", response_model=List[ConversationResponse], status_code=status.HTTP_200_OK)
def list_conversations(
    document_id: Optional[str] = Query(None, description="Filter conversations by document ID"),
    db: Session = Depends(get_db)
):
    """Lists conversations, sorted by most recently active."""
    conversations = conversation_service.list_conversations(db=db, document_id=document_id)
    return [_build_conv_response(c) for c in conversations]

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse, status_code=status.HTTP_200_OK)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves conversation metadata and chronologically ordered messages."""
    conv = conversation_service.get_conversation(db=db, conversation_id=conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found."
        )

    doc_name = conv.document.name if conv.document else None
    messages = [_build_message_response(m) for m in conv.messages]

    return ConversationDetailResponse(
        id=conv.id,
        document_id=conv.document_id,
        document_name=doc_name,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages
    )

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Deletes a conversation and its messages."""
    success = conversation_service.delete_conversation(db=db, conversation_id=conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found."
        )
    return {"status": "success", "message": f"Conversation '{conversation_id}' deleted successfully."}

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def send_message(
    conversation_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db)
):
    """
    Sends a user question within a conversation and returns a grounded assistant answer:
    1. Retains conversation history.
    2. Contextually retrieves document chunks.
    3. Prevents hallucination when no supporting context exists.
    4. Cites source chunks with relevance scores.
    """
    try:
        result = conversation_service.post_message(
            db=db,
            conversation_id=conversation_id,
            content=payload.content,
            top_k=payload.top_k
        )
        sources = [SourceChunk(**s) for s in result["sources"]] if result.get("sources") is not None else []
        return MessageResponse(
            id=result["id"],
            conversation_id=result["conversation_id"],
            role=result["role"],
            content=result["content"],
            sources=sources,
            created_at=result["created_at"],
            provider=result.get("provider"),
            model=result.get("model")
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except ConversationNotFoundError as ce:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ce))
    except DocumentNotFoundError as de:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(de))
    except Exception as e:
        logger.error(f"[ConversationsAPI] Message failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process conversational message: {str(e)}"
        )
