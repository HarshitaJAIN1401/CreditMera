"""Asynchronous Background Job Service for CreditMera.

Orchestrates background tasks, job creation, state transitions (PENDING -> PROCESSING -> COMPLETED/FAILED),
progress reporting, and isolated database transaction commits.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.job import AsyncJob
from app.services.registration_service import (
    register_asset,
    RegistrationError,
    RegistrationValidationError,
    RegistrationStorageError,
    InvalidImageError,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_job(
    db: Session,
    user_id: str,
    title: Optional[str] = None,
    job_type: str = "ASSET_REGISTRATION",
) -> AsyncJob:
    """Create and persist a new background job with PENDING status."""
    job = AsyncJob(
        user_id=user_id,
        job_type=job_type,
        status="PENDING",
        progress=0,
        title=title,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_by_id(db: Session, job_id: str, user_id: str) -> Optional[AsyncJob]:
    """Retrieve job by ID enforcing owner authorization."""
    return db.query(AsyncJob).filter(AsyncJob.id == job_id, AsyncJob.user_id == user_id).first()


def list_user_jobs(
    db: Session,
    user_id: str,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[AsyncJob], int]:
    """List jobs for an authenticated user with pagination and total count."""
    query = db.query(AsyncJob).filter(AsyncJob.user_id == user_id)
    total = query.count()
    jobs = query.order_by(AsyncJob.created_at.desc()).offset(skip).limit(limit).all()
    return jobs, total


def run_async_registration_worker(
    job_id: str,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    title: str,
    ownership_declaration: str,
    algorithm: str,
    alpha: float,
    idempotency_key: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_factory=None,
) -> None:
    """Background worker task executed asynchronously in worker thread pool.

    Manages its own isolated database transaction session to update progress
    and commit the registered asset, receipt, and audit entry.
    """
    factory = session_factory or SessionLocal
    db: Session = factory()
    try:
        job = db.query(AsyncJob).filter(AsyncJob.id == job_id).first()
        if not job:
            logger.error(f"Async worker: job {job_id} not found in database.")
            return

        # 1. Transition to PROCESSING
        job.status = "PROCESSING"
        job.progress = 20
        job.updated_at = utc_now()
        db.commit()

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            job.status = "FAILED"
            job.progress = 0
            job.error_message = "User account not found."
            job.completed_at = utc_now()
            db.commit()
            return

        job.progress = 50
        db.commit()

        # 2. Execute core registration
        asset, receipt, is_duplicate = register_asset(
            db=db,
            user=user,
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

        # 3. Transition to COMPLETED
        job.status = "COMPLETED"
        job.progress = 100
        job.asset_id = asset.asset_id
        job.result_json = {
            "asset_id": asset.asset_id,
            "registered_asset_id": asset.id,
            "title": asset.title,
            "original_filename": asset.original_filename,
            "original_file_hash": asset.original_file_hash,
            "watermarked_file_hash": asset.watermarked_file_hash,
            "algorithm": asset.algorithm,
            "registered_at": asset.registered_at.isoformat() if asset.registered_at else None,
            "receipt_number": receipt.receipt_number,
            "receipt_signature": receipt.receipt_signature,
            "metrics": asset.metrics_json or {},
            "is_duplicate": is_duplicate,
        }
        job.completed_at = utc_now()
        job.updated_at = utc_now()
        db.commit()
        logger.info(f"Async registration job {job_id} completed successfully for asset {asset.asset_id}.")

    except (InvalidImageError, RegistrationValidationError) as ve:
        db.rollback()
        logger.warning(f"Validation error in job {job_id}: {ve}")
        _mark_job_failed(db, job_id, str(ve))
    except RegistrationStorageError as se:
        db.rollback()
        logger.error(f"Storage error in job {job_id}: {se}")
        _mark_job_failed(db, job_id, "Storage persistence failed during background processing.")
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error executing async registration job {job_id}: {e}")
        _mark_job_failed(db, job_id, "An unexpected internal error occurred during background processing.")
    finally:
        db.close()


def _mark_job_failed(db: Session, job_id: str, error_message: str) -> None:
    """Helper to safely record job failure."""
    try:
        job = db.query(AsyncJob).filter(AsyncJob.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.progress = 0
            job.error_message = error_message
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            db.commit()
    except Exception as err:
        logger.error(f"Failed to record failure for job {job_id}: {err}")
        db.rollback()
