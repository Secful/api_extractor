"""Tests for Fastify extractor."""

import os
import pytest
from pathlib import Path
from api_extractor.extractors.javascript.fastify import FastifyExtractor
from api_extractor.core.models import HTTPMethod


def test_fastify_extractor():
    """Test Fastify route extraction."""
    # Get fixture path
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "javascript" / "sample_fastify.js")

    # Extract routes
    extractor = FastifyExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Check that we found endpoints
    assert result.success
    assert len(result.endpoints) > 0

    # Check specific endpoints
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Check root endpoint
    assert ("/", HTTPMethod.GET) in paths
    root_ep = paths[("/", HTTPMethod.GET)]
    # Note: May extract from multiple .js files in the directory
    assert root_ep.source_file.endswith(".js")

    # Check user endpoint with path parameter (normalized to OpenAPI format)
    assert ("/users/{userId}", HTTPMethod.GET) in paths
    user_ep = paths[("/users/{userId}", HTTPMethod.GET)]
    assert user_ep.method == HTTPMethod.GET

    # Check POST endpoint
    assert ("/users", HTTPMethod.POST) in paths

    # Check items endpoint
    assert ("/items", HTTPMethod.GET) in paths

    # Check products endpoints
    assert ("/products", HTTPMethod.POST) in paths
    assert ("/products/{productId}", HTTPMethod.GET) in paths
    assert ("/products/{productId}", HTTPMethod.PUT) in paths
    assert ("/products/{productId}", HTTPMethod.DELETE) in paths


def test_fastify_extractor_no_routes():
    """Test extraction from file with no routes."""
    extractor = FastifyExtractor()

    # Create a temporary file with no routes
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("// No routes here\nconsole.log('hello');\n")

        result = extractor.extract(tmpdir)
        assert not result.success
        assert len(result.endpoints) == 0


def test_fastify_path_parameter_extraction():
    """Test path parameter extraction."""
    extractor = FastifyExtractor()

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


def test_fastify_path_normalization():
    """Test path normalization."""
    extractor = FastifyExtractor()

    # Fastify uses :param syntax, normalize to {param}
    assert extractor._normalize_path("/users/:id") == "/users/{id}"
    assert extractor._normalize_path("/users/:userId/posts/:postId") == "/users/{userId}/posts/{postId}"
    assert extractor._normalize_path("/api/:version/products") == "/api/{version}/products"
