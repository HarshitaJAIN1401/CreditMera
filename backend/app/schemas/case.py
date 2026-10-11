"""Pydantic schemas for Global Case Management."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    asset_id: int = Field(..., ge=1, le=1099511627775, description="Registered 40-bit asset ID")
    suspected_url: Optional[str] = Field(None, max_length=512)
    suspected_country: Optional[str] = Field(None, max_length=64)
    match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    watermark_status: Optional[str] = Field(None, max_length=64)
    evidence_notes: Optional[str] = None


class CaseStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: New, Potential Match, Evidence Collected, Contacted, Under Review, Resolved, Closed")
    note: Optional[str] = None


class CaseNoteRequest(BaseModel):
    note: str = Field(..., min_length=1)


class TimelineEvent(BaseModel):
    timestamp: str
    action: str
    actor: str
    details: Optional[str] = None


class CaseResponse(BaseModel):
    id: str
    case_number: str
    asset_id: int
    asset_title: str
    title: str
    suspected_image_path: Optional[str] = None
    suspected_url: Optional[str] = None
    suspected_country: Optional[str] = None
    match_score: Optional[float] = None
    watermark_status: Optional[str] = None
    status: str
    evidence_notes: Optional[str] = None
    timeline: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class CaseReportResponse(BaseModel):
    report_id: str
    generated_at: datetime
    case: CaseResponse
    registered_asset_metadata: Dict[str, Any]
    technical_evidence_summary: Dict[str, Any]
    disclaimer: str
