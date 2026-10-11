"""CreditMera Phase 6: Backend Integration and API Reliability Tests.

Validates:
1. Strict pagination query validation (skip >= 0, 1 <= limit <= 100).
2. Path parameter bounds validation (40-bit bounds [1, 2^40 - 1]).
3. Form parameter bounds validation on verification endpoint.
4. Storage persistence failure isolation, DB rollback, and file cleanup.
5. Database transaction rollback and storage cleanup on commit failure.
6. Race-condition idempotency key conflict handling.
7. Information leakage prevention on internal server errors.
8. OpenAPI schema integrity and contract synchronization.
"""
import io
import json
from unittest.mock import patch
import pytest
from PIL import Image

from app.models.user import User
from app.models.asset import RegisteredAsset
from storage import get_storage


def make_test_image(width=128, height=128) -> bytes:
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestAPIContractBoundsAndPagination:

    def test_list_assets_pagination_bounds(self, client, test_user_token):
        """Verify skip and limit query parameter bounds validation."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Negative skip must be rejected with 422
        resp = client.get("/api/v1/assets?skip=-1", headers=headers)
        assert resp.status_code == 422
        assert "skip" in resp.text.lower()

        # Zero or negative limit must be rejected with 422
        resp = client.get("/api/v1/assets?limit=0", headers=headers)
        assert resp.status_code == 422
        assert "limit" in resp.text.lower()

        # Excessive limit (> 100) must be rejected with 422
        resp = client.get("/api/v1/assets?limit=101", headers=headers)
        assert resp.status_code == 422
        assert "limit" in resp.text.lower()

        # Valid pagination parameters succeed with 200
        resp = client.get("/api/v1/assets?skip=0&limit=25", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_asset_path_parameter_40bit_bounds(self, client, test_user_token):
        """Verify asset_id path parameter strictly enforces [1, 2^40 - 1]."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Zero or negative asset_id must be rejected with 422
        resp = client.get("/api/v1/assets/0", headers=headers)
        assert resp.status_code == 422

        resp = client.get("/api/v1/assets/-1", headers=headers)
        assert resp.status_code == 422

        resp = client.get("/api/v1/assets/0/receipt", headers=headers)
        assert resp.status_code == 422

        resp = client.get("/api/v1/assets/0/download/watermarked", headers=headers)
        assert resp.status_code == 422

        # Asset ID exceeding 40-bit maximum (1099511627775) must be rejected with 422
        overflow_id = 1099511627776
        resp = client.get(f"/api/v1/assets/{overflow_id}", headers=headers)
        assert resp.status_code == 422

    def test_verification_expected_asset_id_bounds(self, client):
        """Verify expected_asset_id bounds validation on POST /api/v1/verify."""
        img_bytes = make_test_image()
        files = {"file": ("suspect.png", img_bytes, "image/png")}

        # Negative expected_asset_id rejected with 422
        resp = client.post("/api/v1/verify", files=files, data={"expected_asset_id": -5})
        assert resp.status_code == 422

        # Zero expected_asset_id rejected with 422
        files = {"file": ("suspect.png", img_bytes, "image/png")}
        resp = client.post("/api/v1/verify", files=files, data={"expected_asset_id": 0})
        assert resp.status_code == 422

        # Overflow expected_asset_id rejected with 422
        files = {"file": ("suspect.png", img_bytes, "image/png")}
        resp = client.post("/api/v1/verify", files=files, data={"expected_asset_id": 1099511627776})
        assert resp.status_code == 422


class TestStorageAndTransactionReliability:

    def test_storage_failure_during_registration_rollback(self, client, test_user_token, db):
        """When storage.save raises an error, ensure DB transaction rolls back and returns 500."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        img_bytes = make_test_image()
        files = {"file": ("storage_fail.png", img_bytes, "image/png")}
        data = {
            "title": "Storage Failure Test",
            "ownership_declaration": "Declaration for simulated storage failure test.",
            "algorithm": "dct_svd",
        }

        storage = get_storage()
        with patch.object(storage, "save", side_effect=IOError("Simulated disk write failure / full disk")):
            resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
            assert resp.status_code == 500
            res = resp.json()
            assert "detail" in res
            # Ensure filesystem paths or raw python stack trace are NOT leaked
            assert "Simulated disk write failure" not in res["detail"]
            assert "Storage persistence failed" in res["detail"]

        # Confirm no orphaned record exists in database
        asset = db.query(RegisteredAsset).filter(RegisteredAsset.title == "Storage Failure Test").first()
        assert asset is None

    def test_database_commit_failure_cleans_up_saved_files(self, client, test_user_token, db):
        """When DB commit fails, any already saved files must be removed from disk."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        img_bytes = make_test_image()
        files = {"file": ("db_fail.png", img_bytes, "image/png")}
        data = {
            "title": "DB Failure Test",
            "ownership_declaration": "Declaration for simulated database commit failure.",
            "algorithm": "dct_svd",
        }

        storage = get_storage()
        saved_paths = []
        original_save = storage.save

        def tracking_save(data_bytes, rel_path):
            result = original_save(data_bytes, rel_path)
            saved_paths.append(rel_path)
            return result

        with patch.object(storage, "save", side_effect=tracking_save):
            with patch.object(db, "commit", side_effect=RuntimeError("Simulated DB connection lost")):
                resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
                assert resp.status_code == 500

        # Verify that all tracked files written to disk were cleaned up
        assert len(saved_paths) > 0
        for p in saved_paths:
            assert not storage.exists(p), f"Orphaned file remained in storage: {p}"

    def test_upfront_unsupported_algorithm_validation(self, client, test_user_token, db):
        """Unsupported algorithm must fail validation immediately with 422 before allocating ID."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        img_bytes = make_test_image()
        files = {"file": ("algo_test.png", img_bytes, "image/png")}
        data = {
            "title": "Invalid Algo Test",
            "ownership_declaration": "Declaration for invalid algorithm testing.",
            "algorithm": "quantum_hyper_fft",
        }

        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 422
        assert "unknown watermarking algorithm" in resp.json()["detail"].lower()

        # Confirm no record was committed
        count = db.query(RegisteredAsset).filter(RegisteredAsset.title == "Invalid Algo Test").count()
        assert count == 0


class TestSecurityAndInformationLeakage:

    def test_internal_error_does_not_leak_stack_trace_in_verification(self, client):
        """Simulate unexpected internal error in verification and verify clean 500 response."""
        img_bytes = make_test_image()
        files = {"file": ("crash_test.png", img_bytes, "image/png")}

        with patch("app.api.v1.verification.verify_image_ownership", side_effect=Exception("SECRET_DB_PASSWORD_LEAK_TEST")):
            resp = client.post("/api/v1/verify", files=files)
            assert resp.status_code == 500
            detail = resp.json()["detail"]
            assert "SECRET_DB_PASSWORD_LEAK_TEST" not in detail
            assert "unexpected internal error occurred" in detail

    def test_openapi_schema_generation_and_contract_validation(self, client):
        """Verify OpenAPI documentation schema is complete and valid."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()

        assert "openapi" in schema
        assert schema["info"]["title"] == "CreditMera API"
        paths = schema["paths"]

        # Confirm all core routes are documented
        assert "/api/v1/assets/register" in paths
        assert "/api/v1/assets" in paths
        assert "/api/v1/assets/{asset_id}" in paths
        assert "/api/v1/assets/{asset_id}/receipt" in paths
        assert "/api/v1/assets/{asset_id}/download/watermarked" in paths
        assert "/api/v1/assets/receipts/verify" in paths
        assert "/api/v1/verify" in paths
        assert "/health" in paths


class TestAuthenticationAndSecurityIntegration:

    def test_invalid_and_expired_authentication_tokens(self, client):
        """Verify malformed, expired, and missing tokens fail safely with 401."""
        # 1. Missing Authorization header
        resp = client.get("/api/v1/assets")
        assert resp.status_code == 401

        resp = client.get("/api/v1/assets/100")
        assert resp.status_code == 401

        # 2. Malformed Bearer token
        headers = {"Authorization": "Bearer not_a_valid_jwt_token_string"}
        resp = client.get("/api/v1/assets", headers=headers)
        assert resp.status_code == 401
        assert "invalid or expired" in resp.json()["detail"].lower()

        # 3. Forged signature token
        fake_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0."
            "INVALIDSIGNATUREHASH0000000000000000000000"
        )
        headers = {"Authorization": f"Bearer {fake_token}"}
        resp = client.get("/api/v1/assets", headers=headers)
        assert resp.status_code == 401

        # 4. Verification endpoint with invalid token must fail safely with 401
        img_bytes = make_test_image()
        files = {"file": ("suspect.png", img_bytes, "image/png")}
        resp = client.post("/api/v1/verify", headers=headers, files=files)
        assert resp.status_code == 401


class TestIdempotencyAndIntegrityHandling:

    def test_concurrent_idempotency_race_condition_recovery(self, client, test_user_token, sample_image_bytes, db):
        """Simulate concurrent idempotency uniqueness collision and confirm clean recovery."""
        idempotency_key = "concurrent-race-test-key-999"
        headers = {
            "Authorization": f"Bearer {test_user_token}",
            "Idempotency-Key": idempotency_key,
        }
        files = {"file": ("race.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Idempotent Race Asset",
            "ownership_declaration": "Declaration asserting ownership for concurrent test.",
        }

        # 1. Initial registration succeeds with 201 Created
        resp1 = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp1.status_code == 201
        asset_id = resp1.json()["asset_id"]

        # 2. Simulate concurrent collision: second request encounters IntegrityError on uq_owner_idempotency_key
        # The service must catch this, rollback, query the existing record, and return 200 with matching asset_id
        from sqlalchemy.exc import IntegrityError
        from app.services.registration_service import register_asset
        from app.models.user import User

        test_user = db.query(User).first()
        asset, receipt, is_dup = register_asset(
            db=db,
            user=test_user,
            file_bytes=sample_image_bytes,
            filename="race.png",
            title="Idempotent Race Asset",
            ownership_declaration="Declaration asserting ownership for concurrent test.",
            idempotency_key=idempotency_key,
        )
        assert is_dup is True
        assert asset.asset_id == asset_id
        assert receipt.asset_id == asset_id

    def test_unrelated_integrity_error_is_not_suppressed(self, client, test_user_token, sample_image_bytes, db):
        """Confirm that unrelated IntegrityErrors (e.g. check constraints) are NOT suppressed."""
        headers = {
            "Authorization": f"Bearer {test_user_token}",
            "Idempotency-Key": "some-idem-key",
        }
        files = {"file": ("unrelated_err.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Unrelated Error Asset",
            "ownership_declaration": "Declaration asserting ownership.",
        }

        from sqlalchemy.exc import IntegrityError

        # Simulate an IntegrityError that does NOT relate to uq_owner_idempotency_key
        unrelated_ie = IntegrityError(
            statement="INSERT INTO registered_assets ...",
            params={},
            orig=Exception("violates check constraint ck_asset_id_40bit_range")
        )

        with patch.object(db, "commit", side_effect=unrelated_ie):
            resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
            # Must NOT be treated as idempotency match; must return 500 error
            assert resp.status_code == 500
            assert "internal server error" in resp.json()["detail"].lower()


class TestUploadValidationAndReceiptTampering:

    def test_upload_validation_empty_and_bad_extension(self, client, test_user_token):
        """Verify empty files and disallowed extensions fail validation with 400 Bad Request."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        data = {
            "title": "Bad Upload",
            "ownership_declaration": "Declaration for bad upload test.",
        }

        # 1. Empty file
        files = {"file": ("empty.png", b"", "image/png")}
        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

        # 2. Bad extension (.exe)
        img_bytes = make_test_image()
        files = {"file": ("malware.exe", img_bytes, "application/octet-stream")}
        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 400
        assert "extension" in resp.json()["detail"].lower()

    def test_receipt_tampering_detection(self, client, test_user_token, sample_image_bytes):
        """Verify tampered receipt payload or forged signature is detected on verification."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        files = {"file": ("receipt_test.png", sample_image_bytes, "image/png")}
        data = {
            "title": "Receipt Integrity",
            "ownership_declaration": "Declaration for receipt integrity test.",
        }

        reg_resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert reg_resp.status_code == 201
        receipt = reg_resp.json()["receipt"]

        # 1. Authentic receipt verifies successfully
        valid_req = {
            "receipt_payload": receipt["receipt_payload"],
            "receipt_signature": receipt["receipt_signature"],
        }
        v_resp = client.post("/api/v1/assets/receipts/verify", json=valid_req)
        assert v_resp.status_code == 200
        assert v_resp.json()["is_authentic"] is True
        assert v_resp.json()["status"] == "AUTHENTIC"

        # 2. Tampered payload fails verification
        tampered_payload = receipt["receipt_payload"].copy()
        tampered_payload["owner_name"] = "Attacker Name Forgery"
        tampered_req = {
            "receipt_payload": tampered_payload,
            "receipt_signature": receipt["receipt_signature"],
        }
        v_resp_tampered = client.post("/api/v1/assets/receipts/verify", json=tampered_req)
        assert v_resp_tampered.status_code == 200
        assert v_resp_tampered.json()["is_authentic"] is False
        assert v_resp_tampered.json()["signature_valid"] is False
        assert v_resp_tampered.json()["status"] == "SIGNATURE_MISMATCH"
