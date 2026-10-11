"""Cryptographic and security utilities for CreditMera.

Includes:
- PBKDF2-HMAC-SHA256 password hashing and constant-time verification.
- HMAC-signed Bearer token issuance and validation.
- Canonical JSON serialization and HMAC-SHA256 receipt signing.
- Cryptographically secure 40-bit asset ID generation and bounds checking.
- Cryptographic SHA-256 data hashing.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from app.core.config import get_settings

# Upper bound for 40-bit asset IDs (2^40 - 1 = 1,099,511,627,775)
MAX_ASSET_ID = (1 << 40) - 1
MIN_ASSET_ID = 1

PBKDF2_ITERATIONS = 100_000


def compute_sha256(data: bytes) -> str:
    """Compute standard lowercase hex SHA-256 digest over bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 rounds and random salt.
    
    Returns string format: pbkdf2_sha256${iterations}${salt_hex}${hash_hex}
    """
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${pw_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])

        computed = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations
        )
        return hmac.compare_digest(computed, expected_hash)
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed compact bearer token (Header.Payload.Signature)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = data.copy()
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_hex(16),
    })

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8").rstrip("=")

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(to_encode, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8").rstrip("=")

    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify signature and expiration of a bearer token.
    
    Raises ValueError on invalid token, signature mismatch, or expiration.
    """
    settings = get_settings()
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format: must be header.payload.signature")

    header_b64, payload_b64, sig_b64 = parts

    # 1. Decode and strictly validate JWT header
    rem_h = len(header_b64) % 4
    padded_header = header_b64 + ("=" * (4 - rem_h) if rem_h else "")
    try:
        header_bytes = base64.urlsafe_b64decode(padded_header.encode("utf-8"))
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError("Invalid JWT header encoding or structure") from e

    if not isinstance(header, dict):
        raise ValueError("JWT header must be a valid JSON object")

    alg = header.get("alg")
    if alg != "HS256":
        raise ValueError(f"Unsupported or rejected JWT algorithm '{alg}'. Only 'HS256' is permitted.")

    typ = header.get("typ")
    if typ is not None and typ != "JWT":
        raise ValueError(f"Invalid token type '{typ}'. Expected 'JWT'.")

    # 2. Reconstruct signature and verify
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()

    # Pad base64 if needed
    rem = len(sig_b64) % 4
    padded_sig = sig_b64 + ("=" * (4 - rem) if rem else "")
    try:
        provided_sig = base64.urlsafe_b64decode(padded_sig.encode("utf-8"))
    except Exception as e:
        raise ValueError("Invalid token signature encoding") from e

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise ValueError("Token signature verification failed")

    # 3. Decode payload
    rem_p = len(payload_b64) % 4
    padded_payload = payload_b64 + ("=" * (4 - rem_p) if rem_p else "")
    payload_bytes = base64.urlsafe_b64decode(padded_payload.encode("utf-8"))
    payload = json.loads(payload_bytes.decode("utf-8"))

    # 4. Check expiration
    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Token missing expiration timestamp")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > exp:
        raise ValueError("Token has expired")

    return payload


def canonicalize_json(data: Dict[str, Any]) -> bytes:
    """Return canonical, deterministically sorted JSON bytes for cryptographic signing."""
    # Exclude receipt_signature or signature if present
    clean_data = {k: v for k, v in data.items() if k not in ("receipt_signature", "signature")}
    return json.dumps(clean_data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_receipt(receipt_payload: Dict[str, Any], secret_key: str) -> str:
    """Compute HMAC-SHA256 hex signature over canonical receipt JSON payload."""
    canonical = canonicalize_json(receipt_payload)
    key_bytes = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key
    return hmac.new(key_bytes, canonical, hashlib.sha256).hexdigest()


def verify_receipt_signature(
    receipt_payload: Dict[str, Any],
    provided_signature: str,
    secret_key: str
) -> bool:
    """Verify that a receipt payload has not been tampered with since issuance."""
    if not provided_signature or not isinstance(provided_signature, str):
        return False
    computed_sig = sign_receipt(receipt_payload, secret_key)
    return hmac.compare_digest(computed_sig, provided_signature)


def generate_secure_asset_id() -> int:
    """Generate a collision-safe 40-bit unsigned integer asset ID [1, 2^40 - 1].
    
    Fits strictly inside the 5-byte payload allocated by the watermark engine.
    """
    return secrets.randbelow(MAX_ASSET_ID) + 1


def is_valid_asset_id(asset_id: int) -> bool:
    """Check whether an asset ID satisfies the 40-bit integer range."""
    return isinstance(asset_id, int) and (MIN_ASSET_ID <= asset_id <= MAX_ASSET_ID)
