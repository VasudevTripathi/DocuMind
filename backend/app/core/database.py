from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.resolved_database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.resolved_database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency that provides a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    import app.models.document  # noqa: F401
    import app.models.analysis  # noqa: F401
    import app.models.entity  # noqa: F401
    import app.models.finding  # noqa: F401
    import app.models.chunk  # noqa: F401
    Base.metadata.create_all(bind=engine)
