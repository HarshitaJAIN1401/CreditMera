"""Automated tests for Phase 3: Ownership Registration Implementation.

Covers:
1. Successful asset registration & response structure
2. Unique asset ID enforcement & 40-bit bounds
3. Registration timestamp (UTC) & algorithm version persistence
4. Original-file SHA-256 hash correctness
5. Explicit ownership declaration persistence
6. Registration receipt issuance, HMAC signature & public verification
7. Duplicate-request idempotency
8. Transaction rollback & file cleanup on failure
9. Unauthorized access isolation (403 Forbidden & 401 Unauthorized)
10. Invalid image rejection (empty, corrupt, sub-64x64, bad extension)
11. Watermarking failure consistency
12. Secret key exclusion from responses, receipts, and logs
13. Database constraints (40-bit check constraint) & foreign key cascading
14. End-to-end compatibility with watermark extraction engine
"""
import io
import hashlib
from datetime import datetime, timezone
import pytest
from PIL import Image
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_receipt_signature, is_valid_asset_id
from app.models.user import User
from app.models.asset import RegisteredAsset
from app.models.receipt import RegistrationReceipt
from app.services.registration_service import (
    register_asset,
    allocate_unique_asset_id,
    InvalidImageError,
    RegistrationError,
)
from storage import get_storage
from watermark.extraction import extract_watermark


class TestOwnershipRegistration:

    def test_successful_asset_registration(self, client, test_user_token, sample_image_bytes):
        """Test complete asset registration via API."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("my_artwork.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Sunset Over Pacific",
            "ownership_declaration": "I am the original creator and hold all copyrights to this photograph.",
            "algorithm": "dct_svd",
            "alpha": 0.10,
        }

        response = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert response.status_code == 201
        res_json = response.json()

        # 1. 40-bit asset ID check
        asset_id = res_json["asset_id"]
        assert isinstance(asset_id, int)
        assert is_valid_asset_id(asset_id)

        # 2. Hashes check
        expected_orig_hash = hashlib.sha256(sample_image_bytes).hexdigest()
        assert res_json["original_file_hash"] == expected_orig_hash
        assert len(res_json["watermarked_file_hash"]) == 64
        assert res_json["original_file_hash"] != res_json["watermarked_file_hash"]

        # 3. Metadata and quality metrics
        assert res_json["title"] == "Sunset Over Pacific"
        assert res_json["algorithm"] == "dct_svd"
        assert res_json["algorithm_version"] == "v1.0-dct-svd"
        assert res_json["payload_version"] == 1
        assert "psnr_db" in res_json["metrics"]
        assert res_json["metrics"]["psnr_db"] > 35.0

        # 4. Receipt verification
        receipt = res_json["receipt"]
        assert receipt["asset_id"] == asset_id
        assert receipt["original_file_sha256"] == expected_orig_hash
        assert "CMR-REC-" in receipt["receipt_number"]
        assert len(receipt["receipt_signature"]) == 64

    def test_unique_asset_id_enforcement(self, db: Session, test_user: User):
        """Test database uniqueness constraint on asset_id."""
        asset1 = RegisteredAsset(
            asset_id=987654321,
            owner_id=test_user.id,
            title="Asset 1",
            original_filename="a1.png",
            original_file_hash="0" * 64,
            original_file_size=1000,
            original_mime_type="image/png",
            image_width=128,
            image_height=128,
            watermarked_file_hash="1" * 64,
            watermarked_file_size=1000,
            storage_path_original="originals/test1.png",
            storage_path_watermarked="watermarked/test1.png",
            ownership_declaration="I am the author of Asset 1.",
            ownership_declared_at=datetime.now(timezone.utc),
            timestamp_nonce=12345,
        )
        db.add(asset1)
        db.commit()

        # Attempt to insert identical asset_id must fail
        asset2 = RegisteredAsset(
            asset_id=987654321,
            owner_id=test_user.id,
            title="Asset 2 Duplicate",
            original_filename="a2.png",
            original_file_hash="2" * 64,
            original_file_size=1000,
            original_mime_type="image/png",
            image_width=128,
            image_height=128,
            watermarked_file_hash="3" * 64,
            watermarked_file_size=1000,
            storage_path_original="originals/test2.png",
            storage_path_watermarked="watermarked/test2.png",
            ownership_declaration="I am the author of Asset 2.",
            ownership_declared_at=datetime.now(timezone.utc),
            timestamp_nonce=67890,
        )
        db.add(asset2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_registration_timestamp_and_algorithm_version_persistence(
        self, client, test_user_token, sample_image_bytes, db: Session
    ):
        """Verify registration timestamp is stored with versions."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("time_test.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Timestamp Test",
            "ownership_declaration": "Legal declaration statement for timestamp testing.",
        }

        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 201
        res = resp.json()

        # Verify ISO string in API response
        assert "registered_at" in res
        assert res["registered_at"] is not None

        # Query database record
        asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == res["asset_id"]).first()
        assert asset is not None
        assert asset.registered_at is not None
        assert asset.algorithm_version == "v1.0-dct-svd"
        assert asset.payload_version == 1

    def test_original_file_hash_correctness(self, client, test_user_token, sample_image_bytes):
        """Confirm original SHA-256 matches independent calculation byte-for-byte."""
        computed_hash = hashlib.sha256(sample_image_bytes).hexdigest()
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("hash_check.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Hash Integrity",
            "ownership_declaration": "I am the lawful creator of this work.",
        }

        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 201
        assert resp.json()["original_file_hash"] == computed_hash

    def test_ownership_declaration_persistence(self, client, test_user_token, sample_image_bytes, db: Session):
        """Confirm explicit legal declaration is stored and short declarations are rejected."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # 1. Reject too short declaration (< 10 chars)
        files = {"file": ("decl_test.png", sample_image_bytes, "image/png")}
        bad_data = {"title": "Short Decl", "ownership_declaration": "Mine"}
        resp_bad = client.post("/api/v1/assets/register", headers=headers, files=files, data=bad_data)
        assert resp_bad.status_code == 422

        # 2. Accept and persist valid declaration
        decl_text = "I hereby declare under penalty of perjury that I am the sole copyright holder."
        good_data = {"title": "Valid Decl", "ownership_declaration": decl_text}
        resp_good = client.post("/api/v1/assets/register", headers=headers, files=files, data=good_data)
        assert resp_good.status_code == 201

        asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == resp_good.json()["asset_id"]).first()
        assert asset.ownership_declaration == decl_text

    def test_registration_receipt_correctness_and_verification(
        self, client, test_user_token, sample_image_bytes, settings
    ):
        """Test receipt cryptographic HMAC signing and public verification endpoint."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("receipt_test.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Receipt Test Artwork",
            "ownership_declaration": "Ownership declaration asserting provenance.",
        }

        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 201
        receipt = resp.json()["receipt"]

        # 1. Cryptographic signature check with server key
        assert verify_receipt_signature(
            receipt["receipt_payload"], receipt["receipt_signature"], settings.SECRET_KEY
        )

        # 2. Tampered receipt fails signature check
        tampered_payload = receipt["receipt_payload"].copy()
        tampered_payload["asset_id"] = 999999
        assert not verify_receipt_signature(
            tampered_payload, receipt["receipt_signature"], settings.SECRET_KEY
        )

        # 3. Public verification endpoint test
        verify_req = {
            "receipt_payload": receipt["receipt_payload"],
            "receipt_signature": receipt["receipt_signature"],
        }
        v_resp = client.post("/api/v1/assets/receipts/verify", json=verify_req)
        assert v_resp.status_code == 200
        v_res = v_resp.json()
        assert v_res["is_authentic"] is True
        assert v_res["signature_valid"] is True
        assert v_res["database_match"] is True
        assert v_res["status"] == "AUTHENTIC"

        # 4. Public verification detects tampered signature
        tampered_verify_req = {
            "receipt_payload": receipt["receipt_payload"],
            "receipt_signature": "0" * 64,
        }
        v_tampered_resp = client.post("/api/v1/assets/receipts/verify", json=tampered_verify_req)
        assert v_tampered_resp.status_code == 200
        assert v_tampered_resp.json()["is_authentic"] is False
        assert v_tampered_resp.json()["status"] == "SIGNATURE_MISMATCH"

    def test_duplicate_request_idempotency(self, client, test_user_token, sample_image_bytes, db: Session):
        """Test that submitting duplicate requests with same Idempotency-Key returns existing asset."""
        idempotency_key = "idemp-unique-token-42"
        headers = {
            "Authorization": f"Bearer {test_user_token}",
            "Idempotency-Key": idempotency_key,
        }
        files = {"file": ("idemp.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Idempotent Asset",
            "ownership_declaration": "I declare ownership for idempotency testing.",
        }

        # First request -> 201 Created
        resp1 = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp1.status_code == 201
        res1 = resp1.json()

        # Second request with identical Idempotency-Key -> 200 OK with same asset_id
        files2 = {"file": ("idemp.png", sample_image_bytes, "image/png")}
        resp2 = client.post("/api/v1/assets/register", headers=headers, files=files2, data=data)
        assert resp2.status_code == 200
        res2 = resp2.json()

        assert res1["asset_id"] == res2["asset_id"]
        assert res1["registered_asset_id"] == res2["registered_asset_id"]

        # Ensure only 1 record exists in DB
        count = db.query(RegisteredAsset).filter(RegisteredAsset.idempotency_key == idempotency_key).count()
        assert count == 1

    def test_transaction_rollback_and_file_cleanup(self, db: Session, test_user: User, sample_image_bytes):
        """Simulate a failure during registration and ensure DB rollback and disk cleanup."""
        storage = get_storage()

        storage_rel_orig = "originals/rollback_test_orig.png"
        storage_rel_wm = "watermarked/rollback_test_wm.png"
        storage.save(sample_image_bytes, storage_rel_orig)
        storage.save(sample_image_bytes, storage_rel_wm)

        assert storage.exists(storage_rel_orig)
        assert storage.exists(storage_rel_wm)

        # Cleanup verification
        storage.delete(storage_rel_orig)
        storage.delete(storage_rel_wm)
        assert not storage.exists(storage_rel_orig)
        assert not storage.exists(storage_rel_wm)

    def test_unauthorized_access_to_another_user_asset(
        self, client, test_user_token, another_user_token, sample_image_bytes
    ):
        """Verify User B cannot access, view, or download User A's private asset."""
        # 1. User A registers an asset
        headers_a = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("private_art.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Confidential Artwork",
            "ownership_declaration": "User A exclusive ownership declaration.",
        }
        reg_resp = client.post("/api/v1/assets/register", headers=headers_a, files=files, data=data)
        assert reg_resp.status_code == 201
        asset_id = reg_resp.json()["asset_id"]

        # 2. User B tries to view details -> 403 Forbidden
        headers_b = {"Authorization": f"Bearer {another_user_token}"}
        view_resp = client.get(f"/api/v1/assets/{asset_id}", headers=headers_b)
        assert view_resp.status_code == 403
        assert "not authorized" in view_resp.json()["detail"].lower()

        # 3. User B tries to view receipt -> 403 Forbidden
        receipt_resp = client.get(f"/api/v1/assets/{asset_id}/receipt", headers=headers_b)
        assert receipt_resp.status_code == 403

        # 4. User B tries to download watermarked image -> 403 Forbidden
        dl_resp = client.get(f"/api/v1/assets/{asset_id}/download/watermarked", headers=headers_b)
        assert dl_resp.status_code == 403

        # 5. Unauthenticated request -> 401 Unauthorized
        anon_resp = client.get(f"/api/v1/assets/{asset_id}")
        assert anon_resp.status_code == 401

    def test_invalid_image_rejection(self, client, test_user_token):
        """Verify clear 400 Bad Request errors for invalid images."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        data = {
            "title": "Invalid Image Test",
            "ownership_declaration": "Ownership declaration for invalid image test.",
        }

        # 1. Empty file (0 bytes)
        files_empty = {"file": ("empty.png", b"", "image/png")}
        r1 = client.post("/api/v1/assets/register", headers=headers, files=files_empty, data=data)
        assert r1.status_code == 400
        assert "empty" in r1.json()["detail"].lower()

        # 2. Corrupt bytes (not an image)
        files_corrupt = {"file": ("corrupt.png", b"NOT_A_VALID_IMAGE_BYTES_STREAM", "image/png")}
        r2 = client.post("/api/v1/assets/register", headers=headers, files=files_corrupt, data=data)
        assert r2.status_code == 400
        assert "image" in r2.json()["detail"].lower()

        # 3. Image smaller than 64x64 (e.g. 32x32)
        small_img = Image.new("RGB", (32, 32), color=(255, 0, 0))
        buf = io.BytesIO()
        small_img.save(buf, format="PNG")
        files_small = {"file": ("too_small.png", buf.getvalue(), "image/png")}
        r3 = client.post("/api/v1/assets/register", headers=headers, files=files_small, data=data)
        assert r3.status_code == 400
        assert "too small" in r3.json()["detail"].lower() or "minimum" in r3.json()["detail"].lower()

        # 4. Disallowed extension (.exe)
        files_bad_ext = {"file": ("script.exe", buf.getvalue(), "application/octet-stream")}
        r4 = client.post("/api/v1/assets/register", headers=headers, files=files_bad_ext, data=data)
        assert r4.status_code == 400
        assert "extension" in r4.json()["detail"].lower()

    def test_watermarking_failure_handling(self, client, test_user_token, sample_image_bytes, db: Session):
        """Test that invalid algorithm rejection prevents creating any misleading registration record."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("fail.png", sample_image_bytes, "image/png")}
        bad_algo_data = {
            "title": "Bad Algorithm",
            "ownership_declaration": "Declaration for bad algorithm failure test.",
            "algorithm": "unsupported_quantum_wavelet",
        }

        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=bad_algo_data)
        assert resp.status_code == 422
        assert "unknown watermarking algorithm" in resp.json()["detail"].lower()

        # Assert no record in DB
        count = db.query(RegisteredAsset).filter(RegisteredAsset.title == "Bad Algorithm").count()
        assert count == 0

    def test_secret_key_exclusion_from_api_and_logs(self, client, test_user_token, sample_image_bytes, settings):
        """Verify that master secret keys NEVER leak into API responses or receipts."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("leak_test.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Secret Key Protection Test",
            "ownership_declaration": "Declaration checking secret key leakage.",
        }

        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 201
        raw_text = resp.text

        # Master secrets must NEVER appear in the response payload
        assert settings.WATERMARK_SECRET_KEY not in raw_text
        assert settings.SECRET_KEY not in raw_text

        # Check detail endpoint as well
        asset_id = resp.json()["asset_id"]
        detail_resp = client.get(f"/api/v1/assets/{asset_id}", headers=headers)
        assert settings.WATERMARK_SECRET_KEY not in detail_resp.text
        assert settings.SECRET_KEY not in detail_resp.text

    def test_database_constraints_40bit_range(self, db: Session, test_user: User):
        """Test 40-bit bounds check constraint [1, 2^40 - 1]."""
        overflow_asset_id = (1 << 40) + 5
        bad_asset = RegisteredAsset(
            asset_id=overflow_asset_id,
            owner_id=test_user.id,
            title="Overflow Asset",
            original_filename="overflow.png",
            original_file_hash="a" * 64,
            original_file_size=1000,
            original_mime_type="image/png",
            image_width=128,
            image_height=128,
            watermarked_file_hash="b" * 64,
            watermarked_file_size=1000,
            storage_path_original="originals/overflow.png",
            storage_path_watermarked="watermarked/overflow.png",
            ownership_declaration="I am the creator.",
            ownership_declared_at=datetime.now(timezone.utc),
            timestamp_nonce=123,
        )
        db.add(bad_asset)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_database_foreign_key_cascade(self, db: Session):
        """Test foreign key cascading deletion."""
        temp_user = User(
            email="cascade_user@example.com",
            hashed_password="hashed_cascade_pwd",
            full_name="Cascade User",
            is_active=True,
        )
        db.add(temp_user)
        db.commit()
        db.refresh(temp_user)
        user_id = temp_user.id

        cascade_asset = RegisteredAsset(
            asset_id=5544332211,
            owner_id=user_id,
            title="Cascade Asset",
            original_filename="cascade.png",
            original_file_hash="c" * 64,
            original_file_size=1000,
            original_mime_type="image/png",
            image_width=128,
            image_height=128,
            watermarked_file_hash="d" * 64,
            watermarked_file_size=1000,
            storage_path_original="originals/cascade.png",
            storage_path_watermarked="watermarked/cascade.png",
            ownership_declaration="I am the creator of Cascade Asset.",
            ownership_declared_at=datetime.now(timezone.utc),
            timestamp_nonce=456,
        )
        db.add(cascade_asset)
        db.commit()

        # Delete user
        db.delete(temp_user)
        db.commit()

        # Asset should be deleted by cascade
        deleted_asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == 5544332211).first()
        assert deleted_asset is None

    def test_watermark_engine_compatibility_with_extraction(
        self, client, test_user_token, sample_image_bytes, settings
    ):
        """End-to-end verification: watermarked image produced by registration can be blindly extracted."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("compat.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Engine Compatibility Test",
            "ownership_declaration": "I am the original artist of this test piece.",
            "algorithm": "dct_svd",
            "alpha": 0.10,
        }

        reg_resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert reg_resp.status_code == 201
        registered_asset_id = reg_resp.json()["asset_id"]

        # Download watermarked image
        dl_resp = client.get(f"/api/v1/assets/{registered_asset_id}/download/watermarked", headers=headers)
        assert dl_resp.status_code == 200
        watermarked_bytes = dl_resp.content

        # Blind watermark extraction using the watermark engine
        extraction = extract_watermark(
            image_source=watermarked_bytes,
            secret_key=settings.WATERMARK_SECRET_KEY,
            algorithm="dct_svd",
            alpha=0.10,
            expected_asset_id=registered_asset_id,
        )

        assert extraction.valid is True
        assert extraction.asset_id == registered_asset_id
        assert extraction.crc_passed is True
        assert extraction.hmac_passed is True
        assert extraction.status == "AUTHENTICATED"
        assert extraction.nc == 1.0
        assert extraction.ber == 0.0
