"""Tests for NestJS extractor."""

import os
import pytest
from pathlib import Path
from api_extractor.extractors.javascript.nestjs import NestJSExtractor
from api_extractor.core.models import HTTPMethod


def test_nestjs_extractor():
    """Test NestJS route extraction."""
    # Get fixture path
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "javascript" / "sample_nestjs.ts")

    # Extract routes
    extractor = NestJSExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Check that we found endpoints
    assert result.success
    assert len(result.endpoints) > 0

    # Check specific endpoints
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Check user endpoints
    assert ("/users", HTTPMethod.GET) in paths
    user_list_ep = paths[("/users", HTTPMethod.GET)]
    assert user_list_ep.source_file.endswith("sample_nestjs.ts")

    # Check user detail endpoint with path parameter (normalized to OpenAPI format)
    assert ("/users/{id}", HTTPMethod.GET) in paths
    user_detail_ep = paths[("/users/{id}", HTTPMethod.GET)]
    assert user_detail_ep.method == HTTPMethod.GET

    # Check POST endpoint
    assert ("/users", HTTPMethod.POST) in paths

    # Check PUT endpoint
    assert ("/users/{id}", HTTPMethod.PUT) in paths

    # Check DELETE endpoint
    assert ("/users/{id}", HTTPMethod.DELETE) in paths

    # Check versioned controller endpoints
    # @Controller({ path: 'products', version: '1' })
    assert ("/v1/products", HTTPMethod.GET) in paths
    versioned_ep = paths[("/v1/products", HTTPMethod.GET)]
    assert versioned_ep.path.startswith("/v1")

    # Check nested path
    # @Controller('api/orders')
    assert ("/api/orders", HTTPMethod.GET) in paths


def test_nestjs_extractor_no_routes():
    """Test extraction from file with no routes."""
    extractor = NestJSExtractor()

    # Create a temporary file with no routes
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, "w") as f:
            f.write("// No routes here\nconsole.log('hello');\n")

        result = extractor.extract(tmpdir)
        assert not result.success
        assert len(result.endpoints) == 0


def test_nestjs_path_parameter_extraction():
    """Test path parameter extraction."""
    extractor = NestJSExtractor()

    # Test simple parameter
    params = extractor._extract_path_parameters("/users/:id")
    assert len(params) == 1
    assert params[0].name == "id"
    assert params[0].location.value == "path"
    assert params[0].required is True

    # Test multiple parameters
    params = extractor._extract_path_parameters("/users/:userId/posts/:postId")
    assert len(params) == 2
    assert params[0].name == "userId"
    assert params[1].name == "postId"

    # Test parameter in middle of path
    params = extractor._extract_path_parameters("/api/:version/users")
    assert len(params) == 1
    assert params[0].name == "version"


def test_nestjs_path_normalization():
    """Test path normalization."""
    extractor = NestJSExtractor()

    # NestJS uses :param syntax, normalize to {param}
    assert extractor._normalize_path("/users/:id") == "/users/{id}"
    assert extractor._normalize_path("/users/:userId/posts/:postId") == "/users/{userId}/posts/{postId}"
    assert extractor._normalize_path("/api/:version/products") == "/api/{version}/products"


def test_nestjs_controller_path_combination():
    """Test controller path and method path combination."""
    extractor = NestJSExtractor()

    # Base + method path
    assert extractor._combine_paths("/users", "profile") == "/users/profile"
    assert extractor._combine_paths("/users", ":id") == "/users/:id"

    # Empty method path (root)
    assert extractor._combine_paths("/users", "") == "/users"

    # Root controller
    assert extractor._combine_paths("", "health") == "/health"

    # Versioned paths
    assert extractor._combine_paths("/v1/products", ":id") == "/v1/products/:id"
