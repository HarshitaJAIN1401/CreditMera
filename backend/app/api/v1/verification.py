"""Ownership verification endpoint for CreditMera Phase 4.
"""
import json
import logging
from typing import Optional
from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_optional_current_user
from app.models.user import User
from app.schemas.verification import VerificationResponse
from app.services.registration_service import InvalidImageError
from verification.service import verify_image_ownership

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ownership Verification"])


@router.post(
    "/verify",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify image watermark, match registered asset, and validate ownership"
)
async def verify_image_endpoint(
    request: Request,
    file: UploadFile = File(..., description="Suspect image file to extract and verify"),
    algorithm: str = Form("dct_svd", description="Watermarking algorithm: dct_svd, dct, or svd"),
    alpha: float = Form(0.10, ge=0.01, le=1.0, description="Embedding strength factor"),
    expected_asset_id: Optional[int] = Form(
        None,
        ge=1,
        le=1099511627775,
        description="Optional expected numerical asset ID to compute NC/BER correlation against"
    ),
    receipt_payload: Optional[str] = Form(
        None,
        description="Optional JSON string of canonical registration receipt payload"
    ),
    receipt_signature: Optional[str] = Form(
        None,
        description="Optional HMAC-SHA256 signature string for client-supplied receipt"
    ),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Blindly extract embedded watermark from a suspect image and verify ownership:

    1. Validates file format, size, dimensions (64x64 to 8192x8192), and decompression-bomb safety.
    2. Blindly extracts candidate 128-bit watermark using frequency-domain algorithm (DCT-SVD).
    3. Validates 0xC1 magic header, CRC-16 error detection, and truncated HMAC-SHA256 authenticity.
    4. Looks up extracted asset ID against authoritative registered asset database records.
    5. Evaluates suspect image file hash for exact match vs re-encoded/modified distribution.
    6. Validates cryptographic registration receipt (client-supplied or authoritative on-file).
    7. Enforces privacy boundaries: protects registered owner identity from unauthorized public queries.
    8. Returns explicit outcome state: MATCHED, NOT_DETECTED, INVALID_WATERMARK, NO_REGISTERED_RECORD, or INCONCLUSIVE.
    """
    file_bytes = await file.read()
    filename = file.filename or "suspect_image.png"

    parsed_receipt_payload = None
    if receipt_payload:
        try:
            parsed_receipt_payload = json.loads(receipt_payload)
            if not isinstance(parsed_receipt_payload, dict):
                raise ValueError("receipt_payload must be a JSON object dictionary")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid receipt_payload JSON: {str(e)}",
            )

    try:
        verification_result = verify_image_ownership(
            db=db,
            file_bytes=file_bytes,
            filename=filename,
            algorithm=algorithm,
            alpha=alpha,
            expected_asset_id=expected_asset_id,
            receipt_payload=parsed_receipt_payload,
            receipt_signature=receipt_signature,
            current_user=current_user,
        )
        return verification_result

    except InvalidImageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error during watermark verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred during watermark verification.",
        )
