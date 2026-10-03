import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.conversation import Conversation, ConversationMessage
from app.services.retrieval_service import retrieval_service, RetrievalService, DocumentNotFoundError
from app.services.rag_service import format_grounded_context, NO_CONTEXT_FALLBACK
from app.services.llm_service import llm_service, LLMService

logger = logging.getLogger("documind.conversation")

class ConversationNotFoundError(Exception):
    pass

class ConversationService:
    """
    Manages multi-turn conversations and conversational document-grounded Q&A:
    - Conversation lifecycle (create, list, get, delete)
    - Controlled multi-turn conversational RAG answering
    - Grounding strictly on retrieved document context
    - Automatic reference resolution for follow-up questions
    - Strict no-context fallback preventing hallucination
    """

    def __init__(
        self,
        retrieval: RetrievalService = retrieval_service,
        llm: LLMService = llm_service
    ):
        self.retrieval_service = retrieval
        self.llm_service = llm

    def create_conversation(
        self,
        db: Session,
        document_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """Creates a new conversation, optionally associated with a document."""
        if document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise DocumentNotFoundError(f"Document with ID '{document_id}' not found.")

        conv_title = (title or "").strip() or "New Conversation"
        conversation = Conversation(
            document_id=document_id,
            title=conv_title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    def list_conversations(
        self,
        db: Session,
        document_id: Optional[str] = None
    ) -> List[Conversation]:
        """Lists conversations, optionally filtered by document_id, sorted by updated_at descending."""
        query = db.query(Conversation)
        if document_id:
            query = query.filter(Conversation.document_id == document_id)
        return query.order_by(Conversation.updated_at.desc()).all()

    def get_conversation(
        self,
        db: Session,
        conversation_id: str
    ) -> Optional[Conversation]:
        """Retrieves a conversation by its ID."""
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def delete_conversation(
        self,
        db: Session,
        conversation_id: str
    ) -> bool:
        """Deletes a conversation and its cascaded messages."""
        conv = self.get_conversation(db, conversation_id)
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        return True

    def post_message(
        self,
        db: Session,
        conversation_id: str,
        content: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Processes a user question within a conversation:
        1. Validates conversation and document scope.
        2. Contextual retrieval resolving follow-up references.
        3. Applies relevance threshold (> 0.05).
        4. No-context safety guard (returns fallback without invoking LLM).
        5. Persists user message and assistant answer.
        6. Returns structured assistant response with source attributions.
        """
        cleaned_content = (content or "").strip()
        if not cleaned_content:
            raise ValueError("Message content cannot be empty.")

        conversation = self.get_conversation(db, conversation_id)
        if not conversation:
            raise ConversationNotFoundError(f"Conversation '{conversation_id}' not found.")

        # Check document validity if scoped
        if conversation.document_id:
            doc = db.query(Document).filter(Document.id == conversation.document_id).first()
            if not doc:
                raise DocumentNotFoundError(f"Scoped document '{conversation.document_id}' not found.")

        # Fetch recent messages for history and contextual search
        recent_messages = list(conversation.messages)

        # Contextual retrieval: if there is previous conversational context,
        # formulate a combined query to resolve follow-up references (e.g. "When does that trigger?")
        prev_user_msgs = [m for m in recent_messages if m.role == "user"]
        search_results = self.retrieval_service.search(
            db=db,
            query=cleaned_content,
            top_k=top_k,
            document_id=conversation.document_id
        )

        if prev_user_msgs:
            # Augment with previous question context to resolve pronouns/topics
            last_query = prev_user_msgs[-1].content
            augmented_query = f"{last_query} {cleaned_content}"
            augmented_results = self.retrieval_service.search(
                db=db,
                query=augmented_query,
                top_k=top_k,
                document_id=conversation.document_id
            )
            # Merge and deduplicate by chunk_id keeping highest score
            merged_map = {}
            for res in search_results + augmented_results:
                cid = res["chunk_id"]
                score = res.get("score") or res.get("similarity_score", 0.0)
                if cid not in merged_map or score > (merged_map[cid].get("score") or merged_map[cid].get("similarity_score", 0.0)):
                    merged_map[cid] = res
            combined = list(merged_map.values())
            combined.sort(
                key=lambda x: (
                    -float(x.get("rerank_score", x.get("score", 0.0))),
                    -float(x.get("semantic_score", x.get("similarity_score", 0.0))),
                    x.get("chunk_index", 0)
                )
            )
            search_results = combined[:top_k]

        # Filter chunks with meaningful semantic relevance
        usable_chunks = [
            c for c in search_results
            if (c.get("score") or c.get("similarity_score") or 0.0) >= settings.RAG_MIN_SIMILARITY
        ]

        # 1. Persist user message
        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=cleaned_content
        )
        db.add(user_msg)

        # Auto-update conversation title from first question if default
        if conversation.title in ("New Conversation", "", None) and len(recent_messages) == 0:
            conversation.title = cleaned_content[:45] + ("..." if len(cleaned_content) > 45 else "")

        conversation.updated_at = datetime.now(timezone.utc)

        # 2. No-context safety: If no usable chunks retrieved, do NOT call LLM
        if not usable_chunks:
            logger.info(
                f"[ConversationService] No usable chunks retrieved for query: '{cleaned_content[:40]}'. "
                f"Returning fallback without calling LLM."
            )
            assistant_msg = ConversationMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=NO_CONTEXT_FALLBACK,
                sources_json=None
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)

            return {
                "id": assistant_msg.id,
                "conversation_id": conversation.id,
                "role": "assistant",
                "content": NO_CONTEXT_FALLBACK,
                "sources": [],
                "created_at": assistant_msg.created_at
            }

        # 3. Assemble grounded context and bounded history
        context_str = format_grounded_context(usable_chunks)
        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in recent_messages[-6:]
        ]

        # 4. Generate grounded answer via LLM
        logger.info(
            f"[ConversationService] Calling LLM with {len(usable_chunks)} chunks and {len(history_dicts)} history turns."
        )
        answer = self.llm_service.answer_conversational_question(
            question=cleaned_content,
            context=context_str,
            history=history_dicts
        )

        # 5. Format sources (if answer is fallback, return empty sources)
        if answer.strip() == NO_CONTEXT_FALLBACK:
            sources = []
        else:
            sources = [
                {
                    "document_id": c["document_id"],
                    "document_name": c.get("document_name"),
                    "chunk_id": c["chunk_id"],
                    "chunk_index": c["chunk_index"],
                    "page_number": c.get("page_number"),
                    "score": c.get("score") or c.get("similarity_score", 0.0),
                    "text": c.get("text"),
                    "semantic_score": c.get("semantic_score"),
                    "lexical_score": c.get("lexical_score"),
                    "phrase_score": c.get("phrase_score"),
                    "coverage_score": c.get("coverage_score"),
                    "context_score": c.get("context_score"),
                    "rerank_score": c.get("rerank_score")
                }
                for c in usable_chunks
            ]

        # 6. Persist assistant message
        assistant_msg = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer
        )
        assistant_msg.sources = sources
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return {
            "id": assistant_msg.id,
            "conversation_id": conversation.id,
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "created_at": assistant_msg.created_at
        }

conversation_service = ConversationService()
