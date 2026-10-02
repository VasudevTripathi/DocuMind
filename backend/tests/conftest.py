import os
import shutil
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.config import settings
from app.services.vector_store import VectorStore
from app.main import app

@pytest.fixture(scope="session")
def temp_dirs():
    temp_dir = tempfile.mkdtemp(prefix="documind_test_")
    uploads_dir = Path(temp_dir) / "uploads"
    vector_dir = Path(temp_dir) / "vector_store"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    vector_dir.mkdir(parents=True, exist_ok=True)
    yield {
        "root": Path(temp_dir),
        "uploads": uploads_dir,
        "vector_store": vector_dir
    }
    shutil.rmtree(temp_dir, ignore_errors=True)

from sqlalchemy.pool import StaticPool

@pytest.fixture(scope="function")
def test_db():
    # Use SQLite in-memory with StaticPool for test isolation
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    import app.models  # ensure all models registered
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def isolated_vector_store(tmp_path):
    store_dir = tmp_path / "vector_store"
    store_dir.mkdir(parents=True, exist_ok=True)
    store = VectorStore(vector_store_dir=store_dir, dimension=384)
    yield store
    store.clear()

@pytest.fixture(scope="function")
def client(test_db, monkeypatch, tmp_path):
    # Override get_db dependency
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Point uploads and vector store to tmp_path
    tmp_uploads = tmp_path / "uploads"
    tmp_vector = tmp_path / "vector_store"
    tmp_uploads.mkdir(parents=True, exist_ok=True)
    tmp_vector.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_uploads))
    monkeypatch.setattr(settings, "VECTOR_STORE_DIR", str(tmp_vector))

    from app.services import vector_store as vs_module
    test_vs = VectorStore(vector_store_dir=tmp_vector, dimension=384)
    monkeypatch.setattr(vs_module, "vector_store", test_vs)

    from app.services.retrieval_service import retrieval_service
    monkeypatch.setattr(retrieval_service, "vector_store", test_vs)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
