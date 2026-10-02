import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.retrieval_service import retrieval_service, RetrievalService, DocumentNotFoundError
from app.services.llm_service import llm_service, LLMService

logger = logging.getLogger("documind.rag")

NO_CONTEXT_FALLBACK = "The answer could not be found in the provided documents."

def format_grounded_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks into clear, structured context sections with source identifiers.
    """
    sections = []
    for i, c in enumerate(chunks, start=1):
        doc_name = c.get("document_name") or c.get("document_id") or "Unknown Document"
        chunk_idx = c.get("chunk_index", 0)
        chunk_id = c.get("chunk_id", "")
        score = c.get("score") or c.get("similarity_score", 0.0)
        text = (c.get("text") or "").strip()

        sections.append(
            f"[Source {i}]\n"
            f"Document: {doc_name}\n"
            f"Chunk ID: {chunk_id}\n"
            f"Chunk Index: {chunk_idx}\n"
            f"Relevance Score: {score:.4f}\n"
            f"Content:\n{text}"
        )
    return "\n\n".join(sections)

class RAGService:
    """
    Orchestrates the document-grounded question answering workflow:
    1. Validates query and document scoping.
    2. Calls RetrievalService to fetch top-k relevant chunks.
    3. Handles no-context scenarios safely without calling the LLM.
    4. Assembles grounded context with source citations.
    5. Invokes LLM service with dedicated grounding prompt.
    6. Returns structured answer and source attribution.
    """

    def __init__(
        self,
        retrieval: RetrievalService = retrieval_service,
        llm: LLMService = llm_service
    ):
        self.retrieval_service = retrieval
        self.llm_service = llm

    def answer_question(
        self,
        db: Session,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Answers a user question grounded strictly in retrieved document context.
        Raises ValueError if query is empty.
        Raises DocumentNotFoundError if document_id is provided but not found in the DB.
        """
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            raise ValueError("Query string cannot be empty.")

        # If document_id is supplied, verify it exists in DB
        if document_id:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise DocumentNotFoundError(f"Document with ID '{document_id}' was not found.")

        # 1. Retrieve top-k chunks
        chunks = self.retrieval_service.search(
            db=db,
            query=cleaned_query,
            top_k=top_k,
            document_id=document_id
        )

        # Filter chunks that have minimal positive semantic similarity
        usable_chunks = [
            c for c in chunks
            if (c.get("score") or c.get("similarity_score") or 0.0) > 0.05
        ]

        # 2. No-context guard: If no usable chunks retrieved, do NOT call LLM
        if not usable_chunks:
            logger.info(f"[RAGService] No usable chunks retrieved for query: '{cleaned_query[:40]}'. Returning fallback.")
            return {
                "query": cleaned_query,
                "answer": NO_CONTEXT_FALLBACK,
                "sources": [],
                "document_id": document_id
            }

        # 3. Assemble grounded context
        context_str = format_grounded_context(usable_chunks)

        # 4. Generate grounded answer via LLM
        logger.info(f"[RAGService] Invoking LLM answering with {len(usable_chunks)} context sources.")
        answer = self.llm_service.answer_question(
            question=cleaned_query,
            context=context_str
        )

        # 5. Format sources
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
                    "text": c.get("text")
                }
                for c in usable_chunks
            ]

        return {
            "query": cleaned_query,
            "answer": answer,
            "sources": sources,
            "document_id": document_id
        }

rag_service = RAGService()
