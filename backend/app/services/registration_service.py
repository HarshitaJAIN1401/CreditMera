"""Ownership Registration Service for CreditMera.

Orchestrates:
1. Input validation (dimensions, formats, file integrity, sizes).
2. Idempotency checks to prevent accidental duplicate registrations.
3. Cryptographically unique 40-bit asset ID allocation with DB constraint checks.
4. Invisible watermark embedding via DCT-SVD engine.
5. Isolated storage persistence of original and watermarked assets.
6. Server-side HMAC-signed receipt issuance with ownership declaration audit.
7. Strict transactional integrity and automatic file cleanup on any failure.
"""
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.security import (
    compute_sha256,
    generate_secure_asset_id,
    is_valid_asset_id,
    sign_receipt,
    verify_receipt_signature,
)
from app.models.user import User
from app.models.asset import RegisteredAsset
from app.models.receipt import RegistrationReceipt
from app.models.audit import AuditLog
from storage import get_storage
from watermark.embedding import embed_watermark
from watermark.transforms import decode_image


class RegistrationError(Exception):
    """Base exception for asset registration failures."""
    pass


class RegistrationValidationError(RegistrationError):
    """Raised when client input data or parameters fail validation."""
    pass


class RegistrationStorageError(RegistrationError):
    """Raised when storage persistence or file system operations fail."""
    pass


class InvalidImageError(RegistrationValidationError):
    """Raised when an uploaded file is not a valid image or does not meet dimensional bounds."""
    pass


class IdempotencyDuplicateError(RegistrationError):
    """Raised when an idempotency key collision occurs."""
    pass


LEGAL_DISCLAIMER_TEXT = (
    "This registration receipt documents an authoritative system record entry in CreditMera. "
    "It provides cryptographic evidence of asset watermarking, original cryptographic fingerprinting, "
    "and timestamped ownership declaration. It does not constitute a judicial ruling, statutory copyright "
    "grant, or conclusive legal determination of intellectual property ownership."
)


def validate_image_bytes(raw_bytes: bytes, filename: str) -> Tuple[int, int, str]:
    """Validate image bytes, extension, format, and dimensions.
    
    Returns (width, height, mime_type) if valid.
    Raises InvalidImageError if invalid.
    """
    settings = get_settings()
    
    # 1. Size check
    if not raw_bytes or len(raw_bytes) == 0:
        raise InvalidImageError("Uploaded file is empty (0 bytes).")
    
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise InvalidImageError(
            f"Uploaded file exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    # 2. Extension check
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in settings.allowed_extensions_set:
        raise InvalidImageError(
            f"File extension '{ext}' is not permitted. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )

    # 3. Decode and dimensional check
    try:
        rgb_array = decode_image(raw_bytes)
        height, width, _ = rgb_array.shape
    except ValueError as e:
        raise InvalidImageError(f"Image validation failed: {str(e)}")
    except Exception as e:
        raise InvalidImageError(f"Cannot parse uploaded file as valid image: {str(e)}")

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

    # Resolve MIME type
    mime_type_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }
    mime_type = mime_type_map.get(ext, "application/octet-stream")

    return width, height, mime_type


def allocate_unique_asset_id(db: Session, max_retries: int = 10) -> int:
    """Generate a collision-safe 40-bit asset ID validated against the database.
    
    Enforces the 40-bit bounds [1, 2^40 - 1] matching watermark payload capacity.
    """
    for _ in range(max_retries):
        candidate_id = generate_secure_asset_id()
        if not is_valid_asset_id(candidate_id):
            continue
        exists = db.query(RegisteredAsset.id).filter(
            RegisteredAsset.asset_id == candidate_id
        ).first()
        if not exists:
            return candidate_id

    raise RegistrationError("Unable to allocate a unique asset ID after maximum retries.")


def register_asset(
    db: Session,
    user: User,
    file_bytes: bytes,
    filename: str,
    title: str,
    ownership_declaration: str,
    algorithm: str = "dct_svd",
    alpha: float = 0.10,
    category: Optional[str] = "Other",
    country: Optional[str] = "International",
    license_type: Optional[str] = "All Rights Reserved",
    attribution_text: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[RegisteredAsset, RegistrationReceipt, bool]:
    """Register an image asset with watermarking, receipt generation, and DB persistence.
    
    Returns:
        Tuple[RegisteredAsset, RegistrationReceipt, is_idempotent_duplicate]
    """
    settings = get_settings()
    storage = get_storage()
    saved_files: List[str] = []

    # 1. Check idempotency: If existing asset with this idempotency key exists for this user, return it
    if idempotency_key and idempotency_key.strip():
        clean_idem_key = idempotency_key.strip()
        existing = db.query(RegisteredAsset).filter(
            RegisteredAsset.owner_id == user.id,
            RegisteredAsset.idempotency_key == clean_idem_key,
        ).first()
        if existing and existing.receipt:
            return existing, existing.receipt, True
    else:
        clean_idem_key = None

    # 2. Validate declaration and parameters
    clean_declaration = ownership_declaration.strip() if ownership_declaration else ""
    if len(clean_declaration) < 10:
        raise RegistrationValidationError(
            "An explicit ownership declaration of at least 10 characters is required."
        )

    algo_clean = algorithm.lower().strip() if algorithm else ""
    if algo_clean not in ("dct_svd", "dct-svd", "hybrid", "dct", "baseline_dct", "svd", "baseline_svd"):
        raise RegistrationValidationError(
            f"Unknown watermarking algorithm '{algorithm}'. Supported: dct_svd, dct, svd."
        )

    # 3. Validate image
    width, height, mime_type = validate_image_bytes(file_bytes, filename)
    ext = Path(filename).suffix.lstrip(".").lower()

    # 4. Compute original cryptographic hash
    original_file_hash = compute_sha256(file_bytes)
    now = datetime.now(timezone.utc)
    ts_nonce = int(now.timestamp()) & 0xFFFFFFFF

    # 5. Allocate 40-bit unique asset ID
    asset_id = allocate_unique_asset_id(db)

    try:
        # 6. Embed invisible watermark
        embedding_res = embed_watermark(
            image_source=file_bytes,
            asset_id=asset_id,
            secret_key=settings.WATERMARK_SECRET_KEY,
            algorithm=algorithm,
            alpha=alpha,
            timestamp_nonce=ts_nonce,
            output_format="PNG",
        )
        watermarked_bytes = embedding_res.watermarked_bytes
        watermarked_file_hash = compute_sha256(watermarked_bytes)

        # 7. Persist original and watermarked image files in storage
        orig_rel_path = f"originals/{asset_id}_{original_file_hash[:12]}.{ext}"
        wm_rel_path = f"watermarked/{asset_id}_{watermarked_file_hash[:12]}.png"

        try:
            storage.save(file_bytes, orig_rel_path)
            saved_files.append(orig_rel_path)

            storage.save(watermarked_bytes, wm_rel_path)
            saved_files.append(wm_rel_path)
        except Exception as storage_err:
            raise RegistrationStorageError(f"Storage persistence failed: {str(storage_err)}") from storage_err

        # 8. Create Registration Receipt
        receipt_date_str = now.strftime("%Y%m%d")
        rand_token = secrets.token_hex(6).upper()
        receipt_number = f"CMR-REC-{receipt_date_str}-{rand_token}"

        receipt_canonical_payload = {
            "receipt_number": receipt_number,
            "asset_id": asset_id,
            "owner_id": str(user.id),
            "owner_email": user.email,
            "owner_name": user.full_name,
            "original_file_sha256": original_file_hash,
            "watermarked_file_sha256": watermarked_file_hash,
            "algorithm": embedding_res.algorithm,
            "algorithm_version": settings.ALGORITHM_VERSION,
            "payload_version": 1,
            "alpha": float(alpha),
            "image_width": width,
            "image_height": height,
            "registered_at": now.isoformat(),
            "ownership_declaration": clean_declaration,
            "disclaimer": LEGAL_DISCLAIMER_TEXT,
        }

        receipt_signature = sign_receipt(receipt_canonical_payload, settings.SECRET_KEY)

        # Compute perceptual hash for visual similarity lookup
        try:
            from watermark.similarity import compute_phash
            from watermark.transforms import decode_image
            perceptual_hash = compute_phash(decode_image(file_bytes))
        except Exception:
            perceptual_hash = None

        # 9. Build DB models within transaction
        registered_asset = RegisteredAsset(
            asset_id=asset_id,
            owner_id=user.id,
            title=title.strip() or f"Untitled Asset {asset_id}",
            original_filename=filename,
            original_file_hash=original_file_hash,
            original_file_size=len(file_bytes),
            original_mime_type=mime_type,
            image_width=width,
            image_height=height,
            watermarked_file_hash=watermarked_file_hash,
            watermarked_file_size=len(watermarked_bytes),
            storage_path_original=orig_rel_path,
            storage_path_watermarked=wm_rel_path,
            algorithm=embedding_res.algorithm,
            algorithm_version=settings.ALGORITHM_VERSION,
            payload_version=1,
            alpha=float(alpha),
            timestamp_nonce=ts_nonce,
            status="REGISTERED",
            ownership_declaration=clean_declaration,
            ownership_declared_at=now,
            idempotency_key=clean_idem_key,
            metrics_json=embedding_res.metrics,
            category=category or "Other",
            country=country or "International",
            license_type=license_type or "All Rights Reserved",
            attribution_text=attribution_text,
            perceptual_hash=perceptual_hash,
            registered_at=now,
        )
        db.add(registered_asset)
        db.flush()  # Populates registered_asset.id

        receipt = RegistrationReceipt(
            receipt_number=receipt_number,
            registered_asset_id=registered_asset.id,
            asset_id=asset_id,
            issued_at=now,
            issuer=settings.RECEIPT_ISSUER,
            original_file_sha256=original_file_hash,
            watermarked_file_sha256=watermarked_file_hash,
            algorithm_version=settings.ALGORITHM_VERSION,
            payload_version=1,
            owner_declaration_summary=clean_declaration[:250],
            legal_disclaimer=LEGAL_DISCLAIMER_TEXT,
            receipt_payload_json=receipt_canonical_payload,
            receipt_signature=receipt_signature,
        )
        db.add(receipt)

        audit_entry = AuditLog(
            asset_id=asset_id,
            registered_asset_id=registered_asset.id,
            user_id=user.id,
            action="ASSET_REGISTERED",
            status="SUCCESS",
            ip_address=client_ip,
            user_agent=user_agent,
            details={
                "receipt_number": receipt_number,
                "original_file_hash": original_file_hash,
                "watermarked_file_hash": watermarked_file_hash,
                "algorithm": embedding_res.algorithm,
                "elapsed_seconds": embedding_res.elapsed_seconds,
            },
            created_at=now,
        )
        db.add(audit_entry)

        db.commit()
        db.refresh(registered_asset)
        db.refresh(receipt)

        return registered_asset, receipt, False

    except IntegrityError as ie:
        db.rollback()
        for rel_path in saved_files:
            try:
                storage.delete(rel_path)
            except Exception:
                pass
        err_msg = str(ie).lower()
        # Strictly verify that the IntegrityError is an idempotency uniqueness collision
        is_idempotency_conflict = clean_idem_key and (
            "uq_owner_idempotency_key" in err_msg
            or ("owner_id" in err_msg and "idempotency_key" in err_msg)
        )
        if is_idempotency_conflict:
            existing = db.query(RegisteredAsset).filter(
                RegisteredAsset.owner_id == user.id,
                RegisteredAsset.idempotency_key == clean_idem_key,
            ).first()
            if existing and existing.receipt:
                return existing, existing.receipt, True
        raise RegistrationError(f"Asset registration database integrity error: {str(ie)}") from ie

    except RegistrationStorageError:
        db.rollback()
        for rel_path in saved_files:
            try:
                storage.delete(rel_path)
            except Exception:
                pass
        raise

    except RegistrationValidationError:
        db.rollback()
        for rel_path in saved_files:
            try:
                storage.delete(rel_path)
            except Exception:
                pass
        raise

    except Exception as e:
        db.rollback()
        # Clean up stored files on disk to prevent orphaned files
        for rel_path in saved_files:
            try:
                storage.delete(rel_path)
            except Exception:
                pass

        # Record failure in audit log if possible in separate transaction
        try:
            audit_fail = AuditLog(
                asset_id=asset_id,
                user_id=user.id,
                action="ASSET_REGISTRATION_FAILED",
                status="FAILURE",
                ip_address=client_ip,
                user_agent=user_agent,
                details={"error": str(e), "filename": filename},
                created_at=now,
            )
            db.add(audit_fail)
            db.commit()
        except Exception:
            db.rollback()

        raise RegistrationError(f"Asset registration failed: {str(e)}") from e


def get_user_assets(
    db: Session,
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    country: Optional[str] = None,
) -> List[RegisteredAsset]:
    """Retrieve registered assets owned by the given user with optional filtering."""
    q = db.query(RegisteredAsset).filter(RegisteredAsset.owner_id == user_id)
    if category and category != "All":
        q = q.filter(RegisteredAsset.category == category)
    if country and country != "All":
        q = q.filter(RegisteredAsset.country == country)
    return q.order_by(
        RegisteredAsset.registered_at.desc()
    ).offset(skip).limit(limit).all()


def get_asset_by_id(
    db: Session,
    asset_id: int,
    user_id: Optional[str] = None,
) -> Optional[RegisteredAsset]:
    """Retrieve asset by numerical asset ID, optionally verifying ownership."""
    query = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == asset_id)
    if user_id is not None:
        query = query.filter(RegisteredAsset.owner_id == user_id)
    return query.first()


def verify_receipt_record(
    db: Session,
    receipt_payload: Dict[str, Any],
    provided_signature: str,
) -> Dict[str, Any]:
    """Cryptographically verify receipt and check against authoritative DB record."""
    settings = get_settings()

    # 1. Cryptographic HMAC signature check
    is_sig_valid = verify_receipt_signature(
        receipt_payload, provided_signature, settings.SECRET_KEY
    )
    if not is_sig_valid:
        return {
            "is_authentic": False,
            "signature_valid": False,
            "database_match": False,
            "status": "SIGNATURE_MISMATCH",
            "message": "Cryptographic signature does not match. Receipt payload may have been altered.",
            "asset_id": receipt_payload.get("asset_id"),
            "issued_at": receipt_payload.get("registered_at"),
        }

    # 2. Match against authoritative database
    asset_id = receipt_payload.get("asset_id")
    receipt_num = receipt_payload.get("receipt_number")

    db_receipt = db.query(RegistrationReceipt).filter(
        RegistrationReceipt.receipt_number == receipt_num
    ).first()

    if not db_receipt:
        return {
            "is_authentic": True,
            "signature_valid": True,
            "database_match": False,
            "status": "VALID_SIGNATURE_NO_DB_RECORD",
            "message": "Signature is valid under current system key, but no matching database record was found.",
            "asset_id": asset_id,
            "issued_at": receipt_payload.get("registered_at"),
        }

    # Verify matching original hash and asset ID
    if db_receipt.asset_id != asset_id or db_receipt.original_file_sha256 != receipt_payload.get("original_file_sha256"):
        return {
            "is_authentic": False,
            "signature_valid": True,
            "database_match": False,
            "status": "DB_RECORD_DISCREPANCY",
            "message": "Receipt signature is valid, but record fields contradict authoritative database values.",
            "asset_id": asset_id,
            "issued_at": receipt_payload.get("registered_at"),
        }

    return {
        "is_authentic": True,
        "signature_valid": True,
        "database_match": True,
        "status": "AUTHENTIC",
        "message": "Registration receipt is cryptographically authentic and verified against authoritative database records.",
        "asset_id": asset_id,
        "issued_at": receipt_payload.get("registered_at"),
    }
