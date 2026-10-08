import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "DocuMind AI"
    DATABASE_URL: str = "sqlite:///./data/db/documind.db"
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    FRONTEND_URL: str = "http://localhost:5173"
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_RETRIES: int = 2
    GROQ_INITIAL_BACKOFF: float = 1.0

    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GEMINI_MODEL: str | None = None
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MAX_RETRIES: int = 2
    GEMINI_INITIAL_BACKOFF: float = 1.0
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_STORE_DIR: str = "./data/vector_store"

    # Chunking Configuration (Part 4)
    RAG_CHUNK_SIZE_WORDS: int = 600
    RAG_CHUNK_OVERLAP_WORDS: int = 80

    # Context Budget Configuration (Part 8)
    RAG_MAX_CONTEXT_WORDS: int = 2500

    @property
    def active_groq_model(self) -> str:
        return self.GROQ_MODEL or "llama-3.3-70b-versatile"

    @property
    def active_gemini_model(self) -> str:
        return self.GEMINI_MODEL or "gemini-2.5-flash"

    # Phase 8.1 & 8.3 Retrieval & Reranking Settings
    RAG_CANDIDATE_K: int = 8
    RAG_FINAL_K: int = 4
    RAG_CONTEXT_RADIUS: int = 1
    RAG_MIN_SIMILARITY: float = 0.05
    RAG_SEMANTIC_WEIGHT: float = 0.50
    RAG_LEXICAL_WEIGHT: float = 0.15
    RAG_PHRASE_WEIGHT: float = 0.15
    RAG_COVERAGE_WEIGHT: float = 0.10
    RAG_CONTEXT_WEIGHT: float = 0.10
    RAG_CONTEXT_DISCOUNT: float = 0.80

    model_config = SettingsConfigDict(
        env_file=os.path.join(BACKEND_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def resolved_upload_dir(self) -> Path:
        """Resolve upload directory to an absolute Path."""
        path = Path(self.UPLOAD_DIR)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def resolved_vector_store_dir(self) -> Path:
        """Resolve vector store directory to an absolute Path."""
        path = Path(self.VECTOR_STORE_DIR)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def resolved_database_url(self) -> str:
        """Resolve SQLite relative paths to absolute paths to prevent cwd issues."""
        if self.DATABASE_URL.startswith("sqlite:///") and not self.DATABASE_URL.startswith("sqlite:////"):
            rel_path = self.DATABASE_URL.replace("sqlite:///", "")
            abs_path = (BACKEND_DIR / rel_path).resolve()
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{abs_path}"
        return self.DATABASE_URL

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

settings = Settings()
