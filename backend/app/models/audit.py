"""Audit log database model for tracking registration and verification events.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(BigInteger, index=True, nullable=True)
    registered_asset_id = Column(
        String(36),
        ForeignKey("registered_assets.id", ondelete="SET NULL"),
        nullable=True
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )
    
    action = Column(String(64), index=True, nullable=False)
    status = Column(String(32), nullable=False)  # "SUCCESS", "FAILURE"
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    # Relationships
    asset = relationship("RegisteredAsset", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
