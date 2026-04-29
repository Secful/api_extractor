"""Integration tests for Flask extractor against flask-realworld-example-app."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.flask import FlaskExtractor


@pytest.fixture
def flask_example_path() -> str:
    """Get path to flask-realworld-example-app fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "python",
        "flask",
        "flask-realworld-example-app",
        "conduit",
    )
    if not os.path.exists(path):
        pytest.skip("Flask realworld example fixture not available (run: git submodule update --init)")
    return path


def test_flask_example_extraction(flask_example_path: str) -> None:
    """Test extraction from flask-realworld-example-app.

    This tests against a Flask implementation of the RealWorld API from:
    https://github.com/gothinkster/flask-realworld-example-app

    Expected: Conduit blogging platform API with articles, users, comments, etc.
    """
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on flask-realworld-example-app"
    assert len(result.endpoints) > 0, "Should find endpoints"

    # Should have found a reasonable number of endpoints
    # This fixture has ~19 @blueprint.route decorators
    assert len(result.endpoints) == 19, f"Expected at least 15 endpoints, found {len(result.endpoints)}"


def test_flask_example_article_endpoints(flask_example_path: str) -> None:
    """Test that article-related endpoints are extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Article endpoints (core functionality of blogging platform)
    article_endpoints = [ep for ep in result.endpoints if "article" in ep.path.lower()]
    assert len(article_endpoints) == 11, f"Should find article endpoints, found {len(article_endpoints)}"

    # Verify we have the main articles listing endpoint
    article_list_endpoints = [ep for ep in result.endpoints if ep.path == "/api/articles"]
    assert len(article_list_endpoints) == 2, "Should have /api/articles endpoint"


def test_flask_example_user_endpoints(flask_example_path: str) -> None:
    """Test that user authentication endpoints are extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # User authentication endpoints
    user_endpoints = [ep for ep in result.endpoints if "user" in ep.path.lower()]
    assert len(user_endpoints) == 7, f"Should find user endpoints, found {len(user_endpoints)}"


def test_flask_example_comment_endpoints(flask_example_path: str) -> None:
    """Test that comment endpoints are extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Comment endpoints
    comment_endpoints = [ep for ep in result.endpoints if "comment" in ep.path.lower()]
    assert len(comment_endpoints) == 3, f"Should find comment endpoints, found {len(comment_endpoints)}"


def test_flask_example_profile_endpoints(flask_example_path: str) -> None:
    """Test that profile endpoints are extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Profile endpoints
    profile_endpoints = [ep for ep in result.endpoints if "profile" in ep.path.lower()]
    assert len(profile_endpoints) >= 2, f"Should find profile endpoints, found {len(profile_endpoints)}"


def test_flask_example_http_methods(flask_example_path: str) -> None:
    """Test that various HTTP methods are extracted correctly."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Collect all HTTP methods found
    methods = {ep.method for ep in result.endpoints}

    # Verify we found various HTTP methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    assert HTTPMethod.POST in methods, "Should find POST endpoints"
    assert HTTPMethod.PUT in methods or HTTPMethod.PATCH in methods, "Should find PUT or PATCH endpoints"
    assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"


def test_flask_example_path_parameters(flask_example_path: str) -> None:
    """Test that path parameters are correctly extracted and normalized."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Find endpoints with path parameters
    param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
    assert len(param_endpoints) > 0, "Should find endpoints with path parameters"

    # Check that parameters are normalized from <param> to {param}
    for ep in param_endpoints:
        assert "<" not in ep.path, f"Path parameters should be normalized, got: {ep.path}"
        assert ">" not in ep.path, f"Path parameters should be normalized, got: {ep.path}"


def test_flask_example_source_file_info(flask_example_path: str) -> None:
    """Test that all endpoints have proper source file information."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Verify all endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".py"), f"Source file should be Python: {endpoint.source_file}"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_flask_example_blueprint_structure(flask_example_path: str) -> None:
    """Test that routes from Blueprint structure are extracted from multiple files."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Group endpoints by source file
    files = {ep.source_file for ep in result.endpoints}

    # Should find routes from multiple files (modular Blueprint architecture)
    # Expected files: articles/views.py, user/views.py, profile/views.py
    assert len(files) == 3, f"Should find routes from multiple Blueprint files, found {len(files)}"


def test_flask_example_favorite_endpoints(flask_example_path: str) -> None:
    """Test that article favorite/unfavorite endpoints are extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Favorite endpoints
    favorite_endpoints = [ep for ep in result.endpoints if "favorite" in ep.path.lower()]
    assert len(favorite_endpoints) == 2, f"Should find favorite endpoints, found {len(favorite_endpoints)}"


def test_flask_example_tags_endpoint(flask_example_path: str) -> None:
    """Test that tags endpoint is extracted."""
    extractor = FlaskExtractor()
    result = extractor.extract(flask_example_path)

    # Tags endpoint
    tags_endpoints = [ep for ep in result.endpoints if ep.path == "/api/tags"]
    assert len(tags_endpoints) == 1, "Should have /api/tags endpoint"