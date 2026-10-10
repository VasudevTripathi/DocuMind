import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlite3 import OperationalError as SqliteOperationalError
from sqlalchemy.exc import OperationalError as SAOperationalError

from app.core.database import Base, is_sqlite_locked_error, init_db
from app.models.document import Document
from app.models.conversation import Conversation, ConversationMessage
from app.services.conversation_service import ConversationService


@pytest.fixture
def temp_sqlite_file_db():
    """
    Creates an isolated, real file-based SQLite database with WAL mode,
    NullPool, and busy_timeout=30000 matching production configuration.
    """
    temp_dir = tempfile.mkdtemp(prefix="documind_concurrency_test_")
    db_path = Path(temp_dir) / "test_concurrency.db"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False, "timeout": 30.0},
        poolclass=NullPool
    )

    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Set WAL once
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.commit()

    import app.models  # ensure models registered
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield {
        "engine": engine,
        "Session": Session,
        "db_path": db_path,
        "db_url": db_url
    }

    engine.dispose()
    # Cleanup temp files (including -wal and -shm)
    for p in Path(temp_dir).glob("*"):
        try:
            p.unlink()
        except OSError:
            pass
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass


def test_successful_conversation_creation(temp_sqlite_file_db):
    """Requirement 1: Verify successful conversation creation scoped and global."""
    Session = temp_sqlite_file_db["Session"]
    service = ConversationService()

    with Session() as db:
        doc = Document(
            id="doc-test-1",
            name="Spec.pdf",
            original_filename="Spec.pdf",
            file_path="data/uploads/spec.pdf",
            file_type="PDF",
            size_bytes=2048,
            status="analyzed"
        )
        db.add(doc)
        db.commit()

        # Scoped conversation
        c1 = service.create_conversation(db, document_id="doc-test-1", title="Spec Q&A")
        assert c1.id.startswith("conv-")
        assert c1.document_id == "doc-test-1"
        assert c1.title == "Spec Q&A"

        # Global conversation
        c2 = service.create_conversation(db, document_id=None)
        assert c2.id.startswith("conv-")
        assert c2.document_id is None
        assert c2.title == "New Conversation"


def test_rollback_and_session_cleanup_following_failed_write(temp_sqlite_file_db):
    """Requirement 2: Verify rollback and session cleanup following a failed database write."""
    Session = temp_sqlite_file_db["Session"]
    service = ConversationService()

    with Session() as db:
        # Intentionally inject an OperationalError during commit
        call_count = 0
        original_commit = db.commit

        def failing_commit():
            nonlocal call_count
            call_count += 1
            raise SAOperationalError(
                "INSERT INTO conversations ...",
                {},
                SqliteOperationalError("database is locked")
            )

        db.commit = failing_commit

        with pytest.raises(SAOperationalError):
            service.create_conversation(db, title="Will Fail")

        # Restore commit
        db.commit = original_commit

        # The failed transaction must have been rolled back cleanly by service._persist_conversation_with_retry
        # The session should be able to execute subsequent write operations without error
        c_subsequent = service.create_conversation(db, title="Subsequent Success")
        assert c_subsequent.id.startswith("conv-")
        assert c_subsequent.title == "Subsequent Success"


def test_repeated_conversation_creation_requests(temp_sqlite_file_db):
    """Requirement 3: Verify repeated conversation creation requests execute reliably."""
    Session = temp_sqlite_file_db["Session"]
    service = ConversationService()

    created_ids = []
    with Session() as db:
        for i in range(20):
            conv = service.create_conversation(db, title=f"Conversation {i}")
            assert conv.id.startswith("conv-")
            created_ids.append(conv.id)

    # Ensure all 20 unique IDs were persisted
    assert len(set(created_ids)) == 20
    with Session() as db:
        all_convs = service.list_conversations(db)
        persisted_ids = {c.id for c in all_convs}
        for cid in created_ids:
            assert cid in persisted_ids


def test_concurrent_conversation_creation_independent_sessions(temp_sqlite_file_db):
    """Requirement 4: Verify concurrent conversation creation using independent SQLAlchemy sessions."""
    Session = temp_sqlite_file_db["Session"]
    service = ConversationService()
    num_threads = 10
    results = []
    errors = []

    def worker(worker_id):
        try:
            # Independent session per thread, exactly as in request-scoped FastAPI calls
            with Session() as db:
                conv = service.create_conversation(
                    db,
                    title=f"Concurrent Worker {worker_id}"
                )
                return conv.id
        except Exception as e:
            errors.append(e)
            raise

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for f in as_completed(futures):
            results.append(f.result())

    assert len(errors) == 0, f"Encountered errors during concurrent creation: {errors}"
    assert len(results) == num_threads
    assert len(set(results)) == num_threads

    with Session() as db:
        all_convs = service.list_conversations(db)
        assert len(all_convs) >= num_threads


def test_sqlite_busy_timeout_and_wal_initialization(temp_sqlite_file_db):
    """Requirement 5: Verify SQLite busy-timeout and WAL mode configuration."""
    engine = temp_sqlite_file_db["engine"]

    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode;")).scalar()
        busy_timeout = conn.execute(text("PRAGMA busy_timeout;")).scalar()
        synchronous = conn.execute(text("PRAGMA synchronous;")).scalar()

        assert journal_mode.lower() == "wal"
        assert int(busy_timeout) == 30000
        # synchronous 1 is NORMAL (optimal for WAL mode)
        assert int(synchronous) == 1


def test_bounded_retry_recovers_from_transient_sqlite_lock(temp_sqlite_file_db):
    """Requirement 4 & 5: Verify bounded retry with jitter recovers from transient lock and does not duplicate."""
    Session = temp_sqlite_file_db["Session"]
    service = ConversationService()

    with Session() as db:
        attempts = 0
        real_commit = db.commit

        def intermittent_commit():
            nonlocal attempts
            attempts += 1
            if attempts <= 2:
                # First two attempts fail with transient lock error
                raise SAOperationalError(
                    "INSERT INTO conversations ...",
                    {},
                    SqliteOperationalError("database is locked")
                )
            # 3rd attempt succeeds
            return real_commit()

        db.commit = intermittent_commit

        conv = service.create_conversation(db, title="Retry Recovered")
        assert attempts == 3
        assert conv.id.startswith("conv-")
        assert conv.title == "Retry Recovered"

        # Verify only 1 record exists with this title (no duplicate creations)
        matching = db.query(Conversation).filter(Conversation.title == "Retry Recovered").all()
        assert len(matching) == 1


def test_non_blocking_concurrent_read_while_writing(temp_sqlite_file_db):
    """Verify readers do not block writers and writers do not block readers under WAL mode."""
    Session = temp_sqlite_file_db["Session"]
    service = ConversationService()

    # Pre-populate a document
    with Session() as db:
        doc = Document(
            id="doc-wal-read",
            name="WalTest.pdf",
            original_filename="WalTest.pdf",
            file_path="data/uploads/waltest.pdf",
            file_type="PDF",
            size_bytes=1024,
            status="analyzed"
        )
        db.add(doc)
        db.commit()

    read_results = []
    write_results = []
    errors = []

    def writer_worker(idx):
        try:
            with Session() as db:
                c = service.create_conversation(db, document_id="doc-wal-read", title=f"Write {idx}")
                write_results.append(c.id)
        except Exception as e:
            errors.append(("write", e))

    def reader_worker(idx):
        try:
            with Session() as db:
                d = db.query(Document).filter(Document.id == "doc-wal-read").first()
                assert d is not None
                convs = service.list_conversations(db, document_id="doc-wal-read")
                read_results.append(len(convs))
        except Exception as e:
            errors.append(("read", e))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for i in range(5):
            futures.append(executor.submit(writer_worker, i))
            futures.append(executor.submit(reader_worker, i))
        for f in as_completed(futures):
            f.result()

    assert len(errors) == 0, f"Errors during concurrent read/write: {errors}"
    assert len(write_results) == 5
    assert len(read_results) == 5


def test_is_sqlite_locked_error_detection():
    """Verify accurate detection of SQLite locked and busy operational errors."""
    sqlite_err = SqliteOperationalError("database is locked")
    sa_err = SAOperationalError("INSERT ...", {}, sqlite_err)
    assert is_sqlite_locked_error(sqlite_err) is True
    assert is_sqlite_locked_error(sa_err) is True

    busy_err = SqliteOperationalError("database is busy")
    assert is_sqlite_locked_error(busy_err) is True

    other_err = SqliteOperationalError("no such table: foobar")
    assert is_sqlite_locked_error(other_err) is False

    value_err = ValueError("Invalid parameter")
    assert is_sqlite_locked_error(value_err) is False
