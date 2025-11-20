"""Database connection and session management."""

import logging
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "data/ai_radio.db"


def init_database(db_path: str = DEFAULT_DB_PATH):
    """
    Initialize database and create tables.

    Args:
        db_path: Path to SQLite database
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    logger.info(f"Database initialized at {db_path}")


@contextmanager
def get_db_session(db_path: str = DEFAULT_DB_PATH):
    """
    Get database session context manager.

    Args:
        db_path: Path to SQLite database

    Yields:
        SQLAlchemy session
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

