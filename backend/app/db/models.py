"""SQLAlchemy database models for TruthGuard AI run persistence."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    JSON,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RunRecordModel(Base):
    """Stores full execution trail for a query answering run."""

    __tablename__ = "query_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    question = Column(Text, nullable=False)
    mode = Column(String(32), nullable=False, default="truthguard")

    # Output decisions
    answer = Column(Text, nullable=True)
    abstained = Column(Boolean, nullable=False, default=False)
    reason_code = Column(String(32), nullable=False, default="NONE")
    reason_explanation = Column(Text, nullable=False, default="")
    risk_score = Column(Float, nullable=False, default=0.0)

    # Detailed payloads
    draft_answer = Column(Text, nullable=True)
    claims_json = Column(JSON, nullable=True)
    passages_json = Column(JSON, nullable=True)
    timings_json = Column(JSON, nullable=True)
    token_usage_json = Column(JSON, nullable=True)
    parameters_json = Column(JSON, nullable=True)
