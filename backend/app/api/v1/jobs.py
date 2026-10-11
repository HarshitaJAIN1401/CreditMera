"""API routes for asynchronous background job tracking and management.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.job import JobStatusResponse, JobListResponse
from app.services.job_service import get_job_by_id, list_user_jobs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Background Jobs & Scalability"])


@router.get(
    "",
    response_model=JobListResponse,
    summary="List background processing jobs for current user",
)
def list_jobs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all background jobs submitted by the authenticated user."""
    jobs, total = list_user_jobs(db, current_user.id, skip=skip, limit=limit)
    return JobListResponse(
        jobs=[
            JobStatusResponse(
                job_id=j.id,
                user_id=j.user_id,
                job_type=j.job_type,
                status=j.status,
                progress=j.progress,
                title=j.title,
                asset_id=j.asset_id,
                result=j.result_json,
                error_message=j.error_message,
                created_at=j.created_at,
                updated_at=j.updated_at,
                completed_at=j.completed_at,
            )
            for j in jobs
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get background job status and progress",
)
def get_job(
    job_id: str = Path(..., min_length=1, max_length=64, description="Unique job UUID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the real-time processing status, progress percentage, and result of a background job."""
    job = get_job_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    return JobStatusResponse(
        job_id=job.id,
        user_id=job.user_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        title=job.title,
        asset_id=job.asset_id,
        result=job.result_json,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )
