"""Integration tests for HTTP API endpoints."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api_extractor.server import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def minimal_fastapi_path():
    """Path to minimal FastAPI fixture."""
    return str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python")


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_info_endpoint(client):
    """Test service info endpoint."""
    response = client.get("/api/v1/info")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "supported_frameworks" in data
    assert "features" in data
    assert isinstance(data["supported_frameworks"], list)
    assert len(data["supported_frameworks"]) > 0
    assert "fastapi" in data["supported_frameworks"]


def test_analyze_endpoint_success(client, minimal_fastapi_path):
    """Test successful analysis through API."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "path": minimal_fastapi_path,
            "title": "Test API",
            "version": "1.0.0",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["openapi_spec"] is not None
    assert data["endpoints_count"] > 0
    assert len(data["frameworks_detected"]) > 0  # At least one framework detected
    assert isinstance(data["errors"], list)
    assert isinstance(data["warnings"], list)


def test_analyze_endpoint_auto_detection(client, minimal_fastapi_path):
    """Test analysis with automatic framework detection."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "path": minimal_fastapi_path,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["frameworks_detected"]) > 0


def test_analyze_endpoint_invalid_path(client):
    """Test analysis with invalid path."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "path": "/nonexistent/path",
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_analyze_endpoint_path_traversal_blocked(client):
    """Test that path traversal is blocked."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "path": "../../etc/passwd",
        },
    )

    assert response.status_code == 403
    assert "traversal" in response.json()["detail"].lower()


def test_analyze_endpoint_system_directory_blocked(client):
    """Test that system directories are blocked."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "path": "/etc",
        },
    )

    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower()


def test_analyze_endpoint_missing_path(client):
    """Test analysis without path parameter."""
    response = client.post(
        "/api/v1/analyze",
        json={},
    )

    assert response.status_code == 422  # Validation error


def test_analyze_endpoint_with_description(client, minimal_fastapi_path):
    """Test analysis with API description."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "path": minimal_fastapi_path,
            "title": "My API",
            "version": "2.0.0",
            "description": "This is my test API",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_analyze_endpoint_empty_directory(client, tmp_path):
    """Test analysis with empty directory."""
    response = client.post(
        "/api/v1/analyze",
        json={
            "path": str(tmp_path),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert len(data["errors"]) > 0


def test_openapi_docs_accessible(client):
    """Test that OpenAPI documentation is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200

    response = client.get("/redoc")
    assert response.status_code == 200

    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
