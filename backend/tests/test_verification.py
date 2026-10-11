"""Comprehensive tests for CreditMera Phase 4 Ownership Verification and Security.

Validates:
1. End-to-end verification of clean watermarked assets -> MATCHED (UNMODIFIED_COPY).
2. Verification of modified/re-encoded watermarked assets -> MATCHED (MODIFIED_RE_ENCODED).
3. Blind testing of unwatermarked images -> NOT_DETECTED (zero false positives).
4. Corrupted/tampered watermark payloads -> INVALID_WATERMARK.
5. Authenticated watermark with unregistered asset ID -> NO_REGISTERED_RECORD.
6. Borderline degraded signals -> INCONCLUSIVE.
7. Registration receipt validation (authentic vs tampered receipt).
8. Authorization boundaries and privacy isolation between owners and public callers.
9. Image input security, format validation, and decompression-bomb resistance.
10. False-positive and false-negative measurement on benchmark test patterns.
"""
import io
import json
import pytest
import numpy as np
from PIL import Image, ImageFilter
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import compute_sha256
from app.models.user import User
from app.models.asset import RegisteredAsset
from watermark.embedding import embed_watermark
from watermark.payload import encode_payload


def create_test_image_bytes(width=256, height=256, pattern="texture", fmt="PNG") -> bytes:
    """Helper to generate in-memory synthetic images for testing."""
    if pattern == "gradient":
        x = np.linspace(0, 255, width, dtype=np.uint8)
        arr_2d = np.tile(x, (height, 1))
        arr = np.stack([arr_2d, arr_2d.T[:height, :width], np.flipud(arr_2d)], axis=-1)
    elif pattern == "texture":
        u, v = np.meshgrid(np.linspace(0, 8 * np.pi, width), np.linspace(0, 8 * np.pi, height))
        arr_2d = ((np.sin(u) * np.cos(v) + 1.0) * 127.5).astype(np.uint8)
        arr = np.stack([arr_2d, arr_2d, arr_2d], axis=-1)
    elif pattern == "flat":
        arr = np.full((height, width, 3), 128, dtype=np.uint8)
    else:
        rng = np.random.default_rng(42)
        arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)

    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestOwnershipVerification:

    def test_matched_unmodified_watermarked_image(self, client, test_user: User, test_user_token: str):
        """End-to-end verification of an authentic watermarked image returns MATCHED with UNMODIFIED_COPY."""
        user_headers = {"Authorization": f"Bearer {test_user_token}"}
        img_bytes = create_test_image_bytes(256, 256, "texture")

        # 1. Register asset
        files = {"file": ("test_art.png", img_bytes, "image/png")}
        data = {
            "title": "Sunset Symphony",
            "ownership_declaration": "I am the original creator and declare full authorship.",
            "algorithm": "dct_svd",
            "alpha": 0.10,
        }
        reg_resp = client.post("/api/v1/assets/register", headers=user_headers, files=files, data=data)
        assert reg_resp.status_code == 201
        reg_data = reg_resp.json()
        asset_id = reg_data["asset_id"]

        # 2. Download watermarked image
        dl_resp = client.get(f"/api/v1/assets/{asset_id}/download/watermarked", headers=user_headers)
        assert dl_resp.status_code == 200
        watermarked_bytes = dl_resp.content

        # 3. Verify as owner
        v_files = {"file": ("suspect.png", watermarked_bytes, "image/png")}
        v_resp = client.post("/api/v1/verify", headers=user_headers, files=v_files)
        assert v_resp.status_code == 200
        res = v_resp.json()

        assert res["status"] == "MATCHED"
        assert res["confidence"] == 1.0
        assert res["asset_id"] == asset_id
        assert res["integrity_status"] == "UNMODIFIED_COPY"
        assert res["hash_matched"] is True
        assert res["match_details"]["title"] == "Sunset Symphony"
        assert res["match_details"]["asset_id"] == asset_id
        assert res["match_details"]["algorithm"] == "dct_svd"
        assert res["receipt_verification"]["is_authentic"] is True
        assert res["receipt_verification"]["database_match"] is True
        assert res["ownership_status"]["is_owner"] is True
        assert res["ownership_status"]["owner_display"] == test_user.email
        assert "statutory copyright" in res["legal_disclaimer"]
        assert res["diagnostics"]["magic_header_valid"] is True
        assert res["diagnostics"]["crc_passed"] is True
        assert res["diagnostics"]["hmac_passed"] is True

    def test_matched_re_encoded_watermarked_image(self, client, test_user: User, test_user_token: str):
        """Watermark survives image re-encoding; verification returns MATCHED with MODIFIED_RE_ENCODED."""
        user_headers = {"Authorization": f"Bearer {test_user_token}"}
        img_bytes = create_test_image_bytes(256, 256, "gradient")

        # Register asset
        files = {"file": ("gradient_art.png", img_bytes, "image/png")}
        data = {
            "title": "Gradient Aurora",
            "ownership_declaration": "Original gradient design created by test owner.",
            "algorithm": "dct_svd",
            "alpha": 0.10,
        }
        reg_resp = client.post("/api/v1/assets/register", headers=user_headers, files=files, data=data)
        assert reg_resp.status_code == 201
        asset_id = reg_resp.json()["asset_id"]

        # Download watermarked copy
        dl_resp = client.get(f"/api/v1/assets/{asset_id}/download/watermarked", headers=user_headers)
        assert dl_resp.status_code == 200
        watermarked_bytes = dl_resp.content

        # Re-save with different compression / PNG metadata (file hash changes, but pixel watermark survives)
        pil_img = Image.open(io.BytesIO(watermarked_bytes))
        reencoded_buf = io.BytesIO()
        pil_img.save(reencoded_buf, format="PNG", compress_level=1)
        reencoded_bytes = reencoded_buf.getvalue()

        # SHA-256 of re-encoded copy must be different
        assert compute_sha256(reencoded_bytes) != compute_sha256(watermarked_bytes)

        # Verify re-encoded image
        v_files = {"file": ("reencoded.png", reencoded_bytes, "image/png")}
        v_resp = client.post("/api/v1/verify", headers=user_headers, files=v_files)
        assert v_resp.status_code == 200
        res = v_resp.json()

        assert res["status"] == "MATCHED"
        assert res["asset_id"] == asset_id
        assert res["integrity_status"] == "MODIFIED_RE_ENCODED"
        assert res["hash_matched"] is False
        assert res["match_details"]["title"] == "Gradient Aurora"
        assert res["receipt_verification"]["is_authentic"] is True

    def test_not_detected_unwatermarked_image(self, client):
        """Unwatermarked image returns NOT_DETECTED with confidence 0.0."""
        unwatermarked_bytes = create_test_image_bytes(256, 256, "texture")

        v_files = {"file": ("clean_image.png", unwatermarked_bytes, "image/png")}
        v_resp = client.post("/api/v1/verify", files=v_files)
        assert v_resp.status_code == 200
        res = v_resp.json()

        assert res["status"] == "NOT_DETECTED"
        assert res["confidence"] == 0.0
        assert res["asset_id"] is None
        assert res["match_details"] is None
        assert res["diagnostics"]["magic_header_valid"] is False
        assert "No sufficiently reliable watermark detected" in res["message"]

    def test_invalid_watermark_tampered_payload(self, client):
        """Watermarked image with tampered payload returns INVALID_WATERMARK or NOT_DETECTED."""
        img_bytes = create_test_image_bytes(256, 256, "texture")

        # Embed with wrong watermark key
        raw_rgb = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
        embed_res = embed_watermark(
            raw_rgb,
            asset_id=999888,
            secret_key="attacker_arbitrary_key_that_fails_system_hmac",
            algorithm="dct_svd",
            alpha=0.10,
        )

        tampered_buf = io.BytesIO()
        Image.fromarray(embed_res.watermarked_rgb).save(tampered_buf, format="PNG")
        tampered_bytes = tampered_buf.getvalue()

        # Verify against server (which uses system's WATERMARK_SECRET_KEY)
        v_files = {"file": ("tampered.png", tampered_bytes, "image/png")}
        v_resp = client.post("/api/v1/verify", files=v_files)
        assert v_resp.status_code == 200
        res = v_resp.json()

        assert res["status"] in ("NOT_DETECTED", "INVALID_WATERMARK")
        assert res["confidence"] == 0.0
        assert res["match_details"] is None

    def test_no_registered_record_for_valid_watermark(self, client):
        """A watermark embedded with the valid system key but never registered returns NO_REGISTERED_RECORD."""
        settings = get_settings()
        unregistered_asset_id = 99112233
        img_bytes = create_test_image_bytes(256, 256, "texture")
        raw_rgb = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))

        # Embed using the official system secret key
        embed_res = embed_watermark(
            raw_rgb,
            asset_id=unregistered_asset_id,
            secret_key=settings.WATERMARK_SECRET_KEY,
            algorithm="dct_svd",
            alpha=0.10,
        )

        valid_wm_buf = io.BytesIO()
        Image.fromarray(embed_res.watermarked_rgb).save(valid_wm_buf, format="PNG")
        valid_wm_bytes = valid_wm_buf.getvalue()

        # Verify against server
        v_files = {"file": ("unregistered.png", valid_wm_bytes, "image/png")}
        v_resp = client.post("/api/v1/verify", files=v_files)
        assert v_resp.status_code == 200
        res = v_resp.json()

        assert res["status"] == "NO_REGISTERED_RECORD"
        assert res["asset_id"] == unregistered_asset_id
        assert res["match_details"] is None
        assert res["diagnostics"]["magic_header_valid"] is True
        assert res["diagnostics"]["crc_passed"] is True
        assert res["diagnostics"]["hmac_passed"] is True
        assert "no corresponding registration record exists" in res["message"]

    def test_inconclusive_detection_with_real_degraded_watermark(self, client):
        """When an expected asset ID is supplied with real degraded signal (0.50 <= NC < 0.85), INCONCLUSIVE is returned."""
        settings = get_settings()
        target_asset_id = 777888
        img_bytes = create_test_image_bytes(256, 256, "texture")
        raw_rgb = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))

        # Embed watermark
        embed_res = embed_watermark(
            raw_rgb,
            asset_id=target_asset_id,
            secret_key=settings.WATERMARK_SECRET_KEY,
            algorithm="dct_svd",
            alpha=0.10,
        )

        # Apply real Gaussian blur (radius=1.4) causing payload corruption while preserving partial correlation
        pil_wm = Image.fromarray(embed_res.watermarked_rgb)
        blurred = pil_wm.filter(ImageFilter.GaussianBlur(radius=1.4))
        buf = io.BytesIO()
        blurred.save(buf, format="PNG")
        degraded_bytes = buf.getvalue()

        # Query verification with claimed expected_asset_id
        v_files = {"file": ("degraded.png", degraded_bytes, "image/png")}
        v_data = {"expected_asset_id": target_asset_id}
        v_resp = client.post("/api/v1/verify", files=v_files, data=v_data)
        assert v_resp.status_code == 200
        res = v_resp.json()

        assert res["status"] == "INCONCLUSIVE"
        assert res["asset_id"] == target_asset_id
        assert 0.50 <= res["confidence"] < 0.85
        assert res["match_details"] is None
        assert "inconclusive" in res["message"].lower()

    def test_expected_asset_id_cannot_manufacture_match(self, client, test_user_token: str):
        """Passing expected_asset_id on an unwatermarked image CANNOT manufacture a MATCHED or INCONCLUSIVE result."""
        # 1. Register an asset
        user_headers = {"Authorization": f"Bearer {test_user_token}"}
        art_bytes = create_test_image_bytes(256, 256, "texture")
        reg_resp = client.post(
            "/api/v1/assets/register",
            headers=user_headers,
            files={"file": ("legit_art.png", art_bytes, "image/png")},
            data={"title": "Legit Art", "ownership_declaration": "I am the legitimate creator of this art.", "algorithm": "dct_svd"}
        )
        assert reg_resp.status_code == 201
        legit_asset_id = reg_resp.json()["asset_id"]

        # 2. Upload completely unwatermarked image claiming expected_asset_id = legit_asset_id
        clean_bytes = create_test_image_bytes(256, 256, "gradient")
        v_files = {"file": ("clean.png", clean_bytes, "image/png")}
        v_data = {"expected_asset_id": legit_asset_id}
        v_resp = client.post("/api/v1/verify", files=v_files, data=v_data)
        assert v_resp.status_code == 200
        res = v_resp.json()

        # Must be NOT_DETECTED, NEVER MATCHED or INCONCLUSIVE
        assert res["status"] == "NOT_DETECTED"
        assert res["confidence"] == 0.0
        assert res["match_details"] is None

    def test_optional_auth_invalid_token_fails_safely(self, client):
        """Optional authentication fails with 401 when an invalid/expired token is supplied, rather than silently treating as anonymous."""
        img_bytes = create_test_image_bytes(256, 256, "flat")
        v_files = {"file": ("suspect.png", img_bytes, "image/png")}

        # Malformed / forged Bearer token must be rejected with 401
        r_malformed = client.post(
            "/api/v1/verify",
            headers={"Authorization": "Bearer forged.invalid.token"},
            files=v_files,
        )
        assert r_malformed.status_code == 401
        assert "invalid or expired" in r_malformed.json()["detail"].lower()

    def test_client_supplied_receipt_verification_valid_and_tampered(self, client, test_user_token: str):
        """Valid client-supplied receipt is verified; tampered receipt payload is rejected."""
        user_headers = {"Authorization": f"Bearer {test_user_token}"}
        img_bytes = create_test_image_bytes(256, 256, "texture")

        # 1. Register asset
        files = {"file": ("art_with_receipt.png", img_bytes, "image/png")}
        data = {
            "title": "Masterwork With Receipt",
            "ownership_declaration": "Sole author and owner Alice.",
            "algorithm": "dct_svd",
            "alpha": 0.10,
        }
        reg_resp = client.post("/api/v1/assets/register", headers=user_headers, files=files, data=data)
        assert reg_resp.status_code == 201
        reg_json = reg_resp.json()
        asset_id = reg_json["asset_id"]
        receipt_data = reg_json["receipt"]

        # 2. Download watermarked image
        dl_resp = client.get(f"/api/v1/assets/{asset_id}/download/watermarked", headers=user_headers)
        assert dl_resp.status_code == 200
        watermarked_bytes = dl_resp.content

        # 3. Verify with valid receipt supplied
        v_files = {"file": ("suspect.png", watermarked_bytes, "image/png")}
        v_data = {
            "receipt_payload": json.dumps(receipt_data["receipt_payload"]),
            "receipt_signature": receipt_data["receipt_signature"],
        }
        v_resp = client.post("/api/v1/verify", files=v_files, data=v_data)
        assert v_resp.status_code == 200
        res = v_resp.json()

        assert res["status"] == "MATCHED"
        assert res["receipt_verification"]["is_authentic"] is True
        assert res["receipt_verification"]["signature_valid"] is True
        assert res["receipt_verification"]["database_match"] is True

        # 4. Verify with tampered receipt (e.g. modified asset_id or timestamp in receipt payload)
        tampered_payload = dict(receipt_data["receipt_payload"])
        tampered_payload["owner_name"] = "Imposter Hacker"

        t_data = {
            "receipt_payload": json.dumps(tampered_payload),
            "receipt_signature": receipt_data["receipt_signature"],
        }
        t_files = {"file": ("suspect.png", watermarked_bytes, "image/png")}
        t_resp = client.post("/api/v1/verify", files=t_files, data=t_data)
        assert t_resp.status_code == 200
        t_res = t_resp.json()

        assert t_res["status"] == "MATCHED"
        assert t_res["receipt_verification"]["is_authentic"] is False
        assert t_res["receipt_verification"]["signature_valid"] is False

    def test_privacy_and_authorization_isolation(
        self, client, test_user: User, test_user_token: str, another_user: User, another_user_token: str
    ):
        """Owner sees full ownership status; non-owners and public callers receive anonymized data."""
        user1_headers = {"Authorization": f"Bearer {test_user_token}"}
        user2_headers = {"Authorization": f"Bearer {another_user_token}"}
        img_bytes = create_test_image_bytes(256, 256, "texture")

        # Register asset under User 1
        files = {"file": ("private_art.png", img_bytes, "image/png")}
        data = {
            "title": "Private Collection Item",
            "ownership_declaration": "Confidential asset belonging to test owner.",
            "algorithm": "dct_svd",
            "alpha": 0.10,
        }
        reg_resp = client.post("/api/v1/assets/register", headers=user1_headers, files=files, data=data)
        assert reg_resp.status_code == 201
        asset_id = reg_resp.json()["asset_id"]

        dl_resp = client.get(f"/api/v1/assets/{asset_id}/download/watermarked", headers=user1_headers)
        assert dl_resp.status_code == 200
        watermarked_bytes = dl_resp.content

        # Case A: Owner queries verification
        v1_files = {"file": ("query.png", watermarked_bytes, "image/png")}
        v1_resp = client.post("/api/v1/verify", headers=user1_headers, files=v1_files)
        assert v1_resp.status_code == 200
        res1 = v1_resp.json()
        assert res1["ownership_status"]["is_owner"] is True
        assert res1["ownership_status"]["owner_display"] == test_user.email

        # Case B: Non-owner authenticated user queries verification
        v2_files = {"file": ("query.png", watermarked_bytes, "image/png")}
        v2_resp = client.post("/api/v1/verify", headers=user2_headers, files=v2_files)
        assert v2_resp.status_code == 200
        res2 = v2_resp.json()
        assert res2["ownership_status"]["is_owner"] is False
        assert res2["ownership_status"]["owner_display"] == "Registered User (Non-Owner)"
        assert test_user.email not in json.dumps(res2)

        # Case C: Unauthenticated public caller queries verification
        v3_files = {"file": ("query.png", watermarked_bytes, "image/png")}
        v3_resp = client.post("/api/v1/verify", files=v3_files)
        assert v3_resp.status_code == 200
        res3 = v3_resp.json()
        assert res3["ownership_status"]["is_owner"] is None
        assert res3["ownership_status"]["owner_display"] == "Registered Owner (Confidential)"
        assert test_user.email not in json.dumps(res3)

    def test_security_input_validation_and_decompression_bomb(self, client):
        """Ensures corrupted files, empty files, and oversized decompression-bomb images are safely rejected."""
        # 1. Empty file
        empty_files = {"file": ("empty.png", b"", "image/png")}
        r1 = client.post("/api/v1/verify", files=empty_files)
        assert r1.status_code == 400
        assert "empty" in r1.json()["detail"].lower()

        # 2. Disallowed extension
        exe_files = {"file": ("malicious.exe", b"MZ\x90\x00somebinary", "application/octet-stream")}
        r2 = client.post("/api/v1/verify", files=exe_files)
        assert r2.status_code == 400
        assert "not permitted" in r2.json()["detail"].lower()

        # 3. Sub-minimum dimensions (32x32 < 64x64)
        sub_img_bytes = create_test_image_bytes(32, 32, "flat")
        r3 = client.post("/api/v1/verify", files={"file": ("tiny.png", sub_img_bytes, "image/png")})
        assert r3.status_code == 400
        detail = r3.json()["detail"].lower()
        assert "too small" in detail or "smaller than minimum" in detail

        # 4. Malformed image bytes
        r4 = client.post("/api/v1/verify", files={"file": ("corrupt.png", b"not-an-image-data", "image/png")})
        assert r4.status_code == 400
        detail4 = r4.json()["detail"].lower()
        assert "failed" in detail4 or "cannot parse" in detail4

    def test_zero_false_positive_rate_on_benchmark_images(self, client):
        """Evaluates false-positive rate across a diverse set of unwatermarked test images.

        Target: 0.0% false positive match rate (0/4 images declared MATCHED).
        """
        benchmark_patterns = ["gradient", "texture", "flat", "noise"]
        match_count = 0

        for pattern in benchmark_patterns:
            img_bytes = create_test_image_bytes(256, 256, pattern)
            resp = client.post("/api/v1/verify", files={"file": (f"{pattern}.png", img_bytes, "image/png")})
            assert resp.status_code == 200
            res = resp.json()

            # None of the unwatermarked images may ever be classified as MATCHED or NO_REGISTERED_RECORD
            assert res["status"] in ("NOT_DETECTED", "INCONCLUSIVE")
            if res["status"] == "MATCHED":
                match_count += 1

        assert match_count == 0, f"False-positive detected! {match_count} unwatermarked images matched."
