"""Unit tests for CreditMera health and configuration endpoints.
"""
import pytest
from fastapi import status


@pytest.mark.unit
def test_health_check_endpoint(client):
    """Test that /health returns 200 OK and expected system metadata."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "CreditMera"
    assert "version" in data
    assert "environment" in data
    assert "algorithm_version" in data


@pytest.mark.unit
def test_root_endpoint(client):
    """Test that root endpoint returns documentation and health links."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


@pytest.mark.unit
def test_openapi_schema(client):
    """Test that OpenAPI schema is properly generated."""
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert schema["info"]["title"] == "CreditMera API"
    assert "/health" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/api/v1/assets/register" in schema["paths"]
    assert "/api/v1/assets/receipts/verify" in schema["paths"]


@pytest.mark.unit
def test_readiness_check_healthy(client):
    """Test that /health/ready returns 200 OK when database and storage are available."""
    response = client.get("/health/ready")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert data["storage"] == "available"
    assert "storage_backend" in data

    # Verify no credentials or filesystem paths are leaked
    for val in data.values():
        val_str = str(val).lower()
        assert "password" not in val_str
        assert "postgresql://" not in val_str
        assert "c:\\" not in val_str
        assert "/app/" not in val_str


@pytest.mark.unit
def test_readiness_check_db_failure(client, monkeypatch):
    """Test that /health/ready returns 503 when database connectivity fails."""
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    mock_session.execute.side_effect = RuntimeError("Database unreachable")

    # Patch SessionLocal to fail on execute
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: mock_session)

    response = client.get("/health/ready")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["database"] == "disconnected"


@pytest.mark.unit
def test_readiness_check_storage_failure(client, monkeypatch):
    """Test that /health/ready returns 503 when storage backend is unavailable."""
    from unittest.mock import MagicMock
    mock_storage = MagicMock()
    mock_storage.base_dir = MagicMock()
    mock_storage.base_dir.exists.return_value = False

    monkeypatch.setattr("storage.get_storage", lambda: mock_storage)

    response = client.get("/health/ready")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["storage"] == "unavailable"

