"""Asynchronous background job database model for CreditMera scalability.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AsyncJob(Base):
    __tablename__ = "async_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_type = Column(String(64), nullable=False, default="ASSET_REGISTRATION")
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    progress = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=True)
    asset_id = Column(BigInteger, nullable=True, index=True)
    result_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship to User
    user = relationship("User", backref="jobs")
