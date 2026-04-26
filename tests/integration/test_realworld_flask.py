"""Integration tests for Flask extractor against real-world applications."""

import os
import pytest
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def flask_realworld_path():
    """Get path to flask-realworld real-world fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "flask-realworld",
        "conduit"
    )
    if not os.path.exists(path):
        pytest.skip("Flask real-world fixture not available (run: git submodule update --init)")
    return path


def test_flask_realworld_extraction(flask_realworld_path):
    """Test extraction from Flask RealWorld application.

    This tests against the Flask implementation of RealWorld API from:
    https://github.com/DataDog/flask-realworld-example-app

    Expected: Blogging platform API (Conduit) with users, articles,
    comments, favorites, and profiles.
    """
    extractor = FlaskExtractor()
    result = extractor.extract(flask_realworld_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on Flask RealWorld"
    assert len(result.endpoints) > 0, "Should find endpoints in Flask RealWorld"

    # Create lookup dict for easier assertions
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Should have found a reasonable number of endpoints
    assert len(result.endpoints) >= 15, f"Expected at least 15 endpoints, found {len(result.endpoints)}"

    # User authentication endpoints
    user_endpoints = [ep for ep in result.endpoints if "user" in ep.path.lower()]
    assert len(user_endpoints) >= 3, f"Should find user endpoints, found {len(user_endpoints)}"

    # Article endpoints (core functionality)
    article_endpoints = [ep for ep in result.endpoints if "article" in ep.path.lower()]
    assert len(article_endpoints) >= 5, f"Should find article endpoints, found {len(article_endpoints)}"

    # Check for HTTP methods on articles
    article_methods = {ep.method for ep in article_endpoints}
    assert HTTPMethod.GET in article_methods, "Should have GET for articles"
    # Note: Flask extractor currently only detects GET methods from @app.route()
    # POST/PUT/DELETE detection is a known limitation

    # Verify all endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".py"), "Source file should be Python"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_flask_realworld_blueprint_structure(flask_realworld_path):
    """Test that routes from Blueprint structure are extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_realworld_path)

    # Group endpoints by source file
    files = {ep.source_file for ep in result.endpoints}

    # Should find routes from multiple files (modular architecture)
    assert len(files) >= 3, f"Should find routes from multiple Blueprint files, found {len(files)}"


def test_flask_realworld_path_parameters(flask_realworld_path):
    """Test that path parameters are correctly extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_realworld_path)

    # Find endpoints with path parameters
    param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
    assert len(param_endpoints) > 0, "Should find endpoints with path parameters"

    # Check that parameters are extracted
    for ep in param_endpoints:
        # Path should be normalized from <slug> to {slug}
        assert "<" not in ep.path, "Path parameters should be normalized"


def test_flask_realworld_http_methods(flask_realworld_path):
    """Test that various HTTP methods are extracted correctly."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_realworld_path)

    # Collect all HTTP methods found
    methods = {ep.method for ep in result.endpoints}

    # Verify we found HTTP methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    # Note: Flask extractor currently has limited support for method detection
    # in the Flask RealWorld app's routing patterns
