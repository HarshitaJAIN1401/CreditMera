"""Integration tests for Global Cases, Image Passport, and Visual Similarity API endpoints."""
import io
import pytest
from PIL import Image, ImageDraw
import numpy as np


def create_sample_png(color=(120, 150, 220), shape="rect") -> bytes:
    img = Image.new("RGB", (128, 128), color=color)
    draw = ImageDraw.Draw(img)
    if shape == "rect":
        draw.rectangle([30, 30, 90, 90], fill=(20, 40, 80))
    else:
        draw.ellipse([30, 30, 90, 90], fill=(220, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestCasesAndPassportAPI:

    def test_asset_registration_with_passport_metadata(self, client, test_user_token):
        """Verify registration saves category, country, license_type, and attribution."""
        headers = {"Authorization": f"Bearer {test_user_token}"}
        img_bytes = create_sample_png()
        files = {"file": ("snow_leopard.png", img_bytes, "image/png")}
        data = {
            "title": "Snow Leopard in Ladakh",
            "ownership_declaration": "Captured in Hemis National Park by photographer.",
            "category": "Wildlife",
            "country": "India",
            "license_type": "Editorial Only",
            "attribution_text": "Photo by Wildlife Specialist / CreditMera",
        }

        resp = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert resp.status_code == 201
        res = resp.json()

        assert res["title"] == "Snow Leopard in Ladakh"
        assert res["category"] == "Wildlife"
        assert res["country"] == "India"
        assert res["license_type"] == "Editorial Only"
        assert res["attribution_text"] == "Photo by Wildlife Specialist / CreditMera"
        assert res["perceptual_hash"] is not None
        assert len(res["perceptual_hash"]) == 16

        asset_id = res["asset_id"]

        # Verify get detail endpoint returns passport fields
        resp_detail = client.get(f"/api/v1/assets/{asset_id}", headers=headers)
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["category"] == "Wildlife"
        assert detail["country"] == "India"
        assert detail["license_type"] == "Editorial Only"
        assert detail["attribution_text"] == "Photo by Wildlife Specialist / CreditMera"
        assert detail["perceptual_hash"] == res["perceptual_hash"]

    def test_asset_listing_filters(self, client, test_user_token):
        """Verify listing assets supports filtering by category and country."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # Filter by category
        resp_cat = client.get("/api/v1/assets?category=Wildlife", headers=headers)
        assert resp_cat.status_code == 200
        items = resp_cat.json()
        assert all(item["category"] == "Wildlife" for item in items)

        # Filter by country
        resp_country = client.get("/api/v1/assets?country=India", headers=headers)
        assert resp_country.status_code == 200
        items_country = resp_country.json()
        assert all(item["country"] == "India" for item in items_country)

    def test_global_case_lifecycle(self, client, test_user_token):
        """Verify full lifecycle of an international misuse case."""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        # 1. Register an initial asset
        img_bytes = create_sample_png()
        files = {"file": ("reef.png", img_bytes, "image/png")}
        data = {
            "title": "Great Barrier Reef Aerial",
            "ownership_declaration": "Original aerial work.",
            "category": "Travel",
            "country": "Australia",
        }
        r_asset = client.post("/api/v1/assets/register", headers=headers, files=files, data=data)
        assert r_asset.status_code == 201
        asset_id = r_asset.json()["asset_id"]

        # 2. Open a Global Case for this asset
        susp_bytes = create_sample_png(color=(130, 160, 230))
        case_files = {"suspected_file": ("suspected_copy.png", susp_bytes, "image/png")}
        case_data = {
            "title": "Unauthorized Travel Agency Usage in Sydney",
            "asset_id": str(asset_id),
            "suspected_url": "https://example-travel.com.au/promos/reef.jpg",
            "suspected_country": "Australia",
            "match_score": "0.88",
            "watermark_status": "MATCHED",
            "evidence_notes": "Discovered on commercial booking header without attribution.",
        }
        r_case = client.post("/api/v1/cases", headers=headers, files=case_files, data=case_data)
        assert r_case.status_code == 201
        case_res = r_case.json()

        assert case_res["title"] == "Unauthorized Travel Agency Usage in Sydney"
        assert case_res["asset_id"] == asset_id
        assert case_res["status"] == "New"
        assert case_res["suspected_country"] == "Australia"
        assert case_res["case_number"].startswith("CASE-")
        case_id = case_res["id"]

        # 3. List cases
        r_list = client.get("/api/v1/cases", headers=headers)
        assert r_list.status_code == 200
        cases_list = r_list.json()
        assert any(c["id"] == case_id for c in cases_list)

        # 4. Update status to 'Evidence Collected'
        r_status = client.patch(
            f"/api/v1/cases/{case_id}/status",
            headers=headers,
            json={"status": "Evidence Collected", "note": "High-res screenshots archived."},
        )
        assert r_status.status_code == 200
        assert r_status.json()["status"] == "Evidence Collected"

        # 5. Add a communication note
        r_note = client.post(
            f"/api/v1/cases/{case_id}/notes",
            headers=headers,
            json={"note": "Sent licensing notification email to agency contact."},
        )
        assert r_note.status_code == 200
        notes_timeline = r_note.json()["timeline"]
        assert len(notes_timeline) >= 3

        # 6. Generate and download Evidence Report
        r_report = client.get(f"/api/v1/cases/{case_id}/report", headers=headers)
        assert r_report.status_code == 200
        report = r_report.json()
        assert report["report_id"].startswith("REP-")
        assert report["case"]["id"] == case_id
        assert "registered_asset_metadata" in report
        assert "technical_evidence_summary" in report
        assert "CONFIDENTIAL TECHNICAL EVIDENCE DOSSIER" in report["disclaimer"]

    def test_visual_similarity_compare_endpoint(self, client):
        """Verify POST /api/v1/similarity/compare returns multi-metric similarity analysis."""
        img_a = create_sample_png()
        img_b = create_sample_png()

        files = {
            "reference_file": ("ref.png", img_a, "image/png"),
            "suspected_file": ("susp.png", img_b, "image/png"),
        }
        resp = client.post("/api/v1/similarity/compare", files=files)
        assert resp.status_code == 200
        res = resp.json()

        assert res["composite_similarity_score"] >= 0.95
        assert res["similarity_tier"] == "EXACT_OR_NEAR_EXACT"
        assert "phash" in res["metrics"]
        assert "dhash" in res["metrics"]
        assert "ssim" in res["metrics"]
        assert "legal_disclaimer" in res
