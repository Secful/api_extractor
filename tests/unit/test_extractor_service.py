"""Tests for ExtractionService."""

import pytest
from pathlib import Path

from api_extractor.service import ExtractionService, ExtractionServiceResult
from api_extractor.core.models import FrameworkType


@pytest.fixture
def service():
    """Create extraction service instance."""
    return ExtractionService()


@pytest.fixture
def minimal_fastapi_path():
    """Path to minimal FastAPI fixture."""
    return str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python")


def test_service_extract_fastapi_success(service, minimal_fastapi_path):
    """Test successful FastAPI extraction through service."""
    result = service.extract_api(
        path=minimal_fastapi_path,
        frameworks=[FrameworkType.FASTAPI],
        title="Test API",
        version="1.0.0",
    )

    assert isinstance(result, ExtractionServiceResult)
    assert result.success is True
    assert result.openapi_spec is not None
    assert result.endpoints_count > 0
    assert FrameworkType.FASTAPI in result.frameworks_detected
    assert result.metadata["source_path"] == minimal_fastapi_path
    assert result.metadata["is_s3"] is False


def test_service_extract_auto_detection(service, minimal_fastapi_path):
    """Test automatic framework detection."""
    result = service.extract_api(
        path=minimal_fastapi_path,
        frameworks=None,  # Auto-detect
    )

    assert result.success is True
    assert len(result.frameworks_detected) > 0
    # Detector may find multiple frameworks, just ensure it found something
    assert result.endpoints_count > 0


def test_service_extract_invalid_path(service):
    """Test extraction with invalid path."""
    result = service.extract_api(
        path="/nonexistent/path/to/code",
        frameworks=[FrameworkType.FASTAPI],
    )

    assert result.success is False
    assert len(result.errors) > 0
    assert "not found" in result.errors[0].lower() or "not a directory" in result.errors[0].lower()


def test_service_extract_no_endpoints(service, tmp_path):
    """Test extraction with directory containing no API endpoints."""
    # Create empty Python file
    test_file = tmp_path / "empty.py"
    test_file.write_text("# Empty file\n")

    result = service.extract_api(
        path=str(tmp_path),
        frameworks=[FrameworkType.FASTAPI],
    )

    assert result.success is False
    assert "No API endpoints found" in result.errors


def test_service_extract_with_description(service, minimal_fastapi_path):
    """Test extraction with API description."""
    result = service.extract_api(
        path=minimal_fastapi_path,
        frameworks=[FrameworkType.FASTAPI],
        title="Test API",
        version="2.0.0",
        description="This is a test API",
    )

    assert result.success is True
    assert result.openapi_spec is not None


def test_service_extract_multiple_frameworks(service, minimal_fastapi_path):
    """Test extraction with multiple frameworks specified."""
    result = service.extract_api(
        path=minimal_fastapi_path,
        frameworks=[FrameworkType.FASTAPI, FrameworkType.FLASK],
    )

    # Should succeed even if only one framework is found
    assert result.success is True
    assert FrameworkType.FASTAPI in result.frameworks_detected


def test_service_result_model_structure():
    """Test ExtractionServiceResult model structure."""
    result = ExtractionServiceResult(
        success=True,
        endpoints_count=5,
        frameworks_detected=[FrameworkType.FASTAPI],
        errors=["error1"],
        warnings=["warning1"],
        metadata={"key": "value"},
    )

    assert result.success is True
    assert result.endpoints_count == 5
    assert result.errors == ["error1"]
    assert result.warnings == ["warning1"]
    assert result.metadata["key"] == "value"
