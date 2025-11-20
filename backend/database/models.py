"""SQLAlchemy models for signal database."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Signal(Base):
    """Signal detection record."""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    frequency = Column(Float, nullable=False, index=True)
    power = Column(Float)
    bandwidth = Column(Float)
    snr = Column(Float)
    timestamp = Column(String, nullable=False, index=True)
    category = Column(String, index=True)
    modulation = Column(String)
    confidence = Column(Float)
    description = Column(Text)
    technical_details = Column(JSON)
    sample_rate = Column(Float)
    gain = Column(String)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "frequency": self.frequency,
            "power": self.power,
            "bandwidth": self.bandwidth,
            "snr": self.snr,
            "timestamp": self.timestamp,
            "category": self.category,
            "modulation": self.modulation,
            "confidence": self.confidence,
            "description": self.description,
            "technical_details": self.technical_details,
            "sample_rate": self.sample_rate,
            "gain": self.gain,
        }


class Classification(Base):
    """Signal classification record."""

    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, index=True)
    frequency = Column(Float, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    confidence = Column(Float)
    modulation = Column(String)
    timestamp = Column(String, nullable=False, index=True)
    features = Column(JSON)
    method = Column(String)  # 'rule_based' or 'ml'

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "frequency": self.frequency,
            "category": self.category,
            "confidence": self.confidence,
            "modulation": self.modulation,
            "timestamp": self.timestamp,
            "features": self.features,
            "method": self.method,
        }


class Recording(Base):
    """Recording metadata record."""

    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False, unique=True, index=True)
    frequency = Column(Float, nullable=False)
    sample_rate = Column(Float, nullable=False)
    gain = Column(String)
    mode = Column(String)
    start_time = Column(String, nullable=False, index=True)
    duration = Column(Float)
    num_samples = Column(Integer)
    file_size = Column(Integer)
    description = Column(Text)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "frequency": self.frequency,
            "sample_rate": self.sample_rate,
            "gain": self.gain,
            "mode": self.mode,
            "start_time": self.start_time,
            "duration": self.duration,
            "num_samples": self.num_samples,
            "file_size": self.file_size,
            "description": self.description,
        }


def get_db_session(db_path: str = "data/ai_radio.db"):
    """
    Get database session.

    Args:
        db_path: Path to SQLite database

    Returns:
        SQLAlchemy session
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

