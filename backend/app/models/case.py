"""Global Case Management database model for international image misuse tracking."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Text, JSON, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GlobalCase(Base):
    __tablename__ = "global_cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number = Column(String(64), unique=True, index=True, nullable=False)

    reporter_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    asset_id = Column(String(36), ForeignKey("registered_assets.id", ondelete="CASCADE"), index=True, nullable=False)

    title = Column(String(255), nullable=False)
    suspected_image_path = Column(String(512), nullable=True)
    suspected_url = Column(String(512), nullable=True)
    suspected_country = Column(String(64), nullable=True)

    match_score = Column(Float, nullable=True)
    watermark_status = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="New")  # New, Potential Match, Evidence Collected, Contacted, Under Review, Resolved, Closed

    evidence_notes = Column(Text, nullable=True)
    timeline_json = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    reporter = relationship("User", backref="reported_cases")
    asset = relationship("RegisteredAsset", backref="cases")
