import logging
from typing import List, Optional
from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header, Request, Response,
    Query, Path, BackgroundTasks
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.asset import RegisteredAsset
from app.schemas.asset import (
    AssetRegistrationResponse,
    AssetSummaryResponse,
    AssetDetailResponse,
)
from app.schemas.receipt import (
    ReceiptResponse,
    ReceiptVerifyRequest,
    ReceiptVerifyResponse,
)
from app.schemas.job import JobSubmissionResponse
from app.services.registration_service import (
    register_asset,
    get_user_assets,
    get_asset_by_id,
    verify_receipt_record,
    validate_image_bytes,
    RegistrationError,
    RegistrationValidationError,
    RegistrationStorageError,
    InvalidImageError,
)
from app.services.job_service import create_job, run_async_registration_worker
from storage import get_storage


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["Asset Registration"])


@router.post(
    "/register",
    response_model=AssetRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new image asset and embed watermark"
)
async def register_asset_endpoint(
    request: Request,
    response: Response,
    file: UploadFile = File(..., description="Original image file to watermark and register"),
    title: str = Form(..., min_length=1, max_length=255, description="Asset title"),
    ownership_declaration: str = Form(
        ...,
        min_length=10,
        description="Explicit declaration statement asserting ownership of the work"
    ),
    algorithm: str = Form("dct_svd", description="Watermarking algorithm: dct_svd, dct, or svd"),
    alpha: float = Form(0.10, ge=0.01, le=1.0, description="Embedding strength factor"),
    category: Optional[str] = Form("Other", description="Image category"),
    country: Optional[str] = Form("International", description="Creator country"),
    license_type: Optional[str] = Form("All Rights Reserved", description="Licensing preference"),
    attribution_text: Optional[str] = Form(None, description="Attribution notice"),
    idempotency_key: Optional[str] = Header(
        None,
        alias="Idempotency-Key",
        description="Optional unique key to ensure request idempotency"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register an image asset:

    1. Validates file integrity, dimensions (64x64 to 8192x8192), and supported image formats.
    2. Enforces unique 40-bit numerical asset ID allocation bounded for watermark payload.
    3. Embeds invisible watermark using selected frequency-domain algorithm (default DCT-SVD).
    4. Computes cryptographic SHA-256 fingerprints for both original and watermarked assets.
    5. Issues an immutable, HMAC-SHA256 signed registration receipt.
    6. Atomically commits record to the database; rolls back and cleans disk storage on any failure.
    """
    file_bytes = await file.read()
    filename = file.filename or "uploaded_image.png"

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        asset, receipt, is_duplicate = register_asset(
            db=db,
            user=current_user,
            file_bytes=file_bytes,
            filename=filename,
            title=title,
            ownership_declaration=ownership_declaration,
            algorithm=algorithm,
            alpha=alpha,
            category=category,
            country=country,
            license_type=license_type,
            attribution_text=attribution_text,
            idempotency_key=idempotency_key,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        if is_duplicate:
            response.status_code = status.HTTP_200_OK

        receipt_resp = ReceiptResponse(
            receipt_number=receipt.receipt_number,
            asset_id=receipt.asset_id,
            issued_at=receipt.issued_at,
            issuer=receipt.issuer,
            original_file_sha256=receipt.original_file_sha256,
            watermarked_file_sha256=receipt.watermarked_file_sha256,
            algorithm_version=receipt.algorithm_version,
            payload_version=receipt.payload_version,
            owner_declaration_summary=receipt.owner_declaration_summary,
            legal_disclaimer=receipt.legal_disclaimer,
            receipt_signature=receipt.receipt_signature,
            receipt_payload=receipt.receipt_payload_json,
        )

        return AssetRegistrationResponse(
            asset_id=asset.asset_id,
            registered_asset_id=asset.id,
            title=asset.title,
            original_filename=asset.original_filename,
            original_file_hash=asset.original_file_hash,
            watermarked_file_hash=asset.watermarked_file_hash,
            image_width=asset.image_width,
            image_height=asset.image_height,
            algorithm=asset.algorithm,
            algorithm_version=asset.algorithm_version,
            payload_version=asset.payload_version,
            alpha=asset.alpha,
            registered_at=asset.registered_at,
            receipt=receipt_resp,
            metrics=asset.metrics_json or {},
            category=getattr(asset, "category", "Other") or "Other",
            country=getattr(asset, "country", "International") or "International",
            license_type=getattr(asset, "license_type", "All Rights Reserved") or "All Rights Reserved",
            attribution_text=getattr(asset, "attribution_text", None),
            perceptual_hash=getattr(asset, "perceptual_hash", None),
        )

    except InvalidImageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RegistrationValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    except RegistrationStorageError as e:
        logger.error(f"Storage failure during asset registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage persistence failed during asset registration.",
        )
    except RegistrationError as e:
        logger.error(f"Registration failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Asset registration failed due to an internal server error.",
        )
    except Exception as e:
        logger.exception("Unexpected error during asset registration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred during asset registration.",
        )


@router.post(
    "/register-async",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronously submit an image asset for background watermarking and registration",
)
async def register_asset_async_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Original image file to watermark and register"),
    title: str = Form(..., min_length=1, max_length=255, description="Asset title"),
    ownership_declaration: str = Form(
        ...,
        min_length=10,
        description="Explicit declaration statement asserting ownership of the work"
    ),
    algorithm: str = Form("dct_svd", description="Watermarking algorithm: dct_svd, dct, or svd"),
    alpha: float = Form(0.10, ge=0.01, le=1.0, description="Embedding strength factor"),
    idempotency_key: Optional[str] = Header(
        None,
        alias="Idempotency-Key",
        description="Optional unique key to ensure request idempotency"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit an image asset for background processing:

    1. Validates file format, size, dimensions (64x64 to 8192x8192), and supported algorithm.
    2. Persists an initial AsyncJob record with PENDING status.
    3. Dispatches async worker task to background queue for DCT-SVD computation and receipt signing.
    4. Returns HTTP 202 Accepted with job_id and status polling URL (/api/v1/jobs/{job_id}).
    """
    if algorithm not in ("dct_svd", "dct", "svd"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported watermarking algorithm '{algorithm}'. Supported: dct_svd, dct, svd",
        )

    file_bytes = await file.read()
    filename = file.filename or "uploaded_image.png"

    # Upfront dimensional and image validation before queuing
    try:
        validate_image_bytes(file_bytes, filename)
    except InvalidImageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    job = create_job(db, current_user.id, title=title.strip())

    background_tasks.add_task(
        run_async_registration_worker,
        job_id=job.id,
        user_id=current_user.id,
        file_bytes=file_bytes,
        filename=filename,
        title=title,
        ownership_declaration=ownership_declaration,
        algorithm=algorithm,
        alpha=alpha,
        idempotency_key=idempotency_key,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    return JobSubmissionResponse(
        job_id=job.id,
        status="PENDING",
        job_type="ASSET_REGISTRATION",
        poll_url=f"/api/v1/jobs/{job.id}",
        message="Asset registration accepted for background processing.",
    )


@router.get(
    "",
    response_model=List[AssetSummaryResponse],
    summary="List registered assets for current user"
)
def list_assets(
    category: Optional[str] = Query(None, description="Filter by category"),
    country: Optional[str] = Query(None, description="Filter by country"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all assets registered by the authenticated user with optional filtering."""
    assets = get_user_assets(db, current_user.id, skip=skip, limit=limit, category=category, country=country)
    return [
        AssetSummaryResponse(
            asset_id=a.asset_id,
            registered_asset_id=a.id,
            title=a.title,
            original_filename=a.original_filename,
            original_file_hash=a.original_file_hash,
            watermarked_file_hash=a.watermarked_file_hash,
            image_width=a.image_width,
            image_height=a.image_height,
            algorithm=a.algorithm,
            registered_at=a.registered_at,
            status=a.status,
            category=getattr(a, "category", "Other") or "Other",
            country=getattr(a, "country", "International") or "International",
            license_type=getattr(a, "license_type", "All Rights Reserved") or "All Rights Reserved",
            attribution_text=getattr(a, "attribution_text", None),
            perceptual_hash=getattr(a, "perceptual_hash", None),
        )
        for a in assets
    ]


@router.get(
    "/{asset_id}",
    response_model=AssetDetailResponse,
    summary="Get details of a registered asset"
)
def get_asset(
    asset_id: int = Path(..., ge=1, le=1099511627775, description="Unique 40-bit numerical asset ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed information and receipt for a specific registered asset.
    
    Enforces authorization: users cannot access assets belonging to others.
    """
    asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found.",
        )

    if asset.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this asset.",
        )

    receipt_resp = None
    if asset.receipt:
        receipt_resp = ReceiptResponse(
            receipt_number=asset.receipt.receipt_number,
            asset_id=asset.receipt.asset_id,
            issued_at=asset.receipt.issued_at,
            issuer=asset.receipt.issuer,
            original_file_sha256=asset.receipt.original_file_sha256,
            watermarked_file_sha256=asset.receipt.watermarked_file_sha256,
            algorithm_version=asset.receipt.algorithm_version,
            payload_version=asset.receipt.payload_version,
            owner_declaration_summary=asset.receipt.owner_declaration_summary,
            legal_disclaimer=asset.receipt.legal_disclaimer,
            receipt_signature=asset.receipt.receipt_signature,
            receipt_payload=asset.receipt.receipt_payload_json,
        )

    return AssetDetailResponse(
        asset_id=asset.asset_id,
        registered_asset_id=asset.id,
        owner_id=asset.owner_id,
        owner_name=asset.owner.full_name if asset.owner else current_user.full_name,
        title=asset.title,
        original_filename=asset.original_filename,
        original_file_hash=asset.original_file_hash,
        original_file_size=asset.original_file_size,
        original_mime_type=asset.original_mime_type,
        image_width=asset.image_width,
        image_height=asset.image_height,
        watermarked_file_hash=asset.watermarked_file_hash,
        watermarked_file_size=asset.watermarked_file_size,
        storage_path_watermarked=asset.storage_path_watermarked,
        algorithm=asset.algorithm,
        algorithm_version=asset.algorithm_version,
        payload_version=asset.payload_version,
        alpha=asset.alpha,
        status=asset.status,
        ownership_declaration=asset.ownership_declaration,
        ownership_declared_at=asset.ownership_declared_at,
        registered_at=asset.registered_at,
        metrics=asset.metrics_json,
        receipt=receipt_resp,
        category=getattr(asset, "category", "Other") or "Other",
        country=getattr(asset, "country", "International") or "International",
        license_type=getattr(asset, "license_type", "All Rights Reserved") or "All Rights Reserved",
        attribution_text=getattr(asset, "attribution_text", None),
        perceptual_hash=getattr(asset, "perceptual_hash", None),
    )


@router.get(
    "/{asset_id}/receipt",
    response_model=ReceiptResponse,
    summary="Get registration receipt for an asset"
)
def get_receipt(
    asset_id: int = Path(..., ge=1, le=1099511627775, description="Unique 40-bit numerical asset ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the authoritative registration receipt for an asset."""
    asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found.",
        )

    if asset.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this receipt.",
        )

    if not asset.receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration receipt not found for this asset.",
        )

    r = asset.receipt
    return ReceiptResponse(
        receipt_number=r.receipt_number,
        asset_id=r.asset_id,
        issued_at=r.issued_at,
        issuer=r.issuer,
        original_file_sha256=r.original_file_sha256,
        watermarked_file_sha256=r.watermarked_file_sha256,
        algorithm_version=r.algorithm_version,
        payload_version=r.payload_version,
        owner_declaration_summary=r.owner_declaration_summary,
        legal_disclaimer=r.legal_disclaimer,
        receipt_signature=r.receipt_signature,
        receipt_payload=r.receipt_payload_json,
    )


@router.get(
    "/{asset_id}/download/watermarked",
    summary="Download the watermarked image file"
)
def download_watermarked_image(
    asset_id: int = Path(..., ge=1, le=1099511627775, description="Unique 40-bit numerical asset ID"),
    presigned: bool = Query(False, description="Request time-limited presigned S3 download URL"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the watermarked image for the specified asset.
    
    Enforces authorization: only asset owner can download.
    Supports presigned S3 URL redirect when requested.
    """
    asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found.",
        )

    if asset.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to download this image.",
        )

    storage = get_storage()
    if not storage.exists(asset.storage_path_watermarked):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watermarked file not found in storage.",
        )

    if presigned:
        presigned_url = storage.get_presigned_url(asset.storage_path_watermarked)
        if presigned_url:
            return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    file_bytes = storage.read(asset.storage_path_watermarked)
    return Response(
        content=file_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="creditmera_watermarked_{asset_id}.png"',
        },
    )



@router.post(
    "/receipts/verify",
    response_model=ReceiptVerifyResponse,
    summary="Public verification of registration receipt authenticity"
)
def verify_receipt_endpoint(
    req: ReceiptVerifyRequest,
    db: Session = Depends(get_db),
):
    """Public verification endpoint to authenticate a registration receipt.
    
    Verifies that the HMAC-SHA256 signature is authentic and cross-checks
    with authoritative database registration records.
    """
    res = verify_receipt_record(
        db=db,
        receipt_payload=req.receipt_payload,
        provided_signature=req.receipt_signature,
    )
    return ReceiptVerifyResponse(**res)
