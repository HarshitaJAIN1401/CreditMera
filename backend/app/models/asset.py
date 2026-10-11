"""Registered asset database model.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, BigInteger, Integer, Float, Text, JSON,
    DateTime, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RegisteredAsset(Base):
    __tablename__ = "registered_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 40-bit bounded asset ID used for watermark payload embedding
    asset_id = Column(BigInteger, unique=True, index=True, nullable=False)
    
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    
    # Cryptographic hashes & file metadata
    original_file_hash = Column(String(64), index=True, nullable=False)
    original_file_size = Column(BigInteger, nullable=False)
    original_mime_type = Column(String(64), nullable=False)
    image_width = Column(Integer, nullable=False)
    image_height = Column(Integer, nullable=False)
    
    watermarked_file_hash = Column(String(64), nullable=False)
    watermarked_file_size = Column(BigInteger, nullable=False)
    
    # Storage references (relative keys/paths - never store raw binaries in DB)
    storage_path_original = Column(String(512), nullable=False)
    storage_path_watermarked = Column(String(512), nullable=False)
    
    # Algorithm parameters & version tracking
    algorithm = Column(String(64), nullable=False, default="dct_svd")
    algorithm_version = Column(String(64), nullable=False, default="v1.0-dct-svd")
    payload_version = Column(Integer, nullable=False, default=1)
    alpha = Column(Float, nullable=False, default=0.10)
    timestamp_nonce = Column(BigInteger, nullable=False)
    
    status = Column(String(32), nullable=False, default="REGISTERED")
    
    # Explicit legal declaration of ownership
    ownership_declaration = Column(Text, nullable=False)
    ownership_declared_at = Column(DateTime(timezone=True), nullable=False)
    
    # Idempotency support to prevent duplicate registrations
    idempotency_key = Column(String(128), index=True, nullable=True)
    
    # Embedding metrics (PSNR, SSIM, NC, BER)
    metrics_json = Column(JSON, nullable=True)

    # International Attribution & Digital Passport Metadata
    category = Column(String(64), nullable=True, default="Other")
    country = Column(String(64), nullable=True, default="International")
    license_type = Column(String(64), nullable=True, default="All Rights Reserved")
    attribution_text = Column(String(255), nullable=True)
    perceptual_hash = Column(String(64), nullable=True, index=True)
    
    registered_at = Column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "asset_id >= 1 AND asset_id <= 1099511627775",
            name="ck_asset_id_40bit_range"
        ),
        UniqueConstraint(
            "owner_id", "idempotency_key",
            name="uq_owner_idempotency_key"
        ),
    )

    # Relationships
    owner = relationship("User", back_populates="assets")
    receipt = relationship(
        "RegistrationReceipt",
        back_populates="asset",
        uselist=False,
        cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="asset",
        cascade="all, delete-orphan"
    )
