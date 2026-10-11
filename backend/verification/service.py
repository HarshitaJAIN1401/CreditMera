"""CreditMera Phase 4 Ownership Verification Service.

Orchestrates:
1. Strict input validation, dimensional checks, and decompression-bomb protection.
2. Blind frequency-domain watermark extraction using DCT-SVD, DCT, or SVD.
3. Cryptographic payload validation (magic header 0xC1, CRC-16, truncated HMAC-SHA256).
4. Authoritative database lookup against registered assets.
5. Image integrity classification (unmodified copy vs re-encoded/modified).
6. Registration receipt verification (client-supplied and server-stored).
7. Authorization and privacy enforcement (strict isolation of owner details from public queries).
8. Clear structured result classification into explicit verification states:
   - MATCHED
   - NOT_DETECTED
   - INVALID_WATERMARK
   - NO_REGISTERED_RECORD
   - INCONCLUSIVE
"""
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    compute_sha256,
    verify_receipt_signature,
)
from app.models.user import User
from app.models.asset import RegisteredAsset
from app.models.receipt import RegistrationReceipt
from app.schemas.verification import (
    VerificationStatus,
    IntegrityStatus,
    AssetMatchDetails,
    ReceiptVerificationSummary,
    OwnershipStatus,
    VerificationDiagnostics,
    VerificationResponse,
)
from app.services.registration_service import (
    InvalidImageError,
    verify_receipt_record,
)
from watermark.transforms import decode_image
from watermark.extraction import extract_watermark, ExtractionResult
from watermark.payload import MAGIC_VERSION_BYTE, PAYLOAD_BIT_LENGTH


LEGAL_VERIFICATION_DISCLAIMER = (
    "Watermark verification confirms cryptographic correlation between the embedded payload "
    "and authoritative database registration records. It establishes technical chain-of-custody "
    "and timestamped registration evidence, but does not independently establish statutory copyright "
    "ownership, judicial copyright title, or prove that the media has never been altered."
)


def validate_verification_image(raw_bytes: bytes, filename: str) -> np.ndarray:
    """Validate image bytes, extension, format, and dimensions against security policies.

    Enforces decompression-bomb limits and dimension bounds.
    Returns decoded RGB numpy array.
    """
    settings = get_settings()

    if not raw_bytes or len(raw_bytes) == 0:
        raise InvalidImageError("Uploaded file is empty (0 bytes).")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise InvalidImageError(
            f"Uploaded file exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in settings.allowed_extensions_set:
        raise InvalidImageError(
            f"File extension '{ext}' is not permitted. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )

    try:
        rgb_array = decode_image(raw_bytes)
    except ValueError as e:
        raise InvalidImageError(f"Image validation failed: {str(e)}")
    except Exception as e:
        raise InvalidImageError(f"Cannot parse uploaded file as valid image: {str(e)}")

    height, width, _ = rgb_array.shape
    if width < settings.MIN_IMAGE_DIMENSION or height < settings.MIN_IMAGE_DIMENSION:
        raise InvalidImageError(
            f"Image dimensions ({width}x{height}) are smaller than minimum required "
            f"({settings.MIN_IMAGE_DIMENSION}x{settings.MIN_IMAGE_DIMENSION})."
        )

    if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
        raise InvalidImageError(
            f"Image dimensions ({width}x{height}) exceed maximum allowed "
            f"({settings.MAX_IMAGE_DIMENSION}x{settings.MAX_IMAGE_DIMENSION})."
        )

    return rgb_array


def verify_image_ownership(
    db: Session,
    file_bytes: bytes,
    filename: str,
    algorithm: str = "dct_svd",
    alpha: float = 0.10,
    expected_asset_id: Optional[int] = None,
    receipt_payload: Optional[Dict[str, Any]] = None,
    receipt_signature: Optional[str] = None,
    current_user: Optional[User] = None,
) -> VerificationResponse:
    """Perform end-to-end watermark extraction and ownership verification.

    Args:
        db: Active database session.
        file_bytes: Raw bytes of the suspect image.
        filename: Original filename of uploaded image.
        algorithm: Watermarking algorithm to evaluate ('dct_svd', 'dct', 'svd').
        alpha: Embedding strength factor used during embedding.
        expected_asset_id: Optional asset ID to evaluate correlation against.
        receipt_payload: Optional client-provided registration receipt JSON.
        receipt_signature: Optional client-provided HMAC-SHA256 signature.
        current_user: Authenticated user if request is authorized, else None.

    Returns:
        VerificationResponse: Structured result with explicit state and diagnostics.
    """
    settings = get_settings()

    # 1. Image security validation & decoding
    rgb_array = validate_verification_image(file_bytes, filename)
    suspect_hash = compute_sha256(file_bytes)

    # 2. Blind watermark extraction using system secret key
    extraction: ExtractionResult = extract_watermark(
        image_source=rgb_array,
        secret_key=settings.WATERMARK_SECRET_KEY,
        algorithm=algorithm,
        alpha=alpha,
        expected_asset_id=expected_asset_id,
    )

    # Inspect first byte of extracted bitstream
    magic_header_valid = False
    if len(extraction.extracted_bits) >= 8:
        extracted_first_byte = int(np.packbits(extraction.extracted_bits[:8].astype(np.uint8))[0])
        magic_header_valid = (extracted_first_byte == MAGIC_VERSION_BYTE)

    diagnostics = VerificationDiagnostics(
        crc_passed=extraction.crc_passed,
        hmac_passed=extraction.hmac_passed,
        magic_header_valid=magic_header_valid,
        raw_status=extraction.status,
        elapsed_seconds=extraction.elapsed_seconds,
        normalized_correlation=extraction.nc,
        bit_error_rate=extraction.ber,
    )

    # 3. Decision classification into explicit states
    # Case A: Cryptographically authenticated watermark extracted
    if extraction.valid and extraction.status == "AUTHENTICATED" and extraction.asset_id is not None:
        extracted_asset_id = extraction.asset_id

        # Query database for registered asset record
        asset = db.query(RegisteredAsset).filter(
            RegisteredAsset.asset_id == extracted_asset_id
        ).first()

        if not asset:
            # Valid watermark under system key, but no database registration record exists
            return VerificationResponse(
                status=VerificationStatus.NO_REGISTERED_RECORD,
                confidence=0.95,
                asset_id=extracted_asset_id,
                algorithm=extraction.algorithm,
                integrity_status=IntegrityStatus.NOT_APPLICABLE,
                hash_matched=False,
                match_details=None,
                receipt_verification=None,
                ownership_status=None,
                message=(
                    f"A valid, authenticated watermark was extracted (Asset ID: {extracted_asset_id}), "
                    "but no corresponding registration record exists in the database."
                ),
                legal_disclaimer=LEGAL_VERIFICATION_DISCLAIMER,
                diagnostics=diagnostics,
            )

        # MATCHED: Valid watermark matches authoritative registration record!
        # Check image hash integrity
        if suspect_hash == asset.watermarked_file_hash:
            integrity_status = IntegrityStatus.UNMODIFIED_COPY
            hash_matched = True
        else:
            integrity_status = IntegrityStatus.MODIFIED_RE_ENCODED
            hash_matched = False

        # Build public match summary
        match_details = AssetMatchDetails(
            registered_asset_id=str(asset.id),
            asset_id=asset.asset_id,
            title=asset.title,
            registered_at=asset.registered_at.isoformat() if asset.registered_at else "",
            algorithm=asset.algorithm,
            algorithm_version=asset.algorithm_version,
            alpha=asset.alpha,
            image_width=asset.image_width,
            image_height=asset.image_height,
            ownership_declaration_summary=(
                asset.ownership_declaration[:200] + "..."
                if len(asset.ownership_declaration) > 200
                else asset.ownership_declaration
            ),
        )

        # Receipt verification
        receipt_summary: Optional[ReceiptVerificationSummary] = None
        if receipt_payload and receipt_signature:
            # Client provided receipt
            rv = verify_receipt_record(db, receipt_payload, receipt_signature)
            receipt_asset_id = receipt_payload.get("asset_id")
            matches_asset = (receipt_asset_id == extracted_asset_id)
            receipt_summary = ReceiptVerificationSummary(
                receipt_number=receipt_payload.get("receipt_number"),
                is_authentic=rv["is_authentic"] and matches_asset,
                signature_valid=rv["signature_valid"],
                database_match=rv["database_match"] and matches_asset,
                status=rv["status"] if matches_asset else "RECEIPT_ASSET_ID_MISMATCH",
                message=(
                    rv["message"]
                    if matches_asset
                    else "Supplied receipt signature is valid but corresponds to a different asset."
                ),
            )
        elif asset.receipt:
            # Verify authoritative stored registration receipt
            is_valid_sig = verify_receipt_signature(
                asset.receipt.receipt_payload_json,
                asset.receipt.receipt_signature,
                settings.SECRET_KEY,
            )
            receipt_summary = ReceiptVerificationSummary(
                receipt_number=asset.receipt.receipt_number,
                is_authentic=is_valid_sig,
                signature_valid=is_valid_sig,
                database_match=True,
                status="AUTHENTIC" if is_valid_sig else "STORED_RECEIPT_CORRUPTED",
                message=(
                    "Authoritative registration receipt on file is cryptographically authentic."
                    if is_valid_sig
                    else "Stored registration receipt failed cryptographic signature verification."
                ),
            )

        # Ownership authorization & privacy isolation
        ownership_status: OwnershipStatus
        if current_user is not None:
            if current_user.id == asset.owner_id:
                ownership_status = OwnershipStatus(
                    is_owner=True,
                    owner_display=current_user.email,
                )
            else:
                ownership_status = OwnershipStatus(
                    is_owner=False,
                    owner_display="Registered User (Non-Owner)",
                )
        else:
            ownership_status = OwnershipStatus(
                is_owner=None,
                owner_display="Registered Owner (Confidential)",
            )

        confidence_score = 1.0
        if extraction.nc is not None:
            confidence_score = round(float(extraction.nc), 4)

        return VerificationResponse(
            status=VerificationStatus.MATCHED,
            confidence=confidence_score,
            asset_id=extracted_asset_id,
            algorithm=extraction.algorithm,
            integrity_status=integrity_status,
            hash_matched=hash_matched,
            match_details=match_details,
            receipt_verification=receipt_summary,
            ownership_status=ownership_status,
            message=(
                f"Successfully verified watermark matching registered asset '{asset.title}' "
                f"(Asset ID: {extracted_asset_id}). "
                + (
                    "Image is an exact byte-for-byte match to the watermarked distribution."
                    if hash_matched
                    else "Image file hash differs from the registered watermarked distribution copy (consistent with re-encoding, format conversion, or compression), while the embedded watermark survived and was verified."
                )
            ),
            legal_disclaimer=LEGAL_VERIFICATION_DISCLAIMER,
            diagnostics=diagnostics,
        )

    # Case B: Inconclusive signal detection
    # Occurs when an expected asset ID was provided and partial correlation exists (0.50 <= NC < 0.85),
    # but the payload cannot be cryptographically authenticated due to channel degradation.
    if expected_asset_id is not None and extraction.nc is not None and 0.50 <= extraction.nc < 0.85:
        return VerificationResponse(
            status=VerificationStatus.INCONCLUSIVE,
            confidence=round(float(extraction.nc), 4),
            asset_id=expected_asset_id,
            algorithm=extraction.algorithm,
            integrity_status=IntegrityStatus.NOT_APPLICABLE,
            hash_matched=False,
            match_details=None,
            receipt_verification=None,
            ownership_status=None,
            message=(
                f"Extraction confidence is inconclusive (NC = {extraction.nc:.4f}). "
                "Partial correlation detected against claimed asset ID, but payload "
                "does not satisfy cryptographic integrity requirements."
            ),
            legal_disclaimer=LEGAL_VERIFICATION_DISCLAIMER,
            diagnostics=diagnostics,
        )

    # Case C: Candidate watermark detected, but failed integrity or HMAC authentication
    if magic_header_valid:
        # Magic header 0xC1 was present, but CRC or HMAC failed
        return VerificationResponse(
            status=VerificationStatus.INVALID_WATERMARK,
            confidence=0.0,
            asset_id=extraction.asset_id,
            algorithm=extraction.algorithm,
            integrity_status=IntegrityStatus.NOT_APPLICABLE,
            hash_matched=False,
            match_details=None,
            receipt_verification=None,
            ownership_status=None,
            message=(
                f"Candidate watermark structure detected, but failed integrity verification ({extraction.status}). "
                "The watermark payload appears corrupted, altered, or forged."
            ),
            legal_disclaimer=LEGAL_VERIFICATION_DISCLAIMER,
            diagnostics=diagnostics,
        )

    # Case D: Unrecognized header or unwatermarked image
    return VerificationResponse(
        status=VerificationStatus.NOT_DETECTED,
        confidence=0.0,
        asset_id=None,
        algorithm=extraction.algorithm,
        integrity_status=IntegrityStatus.NOT_APPLICABLE,
        hash_matched=False,
        match_details=None,
        receipt_verification=None,
        ownership_status=None,
        message="No sufficiently reliable watermark detected in the image.",
        legal_disclaimer=LEGAL_VERIFICATION_DISCLAIMER,
        diagnostics=diagnostics,
    )
