"""Integration tests for Express extractor against real-world applications."""

import os
import pytest
from api_extractor.extractors.javascript.express import ExpressExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def express_examples_path():
    """Get path to express-examples real-world fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "express-examples"
    )
    if not os.path.exists(path):
        pytest.skip("Express examples fixture not available (run: git submodule update --init)")
    return path


def test_express_examples_extraction(express_examples_path):
    """Test extraction from official Express examples.

    This tests against the official Express.js examples from:
    https://github.com/expressjs/express (examples directory)

    Expected: Various routing patterns, middleware examples, REST API patterns.
    """
    extractor = ExpressExtractor()
    result = extractor.extract(express_examples_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on Express examples"
    assert len(result.endpoints) > 0, "Should find endpoints in Express examples"

    # Should have found endpoints from multiple examples
    assert len(result.endpoints) >= 10, f"Expected at least 10 endpoints, found {len(result.endpoints)}"

    # Verify all endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".js") or endpoint.source_file.endswith(".ts"), \
            "Source file should be JavaScript or TypeScript"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_express_examples_routing_patterns(express_examples_path):
    """Test that various routing patterns are extracted."""
    extractor = ExpressExtractor()
    result = extractor.extract(express_examples_path)

    # Group endpoints by source file
    files = {ep.source_file for ep in result.endpoints}

    # Should find routes from multiple example files
    assert len(files) >= 3, f"Should find routes from multiple files, found {len(files)}"


def test_express_examples_path_parameters(express_examples_path):
    """Test that path parameters are correctly extracted."""
    extractor = ExpressExtractor()
    result = extractor.extract(express_examples_path)

    # Find endpoints with path parameters
    param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]

    # Check that parameters are extracted (might be 0 in some examples)
    for ep in param_endpoints:
        # Path should be normalized from :id to {id}
        assert ":" not in ep.path, "Path parameters should be normalized"


def test_express_examples_http_methods(express_examples_path):
    """Test that various HTTP methods are extracted correctly."""
    extractor = ExpressExtractor()
    result = extractor.extract(express_examples_path)

    # Collect all HTTP methods found
    methods = {ep.method for ep in result.endpoints}

    # Verify we found GET at minimum (most common)
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    # Other methods are optional depending on examples


def test_express_examples_router_usage(express_examples_path):
    """Test that Router-based routes are extracted."""
    extractor = ExpressExtractor()
    result = extractor.extract(express_examples_path)

    # Check that we extracted endpoints (which may use routers)
    assert len(result.endpoints) > 0, "Should extract endpoints from router patterns"

    # Group by methods to verify variety
    methods = {ep.method for ep in result.endpoints}
    assert len(methods) >= 1, "Should find at least one HTTP method"
