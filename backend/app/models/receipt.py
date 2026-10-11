"""Registration receipt database model.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, BigInteger, Integer, Text, JSON,
    DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RegistrationReceipt(Base):
    __tablename__ = "registration_receipts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    receipt_number = Column(String(64), unique=True, index=True, nullable=False)
    
    registered_asset_id = Column(
        String(36),
        ForeignKey("registered_assets.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )
    asset_id = Column(BigInteger, index=True, nullable=False)
    
    issued_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    issuer = Column(String(128), nullable=False)
    
    original_file_sha256 = Column(String(64), nullable=False)
    watermarked_file_sha256 = Column(String(64), nullable=False)
    
    algorithm_version = Column(String(64), nullable=False)
    payload_version = Column(Integer, nullable=False)
    
    owner_declaration_summary = Column(Text, nullable=False)
    legal_disclaimer = Column(Text, nullable=False)
    
    # Authoritative canonical receipt structure
    receipt_payload_json = Column(JSON, nullable=False)
    
    # Server-side HMAC-SHA256 signature preventing tampering
    receipt_signature = Column(String(64), nullable=False)

    # Relationships
    asset = relationship("RegisteredAsset", back_populates="receipt")
