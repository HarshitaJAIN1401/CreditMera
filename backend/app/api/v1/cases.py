"""API routes for Global Case Management (International image misuse tracking)."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Path
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.asset import RegisteredAsset
from app.models.case import GlobalCase
from app.schemas.case import (
    CaseResponse,
    CaseStatusUpdateRequest,
    CaseNoteRequest,
    CaseReportResponse,
)
from storage import get_storage

router = APIRouter(prefix="/cases", tags=["Global Case Management"])

VALID_STATUSES = {
    "New",
    "Potential Match",
    "Evidence Collected",
    "Contacted",
    "Under Review",
    "Resolved",
    "Closed",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open a new international image misuse case",
)
async def create_case(
    title: str = Form(..., min_length=2, max_length=255),
    asset_id: int = Form(..., ge=1, le=1099511627775),
    suspected_url: Optional[str] = Form(None),
    suspected_country: Optional[str] = Form(None),
    match_score: Optional[float] = Form(None),
    watermark_status: Optional[str] = Form(None),
    evidence_notes: Optional[str] = Form(None),
    suspected_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new potential misuse case linked to an owned asset."""
    asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registered asset with ID {asset_id} not found.",
        )
    if asset.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only file cases for your own registered assets.",
        )

    case_uuid = str(uuid.uuid4())
    case_num = f"CASE-{datetime.now(timezone.utc).year}-{case_uuid[:8].upper()}"

    suspected_path = None
    if suspected_file:
        file_bytes = await suspected_file.read()
        storage = get_storage()
        suspected_path = f"cases/{case_num}_suspected.png"
        storage.save(file_bytes, suspected_path)

    initial_timeline = [
        {
            "timestamp": utc_now().isoformat(),
            "action": "CASE_CREATED",
            "actor": current_user.email,
            "details": f"Case opened with initial status 'New'. Suspected country: {suspected_country or 'Unspecified'}.",
        }
    ]

    new_case = GlobalCase(
        id=case_uuid,
        case_number=case_num,
        reporter_id=current_user.id,
        asset_id=asset.id,
        title=title,
        suspected_image_path=suspected_path,
        suspected_url=suspected_url,
        suspected_country=suspected_country,
        match_score=match_score,
        watermark_status=watermark_status,
        status="New",
        evidence_notes=evidence_notes,
        timeline_json=initial_timeline,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return CaseResponse(
        id=new_case.id,
        case_number=new_case.case_number,
        asset_id=asset.asset_id,
        asset_title=asset.title,
        title=new_case.title,
        suspected_image_path=new_case.suspected_image_path,
        suspected_url=new_case.suspected_url,
        suspected_country=new_case.suspected_country,
        match_score=new_case.match_score,
        watermark_status=new_case.watermark_status,
        status=new_case.status,
        evidence_notes=new_case.evidence_notes,
        timeline=new_case.timeline_json or [],
        created_at=new_case.created_at,
        updated_at=new_case.updated_at,
    )


@router.get(
    "",
    response_model=List[CaseResponse],
    summary="List all international misuse cases for the current user",
)
def list_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    country_filter: Optional[str] = Query(None, alias="country"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all misuse cases created by the user with filtering."""
    q = db.query(GlobalCase).filter(GlobalCase.reporter_id == current_user.id)
    if status_filter:
        q = q.filter(GlobalCase.status == status_filter)
    if country_filter:
        q = q.filter(GlobalCase.suspected_country == country_filter)

    cases = q.order_by(GlobalCase.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for c in cases:
        asset_obj = db.query(RegisteredAsset).filter(RegisteredAsset.id == c.asset_id).first()
        results.append(
            CaseResponse(
                id=c.id,
                case_number=c.case_number,
                asset_id=asset_obj.asset_id if asset_obj else 0,
                asset_title=asset_obj.title if asset_obj else "Unknown Asset",
                title=c.title,
                suspected_image_path=c.suspected_image_path,
                suspected_url=c.suspected_url,
                suspected_country=c.suspected_country,
                match_score=c.match_score,
                watermark_status=c.watermark_status,
                status=c.status,
                evidence_notes=c.evidence_notes,
                timeline=c.timeline_json or [],
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return results


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Get case details by ID",
)
def get_case(
    case_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details of a specific case."""
    c = db.query(GlobalCase).filter(GlobalCase.id == case_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if c.reporter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    asset_obj = db.query(RegisteredAsset).filter(RegisteredAsset.id == c.asset_id).first()
    return CaseResponse(
        id=c.id,
        case_number=c.case_number,
        asset_id=asset_obj.asset_id if asset_obj else 0,
        asset_title=asset_obj.title if asset_obj else "Unknown Asset",
        title=c.title,
        suspected_image_path=c.suspected_image_path,
        suspected_url=c.suspected_url,
        suspected_country=c.suspected_country,
        match_score=c.match_score,
        watermark_status=c.watermark_status,
        status=c.status,
        evidence_notes=c.evidence_notes,
        timeline=c.timeline_json or [],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.patch(
    "/{case_id}/status",
    response_model=CaseResponse,
    summary="Update case status",
)
def update_case_status(
    req: CaseStatusUpdateRequest,
    case_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Transition a case's lifecycle status."""
    if req.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid status '{req.status}'. Must be one of: {sorted(list(VALID_STATUSES))}",
        )

    c = db.query(GlobalCase).filter(GlobalCase.id == case_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if c.reporter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    old_status = c.status
    c.status = req.status
    c.updated_at = utc_now()

    timeline = list(c.timeline_json or [])
    timeline.append(
        {
            "timestamp": utc_now().isoformat(),
            "action": "STATUS_CHANGED",
            "actor": current_user.email,
            "details": f"Status updated from '{old_status}' to '{req.status}'. Note: {req.note or 'No additional note'}",
        }
    )
    c.timeline_json = timeline

    db.commit()
    db.refresh(c)

    asset_obj = db.query(RegisteredAsset).filter(RegisteredAsset.id == c.asset_id).first()
    return CaseResponse(
        id=c.id,
        case_number=c.case_number,
        asset_id=asset_obj.asset_id if asset_obj else 0,
        asset_title=asset_obj.title if asset_obj else "Unknown Asset",
        title=c.title,
        suspected_image_path=c.suspected_image_path,
        suspected_url=c.suspected_url,
        suspected_country=c.suspected_country,
        match_score=c.match_score,
        watermark_status=c.watermark_status,
        status=c.status,
        evidence_notes=c.evidence_notes,
        timeline=c.timeline_json or [],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.post(
    "/{case_id}/notes",
    response_model=CaseResponse,
    summary="Add note or communication record to case timeline",
)
def add_case_note(
    req: CaseNoteRequest,
    case_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a note or communication log to the case."""
    c = db.query(GlobalCase).filter(GlobalCase.id == case_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if c.reporter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    timeline = list(c.timeline_json or [])
    timeline.append(
        {
            "timestamp": utc_now().isoformat(),
            "action": "NOTE_ADDED",
            "actor": current_user.email,
            "details": req.note,
        }
    )
    c.timeline_json = timeline
    c.updated_at = utc_now()

    db.commit()
    db.refresh(c)

    asset_obj = db.query(RegisteredAsset).filter(RegisteredAsset.id == c.asset_id).first()
    return CaseResponse(
        id=c.id,
        case_number=c.case_number,
        asset_id=asset_obj.asset_id if asset_obj else 0,
        asset_title=asset_obj.title if asset_obj else "Unknown Asset",
        title=c.title,
        suspected_image_path=c.suspected_image_path,
        suspected_url=c.suspected_url,
        suspected_country=c.suspected_country,
        match_score=c.match_score,
        watermark_status=c.watermark_status,
        status=c.status,
        evidence_notes=c.evidence_notes,
        timeline=c.timeline_json or [],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get(
    "/{case_id}/report",
    response_model=CaseReportResponse,
    summary="Generate and download technical evidence report",
)
def generate_evidence_report(
    case_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate structured technical evidence dossier for a case."""
    c = db.query(GlobalCase).filter(GlobalCase.id == case_id).first()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if c.reporter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    asset = db.query(RegisteredAsset).filter(RegisteredAsset.id == c.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registered asset missing.")

    case_resp = CaseResponse(
        id=c.id,
        case_number=c.case_number,
        asset_id=asset.asset_id,
        asset_title=asset.title,
        title=c.title,
        suspected_image_path=c.suspected_image_path,
        suspected_url=c.suspected_url,
        suspected_country=c.suspected_country,
        match_score=c.match_score,
        watermark_status=c.watermark_status,
        status=c.status,
        evidence_notes=c.evidence_notes,
        timeline=c.timeline_json or [],
        created_at=c.created_at,
        updated_at=c.updated_at,
    )

    asset_meta = {
        "asset_id": asset.asset_id,
        "title": asset.title,
        "original_filename": asset.original_filename,
        "registered_at": asset.registered_at.isoformat(),
        "original_sha256": asset.original_file_hash,
        "watermarked_sha256": asset.watermarked_file_hash,
        "dimensions": f"{asset.image_width}x{asset.image_height}",
        "algorithm": asset.algorithm,
        "algorithm_version": asset.algorithm_version,
        "category": getattr(asset, "category", "Other") or "Other",
        "country": getattr(asset, "country", "International") or "International",
        "license_type": getattr(asset, "license_type", "All Rights Reserved") or "All Rights Reserved",
        "owner_name": current_user.full_name,
        "owner_email": current_user.email,
        "receipt_number": asset.receipt.receipt_number if asset.receipt else "None",
    }

    evidence_summary = {
        "suspected_url": c.suspected_url,
        "suspected_country": c.suspected_country,
        "watermark_verification_outcome": c.watermark_status or "NOT_VERIFIED",
        "visual_similarity_score": c.match_score,
        "similarity_percentage": f"{round(c.match_score * 100.0, 1)}%" if c.match_score is not None else "N/A",
        "case_lifecycle_status": c.status,
    }

    return CaseReportResponse(
        report_id=f"REP-{c.case_number}-{uuid.uuid4().hex[:6].upper()}",
        generated_at=utc_now(),
        case=case_resp,
        registered_asset_metadata=asset_meta,
        technical_evidence_summary=evidence_summary,
        disclaimer=(
            "CONFIDENTIAL TECHNICAL EVIDENCE DOSSIER. Generated by CreditMera International Verification Platform. "
            "This report documents technical forensic observations (cryptographic watermark payload detection and "
            "perceptual similarity scoring) and immutable database timestamps. It constitutes technical documentation "
            "and does not represent a legal determination of copyright infringement."
        ),
    )
