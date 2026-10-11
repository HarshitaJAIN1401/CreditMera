"""API routes for visual similarity analysis and vault lookup."""
import ipaddress
import socket
import urllib.parse
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_optional_current_user
from app.models.user import User
from app.models.asset import RegisteredAsset
from app.schemas.similarity import (
    SimilarityCompareResponse,
    SimilaritySearchResponse,
    SimilaritySearchMatch,
)
from watermark.transforms import decode_image
from watermark.similarity import (
    compare_images,
    compute_phash,
    hamming_distance,
    hash_similarity,
    evaluate_similarity_tier,
)

router = APIRouter(prefix="/similarity", tags=["Visual Similarity Detection"])


def is_safe_external_url(url_str: str) -> bool:
    """Validate URL against SSRF by checking for public non-loopback IP addresses."""
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve IP addresses
        ip_list = socket.getaddrinfo(hostname, None)
        for entry in ip_list:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                return False
        return True
    except Exception:
        return False


async def fetch_image_from_url(url_str: str) -> bytes:
    """Safely fetch image from verified external URL with size and timeout guards."""
    if not is_safe_external_url(url_str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided URL is invalid or targets an internal/restricted IP address.",
        )

    headers = {"User-Agent": "CreditMera-Verification-Bot/1.0"}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url_str, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch image from URL: HTTP status {resp.status_code}",
                )
            content_length = len(resp.content)
            if content_length > 33554432:  # 32MB limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Remote image exceeds maximum permitted size of 32MB.",
                )
            return resp.content
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not connect to remote image host: {str(e)}",
        )


@router.post(
    "/compare",
    response_model=SimilarityCompareResponse,
    summary="Compare two images for visual and perceptual similarity",
)
async def compare_two_images(
    reference_file: Optional[UploadFile] = File(None, description="Reference original image file"),
    suspected_file: Optional[UploadFile] = File(None, description="Suspected image file"),
    suspected_url: Optional[str] = Form(None, description="Optional public URL to suspected image"),
):
    """Perform independent visual similarity analysis (pHash, dHash, SSIM) between two images.

    Independent of watermark presence or payload extraction.
    """
    if not reference_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference image file is required.",
        )

    ref_bytes = await reference_file.read()
    try:
        ref_arr = decode_image(ref_bytes)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Reference image invalid: {e}")

    if suspected_file:
        susp_bytes = await suspected_file.read()
    elif suspected_url:
        susp_bytes = await fetch_image_from_url(suspected_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either suspected_file or suspected_url must be provided.",
        )

    try:
        susp_arr = decode_image(susp_bytes)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Suspected image invalid: {e}")

    res = compare_images(ref_arr, susp_arr)
    return SimilarityCompareResponse(**res)


@router.post(
    "/search",
    response_model=SimilaritySearchResponse,
    summary="Search registered assets for visual similarity against a suspected image",
)
async def search_vault_similarity(
    suspected_file: Optional[UploadFile] = File(None, description="Suspected image file"),
    suspected_url: Optional[str] = Form(None, description="Optional public URL to suspected image"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Calculate perceptual hash of suspected image and search against registered assets."""
    if suspected_file:
        susp_bytes = await suspected_file.read()
    elif suspected_url:
        susp_bytes = await fetch_image_from_url(suspected_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either suspected_file or suspected_url must be provided.",
        )

    try:
        susp_arr = decode_image(susp_bytes)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Suspected image invalid: {e}")

    query_phash = compute_phash(susp_arr)

    # Query registered assets (user's assets if logged in, or all assets if public lookup)
    query = db.query(RegisteredAsset)
    if current_user:
        query = query.filter(RegisteredAsset.owner_id == current_user.id)
    assets = query.all()

    matches = []
    for a in assets:
        if a.perceptual_hash:
            target_phash = a.perceptual_hash
        else:
            # Fallback for older assets before migration
            target_phash = query_phash

        dist = hamming_distance(query_phash, target_phash)
        score = hash_similarity(query_phash, target_phash)
        tier, _ = evaluate_similarity_tier(score, dist)

        matches.append(
            SimilaritySearchMatch(
                asset_id=a.asset_id,
                title=a.title,
                category=getattr(a, "category", "Other") or "Other",
                country=getattr(a, "country", "International") or "International",
                hamming_distance=dist,
                similarity_score=round(score, 4),
                similarity_percentage=round(score * 100.0, 1),
                similarity_tier=tier,
            )
        )

    # Sort descending by similarity score
    matches.sort(key=lambda m: m.similarity_score, reverse=True)
    top_match = matches[0] if matches else None

    return SimilaritySearchResponse(
        query_phash=query_phash,
        total_registered_evaluated=len(assets),
        matches=matches[:20],  # Return top 20 candidates
        top_match=top_match,
        legal_disclaimer=(
            "Visual similarity lookup estimates perceptual correlation against registered images. "
            "It does not constitute conclusive evidence of copyright infringement or authorized licensing."
        ),
    )
