from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.health import router as health_router
from app.api.documents import router as documents_router
from app.api.analysis import router as analysis_router
from app.api.search import router as search_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.resolved_upload_dir
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for DocuMind AI Document Management",
    version="1.0.0",
    lifespan=lifespan
)

origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
unique_origins = list(dict.fromkeys([o.rstrip("/") for o in origins if o]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=unique_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(search_router)

@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "docs_url": "/docs",
        "health_check": "/api/health"
    }
