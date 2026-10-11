"""Asset registration schemas and API response models.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.receipt import ReceiptResponse


class AssetRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: int = Field(..., description="Unique 40-bit numerical asset ID embedded in watermark")
    registered_asset_id: str = Field(..., description="Internal UUID of registered asset")
    title: str = Field(..., description="User title for asset")
    original_filename: str = Field(..., description="Original uploaded filename")
    original_file_hash: str = Field(..., description="SHA-256 hash of original image")
    watermarked_file_hash: str = Field(..., description="SHA-256 hash of watermarked image")
    image_width: int
    image_height: int
    algorithm: str
    algorithm_version: str
    payload_version: int
    alpha: float
    registered_at: datetime
    receipt: ReceiptResponse
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Embedding quality metrics (PSNR, SSIM, NC, BER)")

    # International passport fields
    category: Optional[str] = "Other"
    country: Optional[str] = "International"
    license_type: Optional[str] = "All Rights Reserved"
    attribution_text: Optional[str] = None
    perceptual_hash: Optional[str] = None


class AssetSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: int
    registered_asset_id: str
    title: str
    original_filename: str
    original_file_hash: str
    watermarked_file_hash: str
    image_width: int
    image_height: int
    algorithm: str
    registered_at: datetime
    status: str

    # International passport fields
    category: Optional[str] = "Other"
    country: Optional[str] = "International"
    license_type: Optional[str] = "All Rights Reserved"
    attribution_text: Optional[str] = None
    perceptual_hash: Optional[str] = None


class AssetDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: int
    registered_asset_id: str
    owner_id: str
    owner_name: Optional[str] = None
    title: str
    original_filename: str
    original_file_hash: str
    original_file_size: int
    original_mime_type: str
    image_width: int
    image_height: int
    watermarked_file_hash: str
    watermarked_file_size: int
    storage_path_watermarked: str
    algorithm: str
    algorithm_version: str
    payload_version: int
    alpha: float
    status: str
    ownership_declaration: str
    ownership_declared_at: datetime
    registered_at: datetime
    metrics: Optional[Dict[str, Any]] = None
    receipt: Optional[ReceiptResponse] = None

    # International passport fields
    category: Optional[str] = "Other"
    country: Optional[str] = "International"
    license_type: Optional[str] = "All Rights Reserved"
    attribution_text: Optional[str] = None
    perceptual_hash: Optional[str] = None
