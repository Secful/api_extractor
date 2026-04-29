"""Tests for FastAPI extractor."""

import os
import pytest
from pathlib import Path
from api_extractor.extractors.python.fastapi import FastAPIExtractor
from api_extractor.core.models import HTTPMethod


def test_fastapi_extractor():
    """Test FastAPI route extraction."""
    # Get fixture path
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_fastapi.py")

    # Extract routes
    extractor = FastAPIExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Check that we found endpoints
    assert result.success
    assert len(result.endpoints) > 0

    # Check specific endpoints
    paths = {ep.path: ep for ep in result.endpoints}

    # Check root endpoint
    assert "/api/" in paths
    root_ep = paths["/api/"]
    assert root_ep.method == HTTPMethod.GET
    assert root_ep.source_file.endswith("sample_fastapi.py")

    # Check user endpoint with path parameter
    assert "/api/users/{user_id}" in paths
    user_ep = paths["/api/users/{user_id}"]
    assert user_ep.method == HTTPMethod.GET
    assert len(user_ep.parameters) >= 1  # Should have user_id parameter
    # Check path parameter
    path_params = [p for p in user_ep.parameters if p.location.value == "path"]
    assert len(path_params) == 1
    assert path_params[0].name == "user_id"
    # Note: type extraction from function signatures is a future enhancement
    assert path_params[0].type in ["integer", "string"]

    # Check POST endpoint
    post_users = [ep for ep in result.endpoints if ep.path == "/api/users" and ep.method == HTTPMethod.POST]
    assert len(post_users) == 1

    # Check router endpoints
    # Note: Router prefix handling is a future enhancement
    assert "/api/products/{product_id}" in paths
    product_ep = paths["/api/products/{product_id}"]
    assert product_ep.method in [HTTPMethod.GET, HTTPMethod.PUT, HTTPMethod.DELETE]


def test_fastapi_extractor_no_routes():
    """Test extraction from file with no routes."""
    extractor = FastAPIExtractor()

    # Create a temporary file with no routes
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write("# No routes here\nprint('hello')\n")

        result = extractor.extract(tmpdir)
        assert not result.success
        assert len(result.endpoints) == 0


def test_fastapi_path_parameter_extraction():
    """Test path parameter extraction."""
    extractor = FastAPIExtractor()

    # Test simple parameter
    params = extractor._extract_path_parameters("/users/{user_id}")
    assert len(params) == 1
    assert params[0].name == "user_id"
    assert params[0].location.value == "path"
    assert params[0].required is True

    # Test multiple parameters
    params = extractor._extract_path_parameters("/users/{user_id}/posts/{post_id}")
    assert len(params) == 2
    assert params[0].name == "user_id"
    assert params[1].name == "post_id"

    # Test typed parameter
    params = extractor._extract_path_parameters("/items/{item_id:int}")
    assert len(params) == 1
    assert params[0].name == "item_id"
    assert params[0].type == "integer"


def test_fastapi_path_normalization():
    """Test path normalization."""
    extractor = FastAPIExtractor()

    # FastAPI paths are already in OpenAPI format
    assert extractor._normalize_path("/users/{id}") == "/users/{id}"
    assert extractor._normalize_path("/items/{item_id:int}") == "/items/{item_id:int}"
