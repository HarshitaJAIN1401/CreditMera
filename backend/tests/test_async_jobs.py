"""Tests for Phase 8: Asynchronous Background Jobs & Scalability.

Covers:
1. Asynchronous asset submission returns HTTP 202 Accepted with job polling metadata.
2. Background worker execution (PENDING -> PROCESSING -> COMPLETED) with asset and receipt persistence.
3. Job polling endpoint GET /api/v1/jobs/{job_id} reporting progress and results.
4. User job list endpoint GET /api/v1/jobs with pagination and total count.
5. Multi-tenant privacy isolation (User B cannot access or view User A's jobs).
6. Unauthenticated requests to job endpoints return HTTP 401 Unauthorized.
7. Input validation (corrupt image, sub-64x64, unsupported algorithm) rejected at submission.
8. Safe error handling when worker encounters missing user or internal errors (transitions to FAILED).
9. Presigned download redirect integration with storage provider.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from sqlalchemy.orm import Session

from app.models.job import AsyncJob
from app.models.asset import RegisteredAsset
from app.models.receipt import RegistrationReceipt
from app.models.user import User
from app.services.job_service import (
    create_job,
    get_job_by_id,
    list_user_jobs,
    run_async_registration_worker,
)
from storage.base import StorageProvider


def test_register_async_accepted(client, test_user_token, sample_image_bytes):
    """Verify POST /api/v1/assets/register-async returns 202 Accepted with polling URL."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    files = {"file": ("async_artwork.png", sample_image_bytes, "image/png")}
    data = {
        "title": "Asynchronous Sunset",
        "ownership_declaration": "I am the original copyright holder for this digital artwork.",
        "algorithm": "dct_svd",
        "alpha": 0.10,
    }

    response = client.post("/api/v1/assets/register-async", headers=headers, files=files, data=data)
    assert response.status_code == 202
    res_json = response.json()

    assert "job_id" in res_json
    assert res_json["job_type"] == "ASSET_REGISTRATION"
    assert res_json["status"] in ("PENDING", "COMPLETED")
    assert res_json["poll_url"] == f"/api/v1/jobs/{res_json['job_id']}"


def test_job_worker_execution_and_polling(client, test_user_token, sample_image_bytes, db: Session):
    """Verify full background worker lifecycle and job status polling."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    files = {"file": ("async_canvas.png", sample_image_bytes, "image/png")}
    data = {
        "title": "Deep Sea Landscape",
        "ownership_declaration": "Original photograph captured and created by the submitter.",
        "algorithm": "dct_svd",
        "alpha": 0.12,
    }

    response = client.post("/api/v1/assets/register-async", headers=headers, files=files, data=data)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Since FastAPI TestClient executes BackgroundTasks synchronously on response completion,
    # the worker has already executed!
    status_resp = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert status_resp.status_code == 200
    job_data = status_resp.json()

    assert job_data["job_id"] == job_id
    assert job_data["status"] == "COMPLETED"
    assert job_data["progress"] == 100
    assert job_data["title"] == "Deep Sea Landscape"
    assert job_data["asset_id"] is not None
    assert job_data["error_message"] is None

    result = job_data["result"]
    assert result is not None
    assert result["asset_id"] == job_data["asset_id"]
    assert "receipt_number" in result
    assert "watermarked_file_hash" in result
    assert "metrics" in result
    assert result["metrics"]["psnr_db"] > 30.0

    # Verify database persistence
    asset = db.query(RegisteredAsset).filter(RegisteredAsset.asset_id == job_data["asset_id"]).first()
    assert asset is not None
    assert asset.title == "Deep Sea Landscape"

    receipt = db.query(RegistrationReceipt).filter(RegistrationReceipt.asset_id == job_data["asset_id"]).first()
    assert receipt is not None
    assert receipt.receipt_number == result["receipt_number"]


def test_list_user_jobs(client, test_user_token, sample_image_bytes):
    """Verify GET /api/v1/jobs returns paginated job list for the user."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    files = {"file": ("job1.png", sample_image_bytes, "image/png")}
    data = {
        "title": "Batch Job 1",
        "ownership_declaration": "Author declaration for first job submission.",
        "algorithm": "dct",
        "alpha": 0.08,
    }
    client.post("/api/v1/assets/register-async", headers=headers, files=files, data=data)

    response = client.get("/api/v1/jobs?skip=0&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "jobs" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["jobs"]) >= 1

    first_job = data["jobs"][0]
    assert "job_id" in first_job
    assert "status" in first_job
    assert "progress" in first_job
    assert "created_at" in first_job


def test_job_tenant_isolation(client, test_user_token, another_user_token, sample_image_bytes):
    """Verify that User B cannot view User A's background job (enforcing 404)."""
    headers_user_a = {"Authorization": f"Bearer {test_user_token}"}
    headers_user_b = {"Authorization": f"Bearer {another_user_token}"}

    files = {"file": ("user_a_art.png", sample_image_bytes, "image/png")}
    data = {
        "title": "User A Private Asset",
        "ownership_declaration": "Sole ownership by User A.",
        "algorithm": "dct_svd",
        "alpha": 0.10,
    }

    res = client.post("/api/v1/assets/register-async", headers=headers_user_a, files=files, data=data)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # User A can view their own job
    get_res_a = client.get(f"/api/v1/jobs/{job_id}", headers=headers_user_a)
    assert get_res_a.status_code == 200

    # User B receives 404 Not Found
    get_res_b = client.get(f"/api/v1/jobs/{job_id}", headers=headers_user_b)
    assert get_res_b.status_code == 404
    assert f"Job with ID '{job_id}' not found." in get_res_b.json()["detail"]


def test_job_unauthenticated_requests(client):
    """Verify unauthenticated requests to job endpoints return 401."""
    res_list = client.get("/api/v1/jobs")
    assert res_list.status_code == 401

    res_get = client.get("/api/v1/jobs/nonexistent-id")
    assert res_get.status_code == 401


def test_register_async_validation_errors(client, test_user_token, sample_image_bytes):
    """Verify invalid input data is rejected synchronously at submission."""
    headers = {"Authorization": f"Bearer {test_user_token}"}

    # 1. Unsupported algorithm
    files = {"file": ("test.png", sample_image_bytes, "image/png")}
    data = {
        "title": "Invalid Algo",
        "ownership_declaration": "Legal declaration text goes here.",
        "algorithm": "elliptic_curve_unknown",
        "alpha": 0.10,
    }
    res = client.post("/api/v1/assets/register-async", headers=headers, files=files, data=data)
    assert res.status_code == 422
    assert "Unsupported watermarking algorithm" in res.json()["detail"]

    # 2. Corrupt / empty file
    corrupt_files = {"file": ("bad.png", b"not-a-valid-image", "image/png")}
    data_valid = {
        "title": "Corrupt File",
        "ownership_declaration": "Legal declaration text goes here.",
        "algorithm": "dct_svd",
        "alpha": 0.10,
    }
    res_corrupt = client.post("/api/v1/assets/register-async", headers=headers, files=corrupt_files, data=data_valid)
    assert res_corrupt.status_code == 400
    assert "Image validation failed" in res_corrupt.json()["detail"]

    # 3. Sub-64x64 image
    tiny_img = Image.new("RGB", (32, 32), color="red")
    buf = io.BytesIO()
    tiny_img.save(buf, format="PNG")
    tiny_bytes = buf.getvalue()

    tiny_files = {"file": ("tiny.png", tiny_bytes, "image/png")}
    res_tiny = client.post("/api/v1/assets/register-async", headers=headers, files=tiny_files, data=data_valid)
    assert res_tiny.status_code == 400
    assert "too small" in res_tiny.json()["detail"]


def test_worker_handles_missing_user(db: Session, test_user: User, sample_image_bytes):
    """Verify background worker marks job as FAILED when user is missing."""
    from conftest import TestingSessionLocal
    job = create_job(db, user_id=test_user.id, title="Orphan Job")
    assert job.status == "PENDING"

    # Invoke worker with non-existent user_id
    run_async_registration_worker(
        job_id=job.id,
        user_id="00000000-0000-0000-0000-000000000000",
        file_bytes=sample_image_bytes,
        filename="test.png",
        title="Orphan Job",
        ownership_declaration="Declaration text",
        algorithm="dct_svd",
        alpha=0.10,
        session_factory=TestingSessionLocal,
    )

    db.expire_all()
    job_db = db.query(AsyncJob).filter(AsyncJob.id == job.id).first()
    assert job_db.status == "FAILED"
    assert job_db.progress == 0
    assert "User account not found" in (job_db.error_message or "")
    assert job_db.completed_at is not None


def test_worker_handles_unexpected_exception(db: Session, test_user: User, sample_image_bytes):
    """Verify background worker marks job as FAILED on unexpected exception."""
    from conftest import TestingSessionLocal
    job = create_job(db, user_id=test_user.id, title="Failing Job")

    with patch("app.services.job_service.register_asset") as mock_reg:
        mock_reg.side_effect = RuntimeError("Simulated internal worker crash")

        run_async_registration_worker(
            job_id=job.id,
            user_id=test_user.id,
            file_bytes=sample_image_bytes,
            filename="test.png",
            title="Failing Job",
            ownership_declaration="Declaration text",
            algorithm="dct_svd",
            alpha=0.10,
            session_factory=TestingSessionLocal,
        )

    db.expire_all()
    job_db = db.query(AsyncJob).filter(AsyncJob.id == job.id).first()
    assert job_db.status == "FAILED"
    assert job_db.progress == 0
    assert "unexpected internal error" in (job_db.error_message or "")
    assert job_db.completed_at is not None


def test_presigned_download_redirect(client, test_user_token, sample_image_bytes, db: Session):
    """Verify GET /api/v1/assets/{asset_id}/download/watermarked?presigned=true redirects."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    files = {"file": ("presigned_art.png", sample_image_bytes, "image/png")}
    data = {
        "title": "Presigned Download Art",
        "ownership_declaration": "Legal ownership declaration by user.",
        "algorithm": "dct_svd",
        "alpha": 0.10,
    }

    # Register asset synchronously first
    reg_res = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
    assert reg_res.status_code == 201
    asset_id = reg_res.json()["asset_id"]

    # Mock storage.get_presigned_url to return a mock S3 URL
    mock_url = "https://mock-bucket.s3.amazonaws.com/assets/watermarked.png?presigned=true"
    with patch("storage.base.StorageProvider.get_presigned_url", return_value=mock_url):
        with patch("storage.local.LocalStorageProvider.get_presigned_url", return_value=mock_url):
            # Test client download without following redirects
            resp = client.get(
                f"/api/v1/assets/{asset_id}/download/watermarked?presigned=true",
                headers=headers,
                follow_redirects=False,
            )
            assert resp.status_code == 307
            assert resp.headers["location"] == mock_url
