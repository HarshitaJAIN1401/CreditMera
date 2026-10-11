"""Pydantic request and response schemas for background jobs.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    user_id: str
    job_type: str
    status: str
    progress: int
    title: Optional[str] = None
    asset_id: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class JobSubmissionResponse(BaseModel):
    job_id: str
    status: str
    job_type: str
    poll_url: str
    message: str


class JobListResponse(BaseModel):
    jobs: List[JobStatusResponse]
    total: int
    skip: int
    limit: int
