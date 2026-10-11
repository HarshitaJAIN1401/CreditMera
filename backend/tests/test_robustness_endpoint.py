"""Test suite for the robustness benchmarks endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_robustness_benchmarks_success():
    """Verify that GET /api/v1/robustness/benchmarks returns valid benchmark structure."""
    response = client.get("/api/v1/robustness/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "summary_by_algorithm" in data
    metadata = data["metadata"]
    assert "algorithms_evaluated" in metadata
    assert "dct_svd" in metadata["algorithms_evaluated"]
    assert "false_positive_rate" in metadata
    assert metadata["false_positive_rate"] == 0.0

    summary = data["summary_by_algorithm"]
    assert "dct_svd" in summary
    assert "mean_nc" in summary["dct_svd"]
    assert "mean_psnr_db" in summary["dct_svd"]


def test_get_robustness_benchmarks_fallback_handling(monkeypatch):
    """Verify fallback handling when robustness results file is not found."""
    from pathlib import Path
    from app.api.v1 import robustness

    # Point get_results_path to a nonexistent location
    monkeypatch.setattr(robustness, "get_results_path", lambda: Path("nonexistent_path/benchmarks.json"))
    response = client.get("/api/v1/robustness/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert data["metadata"]["title"] == "CreditMera Watermark Robustness Lab Evaluation"
