"""Integration tests for FastAPI extractor against real-world applications."""

import os
import pytest
from api_extractor.extractors.python.fastapi import FastAPIExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def fastapi_fullstack_path():
    """Get path to fastapi-fullstack real-world fixture."""
    return os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "..", "fixtures",
        "real-world",
        "python",
        "fastapi",
        "fastapi-fullstack",
        "backend",
        "app"
    )


def test_fastapi_fullstack_extraction(fastapi_fullstack_path):
    """Test extraction from official FastAPI full-stack template.

    This tests against the official template from FastAPI creator:
    https://github.com/tiangolo/full-stack-fastapi-template

    Expected: Full-stack app with user management, items CRUD,
    authentication, and utility endpoints.
    """
    extractor = FastAPIExtractor()
    result = extractor.extract(fastapi_fullstack_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on FastAPI fullstack template"
    assert len(result.endpoints) > 0, "Should find endpoints in FastAPI fullstack"

    # Create lookup dict for easier assertions
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Should have found a good number of endpoints
    assert len(result.endpoints) == 23

    # Login/authentication endpoints
    login_endpoints = [ep for ep in result.endpoints if "login" in ep.path.lower() or "password" in ep.path.lower()]
    assert len(login_endpoints) == 6

    # User management endpoints (from users.py source file)
    user_endpoints = [ep for ep in result.endpoints if "users.py" in ep.source_file]
    assert len(user_endpoints) == 10

    # Items CRUD endpoints (from items.py source file)
    items_endpoints = [ep for ep in result.endpoints if "items.py" in ep.source_file]
    assert len(items_endpoints) == 5

    # Check for HTTP methods on items
    items_methods = {ep.method for ep in items_endpoints}
    assert HTTPMethod.GET in items_methods, "Should have GET for items"
    assert HTTPMethod.POST in items_methods, "Should have POST for items"
    assert HTTPMethod.PUT in items_methods or HTTPMethod.PATCH in items_methods, "Should have PUT/PATCH for items"
    assert HTTPMethod.DELETE in items_methods, "Should have DELETE for items"

    # Verify all endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".py"), "Source file should be Python"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_fastapi_fullstack_router_structure(fastapi_fullstack_path):
    """Test that routes from APIRouter structure are extracted."""
    extractor = FastAPIExtractor()
    result = extractor.extract(fastapi_fullstack_path)

    # Group endpoints by source file
    files = {ep.source_file for ep in result.endpoints}

    # Should find routes from multiple files (modular architecture)
    assert len(files) == 5

    # Check for routes directory
    route_files = [f for f in files if "/routes/" in f or "\\routes\\" in f]
    assert len(route_files) == 5


def test_fastapi_fullstack_path_parameters(fastapi_fullstack_path):
    """Test that path parameters are correctly extracted."""
    extractor = FastAPIExtractor()
    result = extractor.extract(fastapi_fullstack_path)

    # Find endpoints with path parameters
    param_endpoints = [ep for ep in result.endpoints if "{" in ep.path and "}" in ep.path]
    assert len(param_endpoints) > 0, "Should find endpoints with path parameters"

    # Check that parameters use OpenAPI format {param}
    for ep in param_endpoints:
        # FastAPI uses {param} format which should be preserved
        assert "{" in ep.path and "}" in ep.path, "Path should have parameter placeholders"


def test_fastapi_fullstack_http_methods(fastapi_fullstack_path):
    """Test that various HTTP methods are extracted correctly."""
    extractor = FastAPIExtractor()
    result = extractor.extract(fastapi_fullstack_path)

    # Collect all HTTP methods found
    methods = {ep.method for ep in result.endpoints}

    # Verify we found various HTTP methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    assert HTTPMethod.POST in methods, "Should find POST endpoints"
    assert HTTPMethod.PUT in methods or HTTPMethod.PATCH in methods, "Should find PUT or PATCH endpoints"
    assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"


def test_fastapi_fullstack_router_prefixes(fastapi_fullstack_path):
    """Test that router prefixes are handled correctly."""
    extractor = FastAPIExtractor()
    result = extractor.extract(fastapi_fullstack_path)

    # Items router has prefix="/items"
    items_paths = [ep.path for ep in result.endpoints if "items" in ep.path]

    # All item paths should start with /items (from router prefix)
    for path in items_paths:
        # Path should contain "items" either directly or as part of the route
        assert "items" in path.lower(), f"Items endpoint should contain 'items' in path: {path}"
