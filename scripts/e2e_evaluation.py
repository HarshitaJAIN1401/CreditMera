#!/usr/bin/env python3
"""CreditMera Phase 9: Automated End-to-End (E2E) System Evaluation Suite.

Validates the deployed or locally running application stack through its public HTTP API:
1. Liveness and readiness probes (/health, /health/ready).
2. User account creation and JWT authentication (/api/v1/auth/*).
3. Synchronous image registration with DCT-SVD watermarking and receipt generation.
4. Asynchronous image registration (/api/v1/assets/register-async) and background job polling.
5. Watermarked image retrieval and download integrity.
6. Blind watermark extraction and forensic ownership verification (/api/v1/verify -> MATCHED).
7. Standalone public registration receipt verification (/api/v1/assets/receipts/verify -> VALID).
8. Negative test cases: unwatermarked image rejection, tampered image robustness handling,
   and multi-tenant authorization isolation (403/404).
"""
import sys
import io
import time
import uuid
import argparse
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image

try:
    import httpx
except ImportError:
    print("Error: 'httpx' is required to run e2e_evaluation.py. Install via: pip install httpx")
    sys.exit(1)


def generate_synthetic_image(width: int = 128, height: int = 128, seed: int = 42) -> bytes:
    """Generate a reproducible, clean RGB image for testing."""
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    r = (np.sin(xx * 10) * 127 + 128).astype(np.uint8)
    g = (np.cos(yy * 10) * 127 + 128).astype(np.uint8)
    b = ((xx + yy) * 127).astype(np.uint8)
    img_array = np.stack([r, g, b], axis=-1)

    img = Image.fromarray(img_array, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def tamper_image(image_bytes: bytes) -> bytes:
    """Apply severe pseudo-random noise tampering to test rejection/inconclusive detection."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.array(img).astype(np.float32)
    # Add aggressive noise
    rng = np.random.default_rng(999)
    noise = rng.normal(0, 80, arr.shape)
    tampered_arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(tampered_arr).save(buf, format="PNG")
    return buf.getvalue()


class E2EEvaluationRunner:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        self.passed_count = 0
        self.total_count = 0

    def record_result(self, name: str, success: bool, details: str = ""):
        self.total_count += 1
        if success:
            self.passed_count += 1
            print(f"  [PASS] {name} {details}")
        else:
            print(f"  [FAIL] {name} - {details}")
            raise AssertionError(f"Step failed: {name} ({details})")

    def run_all(self):
        print("=" * 75)
        print("CREDITMERA END-TO-END (E2E) SYSTEM EVALUATION")
        print(f"Target Base URL: {self.base_url}")
        print(f"Timeout: {self.timeout}s")
        print("=" * 75)

        start_time = time.time()
        try:
            self.test_health_probes()
            user_a_token, user_a_id = self.test_user_auth("creator_a")
            user_b_token, user_b_id = self.test_user_auth("creator_b")
            sync_asset = self.test_sync_registration(user_a_token)
            async_asset = self.test_async_registration_and_polling(user_a_token)
            wm_bytes = self.test_image_download(user_a_token, sync_asset["asset_id"])
            self.test_watermark_verification(user_a_token, sync_asset["asset_id"], wm_bytes)
            self.test_public_receipt_verification(sync_asset["receipt"])
            self.test_negative_unwatermarked_image()
            self.test_negative_tampered_image(wm_bytes)
            self.test_tenant_isolation(user_a_token, user_b_token, sync_asset["asset_id"], async_asset["job_id"])

            elapsed = time.time() - start_time
            print("=" * 75)
            print(f"E2E EVALUATION COMPLETED: {self.passed_count}/{self.total_count} CHECKS PASSED in {elapsed:.2f}s")
            print("System is healthy, compliant, and verified end-to-end.")
            print("=" * 75)
            return True

        except Exception as e:
            elapsed = time.time() - start_time
            print("=" * 75)
            print(f"E2E EVALUATION FAILED: {self.passed_count}/{self.total_count} passed after {elapsed:.2f}s")
            print(f"Error: {e}")
            print("=" * 75)
            return False

    def test_health_probes(self):
        print("\n1. Testing System Health & Readiness Probes...")
        r_health = self.client.get("/health")
        self.record_result(
            "Liveness Probe (/health)",
            r_health.status_code == 200 and r_health.json().get("status") == "healthy",
            f"Status={r_health.status_code}, env={r_health.json().get('environment')}"
        )

        r_ready = self.client.get("/health/ready")
        data_ready = r_ready.json()
        self.record_result(
            "Readiness Probe (/health/ready)",
            r_ready.status_code == 200 and data_ready.get("status") == "ready" and data_ready.get("database") == "connected",
            f"Status={r_ready.status_code}, db={data_ready.get('database')}, storage={data_ready.get('storage')}"
        )

    def test_user_auth(self, prefix: str) -> Tuple[str, str]:
        print(f"\n2. Testing User Lifecycle for '{prefix}'...")
        uid = uuid.uuid4().hex[:8]
        email = f"e2e_{prefix}_{uid}@creditmera-test.internal"
        password = "E2E_SecurePassword123!"
        full_name = f"E2E Test User {prefix.upper()}"

        # Register
        r_reg = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name,
        })
        self.record_result(
            f"User Registration ({prefix})",
            r_reg.status_code == 201,
            f"Created user_id={r_reg.json().get('id')}"
        )
        user_id = r_reg.json().get("id")

        # Login
        r_login = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password,
        })
        self.record_result(
            f"JWT Authentication ({prefix})",
            r_login.status_code == 200 and "access_token" in r_login.json(),
            f"Received bearer token type={r_login.json().get('token_type')}"
        )
        token = r_login.json()["access_token"]

        # Current user profile
        r_me = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.record_result(
            f"Authenticated Profile Query ({prefix})",
            r_me.status_code == 200 and r_me.json().get("email") == email,
            f"Confirmed user email={email}"
        )

        return token, user_id

    def test_sync_registration(self, token: str) -> Dict[str, Any]:
        print("\n3. Testing Synchronous Asset Registration...")
        img_bytes = generate_synthetic_image(128, 128, seed=101)
        files = {"file": ("masterpiece.png", img_bytes, "image/png")}
        data = {
            "title": "E2E Masterpiece Artwork",
            "ownership_declaration": "I am the original creator holding all legal rights to this work.",
            "algorithm": "dct_svd",
            "alpha": "0.10",
        }
        headers = {"Authorization": f"Bearer {token}"}

        r = self.client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        res = r.json()

        self.record_result(
            "Synchronous Registration (HTTP 201)",
            r.status_code == 201 and "asset_id" in res and "receipt" in res,
            f"Assigned 40-bit asset_id={res.get('asset_id')}"
        )

        asset_id = res["asset_id"]
        self.record_result(
            "40-Bit Asset ID Bounds Verification",
            1 <= asset_id <= 0xFFFFFFFFFF,
            f"asset_id={asset_id} is within [1, 2^40 - 1]"
        )

        metrics = res.get("metrics", {})
        self.record_result(
            "Embedding Perceptual Metrics (PSNR/SSIM)",
            metrics.get("psnr_db", 0) > 30.0 and metrics.get("ssim", 0) > 0.90,
            f"PSNR={metrics.get('psnr_db')} dB, SSIM={metrics.get('ssim')}"
        )

        return res

    def test_async_registration_and_polling(self, token: str) -> Dict[str, Any]:
        print("\n4. Testing Asynchronous Asset Registration & Background Job Polling...")
        img_bytes = generate_synthetic_image(128, 128, seed=202)
        files = {"file": ("async_artwork.png", img_bytes, "image/png")}
        data = {
            "title": "E2E Background Processed Asset",
            "ownership_declaration": "Asynchronous submission ownership declaration.",
            "algorithm": "dct_svd",
            "alpha": "0.10",
        }
        headers = {"Authorization": f"Bearer {token}"}

        r_sub = self.client.post("/api/v1/assets/register-async", headers=headers, files=files, data=data)
        res_sub = r_sub.json()

        self.record_result(
            "Async Submission (HTTP 202 Accepted)",
            r_sub.status_code == 202 and "job_id" in res_sub and "poll_url" in res_sub,
            f"job_id={res_sub.get('job_id')}, poll_url={res_sub.get('poll_url')}"
        )
        job_id = res_sub["job_id"]

        # Poll job status with timeout
        poll_start = time.time()
        final_job = None
        while time.time() - poll_start < 15.0:
            r_poll = self.client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            if r_poll.status_code == 200:
                job_data = r_poll.json()
                status = job_data.get("status")
                if status in ("COMPLETED", "FAILED"):
                    final_job = job_data
                    break
            time.sleep(0.4)

        self.record_result(
            "Background Job Completion",
            final_job is not None and final_job.get("status") == "COMPLETED",
            f"Completed in {time.time() - poll_start:.2f}s with progress={final_job.get('progress') if final_job else 'none'}%"
        )

        return final_job

    def test_image_download(self, token: str, asset_id: int) -> bytes:
        print("\n5. Testing Watermarked Image Download & Presigned Parameters...")
        headers = {"Authorization": f"Bearer {token}"}

        # Direct download
        r_dl = self.client.get(f"/api/v1/assets/{asset_id}/download/watermarked", headers=headers)
        self.record_result(
            "Watermarked Image Direct Download",
            r_dl.status_code == 200 and r_dl.content.startswith(b"\x89PNG"),
            f"Received {len(r_dl.content)} bytes of PNG data"
        )

        # Download with presigned=true parameter (gracefully handled on both local and S3 backends)
        r_pre = self.client.get(
            f"/api/v1/assets/{asset_id}/download/watermarked?presigned=true",
            headers=headers,
            follow_redirects=True,
        )
        self.record_result(
            "Presigned Download Handling",
            r_pre.status_code == 200 and len(r_pre.content) > 0,
            f"Status={r_pre.status_code}, content_length={len(r_pre.content)}"
        )

        return r_dl.content

    def test_watermark_verification(self, token: str, asset_id: int, wm_bytes: bytes):
        print("\n6. Testing Blind Watermark Extraction & Forensic Verification...")
        files = {"file": ("suspect.png", wm_bytes, "image/png")}
        data = {
            "algorithm": "dct_svd",
            "alpha": "0.10",
        }
        headers = {"Authorization": f"Bearer {token}"}

        r_ver = self.client.post("/api/v1/verify", headers=headers, files=files, data=data)
        res = r_ver.json()
        ver_status = res.get("status")

        self.record_result(
            "Watermark Verification (HTTP 200)",
            r_ver.status_code == 200,
            f"Response received: status={ver_status}"
        )

        self.record_result(
            "Ownership MATCHED Outcome Decision",
            ver_status == "MATCHED",
            f"Verified status='{ver_status}', matched asset_id={res.get('asset_id')}"
        )

        owner_info = res.get("ownership_status") or {}
        diag = res.get("diagnostics") or {}
        self.record_result(
            "Authentication & Integrity State",
            diag.get("hmac_passed") is True and owner_info.get("is_owner") is True,
            f"is_owner={owner_info.get('is_owner')}, integrity_status={res.get('integrity_status')}"
        )

    def test_public_receipt_verification(self, receipt: Dict[str, Any]):
        print("\n7. Testing Standalone Public Receipt Verification...")
        payload = receipt["receipt_payload"]
        sig = receipt["receipt_signature"]

        # Call public endpoint without authorization header
        r_rcpt = self.client.post("/api/v1/assets/receipts/verify", json={
            "receipt_payload": payload,
            "receipt_signature": sig,
        })
        res = r_rcpt.json()

        self.record_result(
            "Public Receipt Verification Endpoint",
            r_rcpt.status_code == 200 and res.get("is_authentic") is True,
            f"Receipt status={res.get('status')}, asset_id={res.get('asset_id')}"
        )

        self.record_result(
            "Cryptographic Signature & Database Matching",
            res.get("signature_valid") is True and res.get("database_match") is True,
            "HMAC-SHA256 signature mathematically verified and matched on-chain record"
        )

    def test_negative_unwatermarked_image(self):
        print("\n8. Testing Negative Case: Clean Unwatermarked Image...")
        clean_bytes = generate_synthetic_image(128, 128, seed=777)
        files = {"file": ("clean.png", clean_bytes, "image/png")}
        data = {"algorithm": "dct_svd", "alpha": "0.10"}

        r = self.client.post("/api/v1/verify", files=files, data=data)
        res = r.json()
        ver_status = res.get("status")

        self.record_result(
            "Unwatermarked Image Rejection",
            r.status_code == 200 and ver_status == "NOT_DETECTED",
            f"Outcome correctly identified as '{ver_status}'"
        )

    def test_negative_tampered_image(self, wm_bytes: bytes):
        print("\n9. Testing Negative Case: Tampered & Degraded Watermark...")
        tampered_bytes = tamper_image(wm_bytes)
        files = {"file": ("tampered.png", tampered_bytes, "image/png")}
        data = {"algorithm": "dct_svd", "alpha": "0.10"}

        r = self.client.post("/api/v1/verify", files=files, data=data)
        res = r.json()
        ver_status = res.get("status")

        # Per specifications: degraded/tampered noise may yield INVALID_WATERMARK, INCONCLUSIVE, or NOT_DETECTED
        self.record_result(
            "Tampered Image Rejection / Inconclusive Detection",
            r.status_code == 200 and ver_status in ("INVALID_WATERMARK", "INCONCLUSIVE", "NOT_DETECTED"),
            f"Tampered outcome correctly assessed as '{ver_status}'"
        )

    def test_tenant_isolation(self, token_a: str, token_b: str, asset_id_a: int, job_id_a: str):
        print("\n10. Testing Tenant Privacy & Access Authorization Isolation...")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B requests User A's private receipt -> 403 Forbidden
        r_rcpt = self.client.get(f"/api/v1/assets/{asset_id_a}/receipt", headers=headers_b)
        self.record_result(
            "Cross-User Receipt Access Isolation (HTTP 403)",
            r_rcpt.status_code == 403,
            f"User B correctly denied access: status={r_rcpt.status_code}"
        )

        # User B requests User A's private download -> 403 Forbidden
        r_dl = self.client.get(f"/api/v1/assets/{asset_id_a}/download/watermarked", headers=headers_b)
        self.record_result(
            "Cross-User Image Download Isolation (HTTP 403)",
            r_dl.status_code == 403,
            f"User B correctly denied download: status={r_dl.status_code}"
        )

        # User B polls User A's background job -> 404 Not Found (zero enumeration leakage)
        r_job = self.client.get(f"/api/v1/jobs/{job_id_a}", headers=headers_b)
        self.record_result(
            "Cross-User Job Enumeration Isolation (HTTP 404)",
            r_job.status_code == 404,
            f"User B cannot view or discover User A's job: status={r_job.status_code}"
        )


def main():
    parser = argparse.ArgumentParser(description="CreditMera End-to-End System Evaluation Suite")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Root URL of running backend or reverse proxy")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds")
    args = parser.parse_args()

    runner = E2EEvaluationRunner(base_url=args.base_url, timeout=args.timeout)
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
