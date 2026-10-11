"""Automated security hardening verification tests for CreditMera Phase 3.

Covers:
1. Production secret validation (reject defaults, reject short secrets, allow valid, allow dev).
2. Image decompression-bomb and oversized image rejection before memory allocation.
3. Storage path traversal containment checks (parent traversal, sibling prefix attack, absolute paths).
4. Strict JWT header algorithm validation (HS256 enforced, alg:none rejected, unsupported rejected, malformed rejected).
"""
import io
import json
import base64
import tempfile
import shutil
from pathlib import Path
from datetime import timedelta
import pytest
import numpy as np
from PIL import Image

from app.core.config import (
    Settings,
    DEV_DEFAULT_SECRET_KEY,
    DEV_DEFAULT_WATERMARK_KEY,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
)
from watermark.transforms import (
    decode_image,
    ImageValidationError,
    MAX_IMAGE_DIMENSION,
    MIN_IMAGE_DIMENSION,
)
from storage.local import LocalStorageProvider


# ==============================================================================
# 1. Production Secret Validation Tests
# ==============================================================================
class TestProductionSecretValidation:

    def test_production_with_default_secret_key_fails(self):
        """Production environment must strictly reject default development SECRET_KEY."""
        with pytest.raises(ValueError, match="Production environment requires a unique, secure SECRET_KEY"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY=DEV_DEFAULT_SECRET_KEY,
                WATERMARK_SECRET_KEY="a_secure_custom_watermark_key_that_is_long_enough",
            )

    def test_production_with_default_watermark_key_fails(self):
        """Production environment must strictly reject default development WATERMARK_SECRET_KEY."""
        with pytest.raises(ValueError, match="Production environment requires a unique, secure WATERMARK_SECRET_KEY"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="a_secure_custom_jwt_secret_that_is_long_enough_32",
                WATERMARK_SECRET_KEY=DEV_DEFAULT_WATERMARK_KEY,
            )

    def test_production_with_short_secret_key_fails(self):
        """Production environment must reject SECRET_KEY shorter than 32 characters."""
        with pytest.raises(ValueError, match="SECRET_KEY to be at least 32 characters long"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="too_short_key",
                WATERMARK_SECRET_KEY="a_secure_custom_watermark_key_that_is_long_enough",
            )

    def test_production_with_short_watermark_key_fails(self):
        """Production environment must reject WATERMARK_SECRET_KEY shorter than 32 characters."""
        with pytest.raises(ValueError, match="WATERMARK_SECRET_KEY to be at least 32 characters long"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="a_secure_custom_jwt_secret_that_is_long_enough_32",
                WATERMARK_SECRET_KEY="short_wm_key",
            )

    def test_production_with_valid_secrets_passes(self):
        """Production environment must accept unique, sufficiently long secrets."""
        prod_settings = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="prod_custom_jwt_secret_key_for_testing_purposes_min32",
            WATERMARK_SECRET_KEY="prod_custom_watermark_master_key_for_testing_purposes_32",
        )
        assert prod_settings.ENVIRONMENT == "production"
        assert len(prod_settings.SECRET_KEY) >= 32
        assert len(prod_settings.WATERMARK_SECRET_KEY) >= 32

    def test_development_configuration_continues_working(self):
        """Development and test environments must continue working with default configurations."""
        dev_settings = Settings(_env_file=None, ENVIRONMENT="development")
        assert dev_settings.ENVIRONMENT == "development"
        assert dev_settings.SECRET_KEY == DEV_DEFAULT_SECRET_KEY


# ==============================================================================
# 2. Image Decompression-Bomb and Validation Tests
# ==============================================================================
class TestImageDecompressionBombProtection:

    def test_valid_image_decoding(self):
        """Verify normal compliant image decodes to (H, W, 3) uint8 array."""
        img = Image.new("RGB", (128, 128), color=(120, 180, 240))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        arr = decode_image(buf.getvalue())
        assert arr.shape == (128, 128, 3)
        assert arr.dtype == np.uint8

    def test_oversized_image_rejected_without_load(self):
        """Verify images exceeding MAX_IMAGE_DIMENSION are rejected with ImageValidationError."""
        oversized = Image.new("RGB", (MAX_IMAGE_DIMENSION + 10, 128), color=(255, 0, 0))
        buf = io.BytesIO()
        oversized.save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        with pytest.raises(ImageValidationError, match="exceed maximum allowed limit"):
            decode_image(raw_bytes)

    def test_sub_minimum_image_rejected(self):
        """Verify images below MIN_IMAGE_DIMENSION are rejected with ImageValidationError."""
        small = Image.new("RGB", (MIN_IMAGE_DIMENSION - 10, MIN_IMAGE_DIMENSION - 10), color=(0, 255, 0))
        buf = io.BytesIO()
        small.save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        with pytest.raises(ImageValidationError, match="too small"):
            decode_image(raw_bytes)

    def test_empty_image_rejected(self):
        """Verify empty byte payload is rejected immediately."""
        with pytest.raises(ImageValidationError, match="Empty image byte payload"):
            decode_image(b"")

    def test_malformed_image_rejected(self):
        """Verify non-image corrupted bytes raise ImageValidationError."""
        with pytest.raises(ImageValidationError, match="Failed to decode image"):
            decode_image(b"CORRUPTED_NON_IMAGE_DATA_STREAM")

    def test_grayscale_and_rgba_compatibility(self):
        """Verify grayscale and RGBA inputs are properly normalized to 3-channel RGB."""
        # Grayscale
        gray = Image.new("L", (100, 100), color=128)
        buf_gray = io.BytesIO()
        gray.save(buf_gray, format="PNG")
        arr_gray = decode_image(buf_gray.getvalue())
        assert arr_gray.shape == (100, 100, 3)

        # RGBA
        rgba = Image.new("RGBA", (100, 100), color=(50, 100, 150, 200))
        buf_rgba = io.BytesIO()
        rgba.save(buf_rgba, format="PNG")
        arr_rgba = decode_image(buf_rgba.getvalue())
        assert arr_rgba.shape == (100, 100, 3)


# ==============================================================================
# 3. Storage Path Traversal Protection Tests
# ==============================================================================
class TestStoragePathTraversalProtection:

    @pytest.fixture
    def local_storage(self):
        temp_dir = Path(tempfile.mkdtemp(prefix="creditmera_sec_storage_"))
        storage = LocalStorageProvider(base_dir=temp_dir)
        yield storage, temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_valid_original_and_watermarked_image_paths(self, local_storage):
        storage, temp_dir = local_storage
        orig_path = "originals/12345_abc123.png"
        wm_path = "watermarked/12345_def456.png"

        saved_orig = storage.save(b"original_bytes", orig_path)
        saved_wm = storage.save(b"watermarked_bytes", wm_path)

        assert storage.exists(saved_orig)
        assert storage.exists(saved_wm)
        assert storage.read(saved_orig) == b"original_bytes"
        assert storage.read(saved_wm) == b"watermarked_bytes"

    def test_parent_directory_traversal_rejected(self, local_storage):
        storage, _ = local_storage
        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.save(b"malicious", "../outside_file.png")

        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.read("../../etc/passwd")

    def test_sibling_directory_prefix_attack_rejected(self, local_storage):
        """Ensure paths targeting a sibling directory with a common prefix are rejected."""
        storage, temp_dir = local_storage
        # Sibling directory attempt: e.g. ../creditmera_sec_storage_evil/file.png
        sibling_rel = f"../{temp_dir.name}_evil/payload.bin"
        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.save(b"sibling_evil", sibling_rel)

    def test_absolute_external_path_rejected(self, local_storage):
        storage, _ = local_storage
        # Windows / POSIX absolute paths
        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.save(b"evil", "C:/Windows/System32/evil.dll")

        with pytest.raises(ValueError, match="Path traversal detected"):
            storage.read("/etc/shadow")


# ==============================================================================
# 4. Strict JWT Header Algorithm Validation Tests
# ==============================================================================
class TestJWTHeaderAlgorithmValidation:

    def test_valid_hs256_token_decodes_successfully(self):
        """Tokens created by CreditMera use HS256 and decode cleanly."""
        token = create_access_token({"sub": "user-uuid-1", "email": "test@test.com"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-uuid-1"
        assert payload["email"] == "test@test.com"

    def test_expired_token_rejected(self):
        """Tokens past expiration timestamp must be rejected."""
        token = create_access_token(
            {"sub": "user-uuid-2", "email": "test@test.com"},
            expires_delta=timedelta(seconds=-60)
        )
        with pytest.raises(ValueError, match="Token has expired"):
            decode_access_token(token)

    def test_tampered_payload_rejected(self):
        """Tokens with modified payload bytes fail signature verification."""
        token = create_access_token({"sub": "user-uuid-3", "email": "test@test.com"})
        parts = token.split(".")
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "admin-uuid", "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        with pytest.raises(ValueError, match="Token signature verification failed"):
            decode_access_token(tampered_token)

    def test_alg_none_token_strictly_rejected(self):
        """Tokens attempting 'alg: none' bypass must be rejected with algorithm error."""
        hdr_none = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).decode().rstrip("=")
        pay = base64.urlsafe_b64encode(
            json.dumps({"sub": "user-attacker", "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        none_token = f"{hdr_none}.{pay}."

        with pytest.raises(ValueError, match="Unsupported or rejected JWT algorithm 'none'"):
            decode_access_token(none_token)

    def test_unsupported_algorithm_rejected(self):
        """Tokens with algorithms other than HS256 (e.g. RS256, ES256) must be rejected."""
        hdr_rs256 = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
        ).decode().rstrip("=")
        pay = base64.urlsafe_b64encode(
            json.dumps({"sub": "user-attacker", "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        rs256_token = f"{hdr_rs256}.{pay}.fakesignature"

        with pytest.raises(ValueError, match="Unsupported or rejected JWT algorithm 'RS256'"):
            decode_access_token(rs256_token)

    def test_malformed_jwt_header_rejected(self):
        """Tokens with corrupted or non-JSON headers must be rejected cleanly."""
        bad_hdr_token = "invalid_base64_header.eyJzdWIiOiIxIn0.sig"
        with pytest.raises(ValueError, match="Invalid JWT header"):
            decode_access_token(bad_hdr_token)

    def test_invalid_token_type_rejected(self):
        """Tokens with invalid type claim must be rejected."""
        hdr_bad_typ = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "NOT_JWT"}).encode()
        ).decode().rstrip("=")
        pay = base64.urlsafe_b64encode(
            json.dumps({"sub": "user-uuid", "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        bad_typ_token = f"{hdr_bad_typ}.{pay}.fakesig"

        with pytest.raises(ValueError, match="Invalid token type 'NOT_JWT'"):
            decode_access_token(bad_typ_token)
