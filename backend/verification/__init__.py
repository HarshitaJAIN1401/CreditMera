"""Ownership Verification Package for CreditMera Phase 4.
"""
from verification.service import (
    verify_image_ownership,
    validate_verification_image,
    LEGAL_VERIFICATION_DISCLAIMER,
)
from app.schemas.verification import (
    VerificationStatus,
    IntegrityStatus,
    AssetMatchDetails,
    ReceiptVerificationSummary,
    OwnershipStatus,
    VerificationDiagnostics,
    VerificationResponse,
)

__all__ = [
    "verify_image_ownership",
    "validate_verification_image",
    "LEGAL_VERIFICATION_DISCLAIMER",
    "VerificationStatus",
    "IntegrityStatus",
    "AssetMatchDetails",
    "ReceiptVerificationSummary",
    "OwnershipStatus",
    "VerificationDiagnostics",
    "VerificationResponse",
]
