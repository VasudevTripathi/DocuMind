import logging
import sqlite3
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError as SAOperationalError
from app.core.config import settings

logger = logging.getLogger("documind.database")

is_sqlite = settings.resolved_database_url.startswith("sqlite")

connect_args = {}
engine_kwargs = {}

if is_sqlite:
    connect_args = {
        "check_same_thread": False,
        "timeout": 30.0,  # SQLite connection-level busy timeout (30 seconds)
    }
    # For file-based SQLite, NullPool avoids lingering idle connection locks across threads.
    # In-memory SQLite (e.g. in tests) keeps default/StaticPool behavior.
    if ":memory:" not in settings.resolved_database_url:
        from sqlalchemy.pool import NullPool
        engine_kwargs["poolclass"] = NullPool

engine = create_engine(
    settings.resolved_database_url,
    connect_args=connect_args,
    **engine_kwargs
)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def is_sqlite_locked_error(exc: Exception) -> bool:
    """Checks whether an exception represents a transient SQLite database lock or busy error."""
    orig = getattr(exc, "orig", None)
    if orig and isinstance(orig, sqlite3.OperationalError):
        msg = str(orig).lower()
        return "database is locked" in msg or "database is busy" in msg
    if isinstance(exc, (sqlite3.OperationalError, SAOperationalError)):
        msg = str(exc).lower()
        return "database is locked" in msg or "database is busy" in msg
    return False

def get_db():
    """Dependency that provides a SQLAlchemy database session with reliable rollback and cleanup."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database tables, safe WAL journal mode, and lightweight schema migrations."""
    # Import models here so that Base knows about them before create_all
    import app.models  # noqa: F401

    # Safely enable WAL mode once during initialization for file-based SQLite
    if is_sqlite and ":memory:" not in settings.resolved_database_url:
        try:
            with engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL;"))
                conn.execute(text("PRAGMA busy_timeout=30000;"))
                conn.commit()
                logger.info("[Database] SQLite WAL mode successfully initialized.")
        except Exception as e:
            logger.warning(f"[Database] SQLite WAL mode initialization skipped: {e}")

    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            cursor = conn.execute(text("PRAGMA table_info(document_analyses);"))
            existing_cols = {row[1] for row in cursor.fetchall()}
            if "provider" not in existing_cols:
                conn.execute(text("ALTER TABLE document_analyses ADD COLUMN provider VARCHAR(50) DEFAULT 'gemini';"))
            if "quota_exceeded" not in existing_cols:
                conn.execute(text("ALTER TABLE document_analyses ADD COLUMN quota_exceeded BOOLEAN DEFAULT 0;"))

            msg_cursor = conn.execute(text("PRAGMA table_info(conversation_messages);"))
            existing_msg_cols = {row[1] for row in msg_cursor.fetchall()}
            if "provider" not in existing_msg_cols:
                conn.execute(text("ALTER TABLE conversation_messages ADD COLUMN provider VARCHAR(50);"))
            if "model" not in existing_msg_cols:
                conn.execute(text("ALTER TABLE conversation_messages ADD COLUMN model VARCHAR(100);"))

            conn.commit()
    except Exception as e:
        logger.debug(f"[Database] Lightweight migration check completed: {e}")

