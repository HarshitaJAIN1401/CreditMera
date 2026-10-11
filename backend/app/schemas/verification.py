"""Pydantic schemas for ownership verification and result reporting.
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Explicit verification outcome states for CreditMera Phase 4."""
    MATCHED = "MATCHED"
    NOT_DETECTED = "NOT_DETECTED"
    INVALID_WATERMARK = "INVALID_WATERMARK"
    NO_REGISTERED_RECORD = "NO_REGISTERED_RECORD"
    INCONCLUSIVE = "INCONCLUSIVE"


class IntegrityStatus(str, Enum):
    """Image file integrity comparison against registered hashes."""
    UNMODIFIED_COPY = "UNMODIFIED_COPY"
    MODIFIED_RE_ENCODED = "MODIFIED_RE_ENCODED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AssetMatchDetails(BaseModel):
    """Public summary of a matched registered asset."""
    registered_asset_id: str = Field(..., description="UUID of registered asset")
    asset_id: int = Field(..., description="40-bit numerical asset ID embedded in watermark")
    title: str = Field(..., description="Asset title")
    registered_at: str = Field(..., description="ISO 8601 registration timestamp")
    algorithm: str = Field(..., description="Algorithm used during registration")
    algorithm_version: str = Field(..., description="Algorithm version")
    alpha: float = Field(..., description="Embedding strength factor")
    image_width: int = Field(..., description="Original registered image width")
    image_height: int = Field(..., description="Original registered image height")
    ownership_declaration_summary: Optional[str] = Field(
        None,
        description="Public summary of original legal declaration made at registration"
    )


class ReceiptVerificationSummary(BaseModel):
    """Outcome of cryptographic registration receipt verification."""
    receipt_number: Optional[str] = None
    is_authentic: bool = Field(..., description="Whether cryptographic receipt signature is valid")
    signature_valid: bool = Field(..., description="HMAC-SHA256 signature verification status")
    database_match: bool = Field(..., description="Whether receipt matches authoritative DB record")
    status: str = Field(..., description="Detailed receipt status")
    message: str = Field(..., description="Receipt verification narrative")


class OwnershipStatus(BaseModel):
    """Ownership identity and permission status for caller."""
    is_owner: Optional[bool] = Field(
        None,
        description="True if caller is verified as asset owner; False if authenticated non-owner; None if public"
    )
    owner_display: Optional[str] = Field(
        None,
        description="Masked or displayed owner handle (anonymized for public queries)"
    )


class VerificationDiagnostics(BaseModel):
    """Technical extraction and integrity diagnostics."""
    crc_passed: bool
    hmac_passed: bool
    magic_header_valid: bool
    raw_status: str
    elapsed_seconds: float
    normalized_correlation: Optional[float] = None
    bit_error_rate: Optional[float] = None


class VerificationResponse(BaseModel):
    """Structured response for watermark verification endpoint."""
    status: VerificationStatus = Field(..., description="Primary verification outcome state")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Verification confidence score (0.0 to 1.0)")
    asset_id: Optional[int] = Field(None, description="Extracted 40-bit numerical asset ID")
    algorithm: str = Field(..., description="Watermarking algorithm evaluated")
    integrity_status: IntegrityStatus = Field(
        IntegrityStatus.NOT_APPLICABLE,
        description="Integrity status of the suspect image relative to registered copies"
    )
    hash_matched: bool = Field(
        False,
        description="True if suspect image hash exactly matches watermarked distribution hash"
    )
    match_details: Optional[AssetMatchDetails] = Field(
        None,
        description="Details of matched asset record (only present when status is MATCHED)"
    )
    receipt_verification: Optional[ReceiptVerificationSummary] = Field(
        None,
        description="Receipt authenticity details if receipt was supplied or cross-checked"
    )
    ownership_status: Optional[OwnershipStatus] = Field(
        None,
        description="Ownership relationship of caller to verified asset"
    )
    message: str = Field(..., description="Detailed explanatory narrative of verification result")
    legal_disclaimer: str = Field(
        ...,
        description="Legal disclaimer regarding the technical scope of watermark verification"
    )
    diagnostics: Optional[VerificationDiagnostics] = Field(
        None,
        description="Low-level cryptographic and signal metrics"
    )
