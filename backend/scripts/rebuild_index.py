"""
Deterministic Vector Store & Chunk Index Rebuilder
DocuMind AI

Rebuilds SQLite chunks and FAISS vector index from scratch for all analyzed documents
using the updated chunking settings (RAG_CHUNK_SIZE_WORDS, RAG_CHUNK_OVERLAP_WORDS).
"""
import sys
import os
import logging
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.document import Document
from app.services.document_service import DocumentService
from app.services.document_parser import parse_document
from app.services.chunker import chunk_document
from app.services.chunk_service import ChunkService
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("documind.rebuild")

def rebuild_index():
    db = SessionLocal()
    try:
        documents = db.query(Document).filter(Document.status == "analyzed").all()
        if not documents:
            logger.info("No analyzed documents found in database to rebuild.")
            return

        logger.info(f"Starting index rebuild for {len(documents)} analyzed documents...")

        # Clear vector store for clean deterministic rebuild
        vector_store.clear()

        rebuilt_docs = 0
        total_chunks = 0

        for doc in documents:
            try:
                file_path = DocumentService.get_physical_file_path(doc)
                if not os.path.exists(file_path):
                    logger.warning(f"File for document '{doc.name}' ({doc.id}) not found at {file_path}. Skipping.")
                    continue

                parsed_data = parse_document(file_path, doc.file_type)
                raw_chunks = chunk_document(doc.id, parsed_data)

                # Atomically replace chunks in SQLite
                persisted_chunks = ChunkService.replace_chunks(db, doc.id, raw_chunks)

                # Embed and index into FAISS
                chunk_texts = [c.text for c in persisted_chunks]
                chunk_ids = [c.id for c in persisted_chunks]
                embeddings = embedding_service.embed_chunks(chunk_texts)
                vector_store.add_document_chunks(doc.id, chunk_ids, embeddings)

                rebuilt_docs += 1
                total_chunks += len(chunk_ids)
                logger.info(f"Rebuilt document '{doc.name}' ({doc.id}) with {len(chunk_ids)} chunks.")
            except Exception as e:
                logger.error(f"Failed to rebuild document '{doc.name}' ({doc.id}): {e}", exc_info=True)

        db.commit()
        logger.info(f"Rebuild completed successfully! Rebuilt {rebuilt_docs} documents, {total_chunks} total chunks.")
    finally:
        db.close()

if __name__ == "__main__":
    rebuild_index()
