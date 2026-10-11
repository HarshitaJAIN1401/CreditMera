"""Registration receipt schemas and verification structures.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ReceiptPayload(BaseModel):
    receipt_number: str
    asset_id: int
    owner_id: str
    owner_email: str
    owner_name: str
    original_file_sha256: str
    watermarked_file_sha256: str
    algorithm: str
    algorithm_version: str
    payload_version: int
    alpha: float
    image_width: int
    image_height: int
    registered_at: str
    ownership_declaration: str
    disclaimer: str


class ReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    receipt_number: str
    asset_id: int
    issued_at: datetime
    issuer: str
    original_file_sha256: str
    watermarked_file_sha256: str
    algorithm_version: str
    payload_version: int
    owner_declaration_summary: str
    legal_disclaimer: str
    receipt_signature: str
    receipt_payload: Dict[str, Any]


class ReceiptVerifyRequest(BaseModel):
    receipt_payload: Dict[str, Any] = Field(..., description="Canonical receipt dictionary")
    receipt_signature: str = Field(..., description="HMAC-SHA256 signature to verify")


class ReceiptVerifyResponse(BaseModel):
    is_authentic: bool = Field(..., description="True if signature is valid and untampered")
    signature_valid: bool = Field(..., description="Cryptographic signature verification status")
    database_match: bool = Field(..., description="Whether receipt matches authoritative database record")
    status: str = Field(..., description="Detailed status string (e.g. AUTHENTIC, SIGNATURE_MISMATCH, RECORD_NOT_FOUND)")
    message: str = Field(..., description="Human-readable verification narrative")
    asset_id: Optional[int] = None
    issued_at: Optional[str] = None
