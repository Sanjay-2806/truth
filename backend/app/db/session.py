"""Database engine and session management for TruthGuard AI."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Base

logger = get_logger("truthguard.db")

# Attempt primary PostgreSQL connection; fallback to SQLite for local development
engine = None
try:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        logger.info("Successfully connected to primary PostgreSQL database.")
except Exception as e:
    sqlite_path = settings.PROJECT_ROOT / "data/processed/truthguard.db"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_url = f"sqlite:///{sqlite_path}"
    logger.warning(
        f"PostgreSQL unreachable ({e}). Initializing fallback SQLite database at: {sqlite_url}"
    )
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Creates database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
