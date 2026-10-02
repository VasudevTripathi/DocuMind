from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.services.vector_store import vector_store
from app.models.chunk import DocumentChunk
from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.analysis import router as analysis_router
from app.api.search import router as search_router
from app.api.ask import router as ask_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables and upload/vector folders are initialized on startup
    init_db()
    settings.resolved_upload_dir
    settings.resolved_vector_store_dir

    # Synchronize FAISS index from authoritative SQLite chunks if index is empty
    db = SessionLocal()
    try:
        if vector_store.count() == 0 and db.query(DocumentChunk).count() > 0:
            vector_store.rebuild_from_db(db)
    except Exception as e:
        import logging
        logging.getLogger("documind.startup").warning(f"Vector store startup sync skipped: {e}")
    finally:
        db.close()

    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for DocuMind AI Document Management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
# Remove any duplicates while preserving order
unique_origins = list(dict.fromkeys([o.rstrip("/") for o in origins if o]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=unique_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(health_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(ask_router, prefix="/api")

@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "docs_url": "/docs",
        "health_check": "/api/health"
    }
