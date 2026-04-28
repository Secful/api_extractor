"""Integration tests for Flask extractor with Flask RealWorld Example App."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.flask import FlaskExtractor


@pytest.fixture
def flask_realworld_path():
    """Get path to Flask RealWorld Example App fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "python",
        "flask",
        "flask-realworld-example-app",
    )
    if not os.path.exists(path):
        pytest.skip("Flask RealWorld fixture not available (run: git submodule update --init)")
    return path


class TestFlaskRealWorld:
    """Integration tests for Flask RealWorld Example App (gothinkster)."""

    def test_extraction(self, flask_realworld_path: str) -> None:
        """Test extraction from Flask RealWorld Example App.

        Repository: https://github.com/gothinkster/flask-realworld-example-app
        Domain: Social blogging platform (Medium clone per RealWorld spec)
        """
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count range (19 expected)
        assert 17 <= len(result.endpoints) <= 21, \
            f"Expected 17-21 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, flask_realworld_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_path_parameters(self, flask_realworld_path: str) -> None:
        """Test that path parameters are properly extracted and normalized."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) >= 8, \
            f"Should find at least 8 endpoints with path parameters, found {len(param_endpoints)}"

        # Check for slug-based paths
        slug_paths = [ep for ep in result.endpoints if "{slug}" in ep.path]
        assert len(slug_paths) >= 5, \
            f"Should find at least 5 slug-based paths, found {len(slug_paths)}"

    def test_source_tracking(self, flask_realworld_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".py")
            assert ep.source_line is not None
            assert ep.source_line > 0

    def test_blueprint_prefixes(self, flask_realworld_path: str) -> None:
        """Test that Blueprint URL prefixes are applied."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # All RealWorld API paths should start with /api
        api_paths = [p for p in paths if p.startswith("/api")]
        assert len(api_paths) >= 10, \
            f"Most paths should start with /api, found {len(api_paths)}"

        # Should have 12 unique paths (19 endpoints with different methods)
        assert len(paths) == 12, \
            f"Expected 12 unique paths, found {len(paths)}"

    def test_specific_endpoints(self, flask_realworld_path: str) -> None:
        """Test that expected RealWorld endpoints are found."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Core authentication endpoints
        assert "/api/users" in paths or any("users" in p for p in paths), \
            "Should find user registration endpoint"
        assert any("login" in p for p in paths), \
            "Should find login endpoint"

        # Article endpoints
        assert any("articles" in p for p in paths), \
            "Should find article endpoints"

        # Tag endpoint
        assert any("tags" in p for p in paths), \
            "Should find tags endpoint"

    def test_nested_resources(self, flask_realworld_path: str) -> None:
        """Test that nested resources (articles/comments) are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for nested comment routes under articles
        comment_paths = [p for p in paths if "comment" in p.lower()]
        if len(comment_paths) > 0:
            # Should have nested structure
            nested_comments = [p for p in comment_paths if p.count("/") > 3]
            assert len(nested_comments) > 0, \
                "Comment paths should be nested under articles"

    def test_social_features(self, flask_realworld_path: str) -> None:
        """Test that social feature endpoints are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for follow/favorite patterns
        social_paths = [
            p for p in paths
            if "follow" in p.lower() or "favorite" in p.lower()
        ]

        assert len(social_paths) > 0, \
            "Should find social feature endpoints (follow/favorite)"

    def test_slug_based_urls(self, flask_realworld_path: str) -> None:
        """Test that slug-based article URLs are properly extracted."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success

        # Find endpoints that work with article slugs
        slug_endpoints = [ep for ep in result.endpoints if "{slug}" in ep.path]

        assert len(slug_endpoints) >= 5, \
            f"Should find multiple slug-based endpoints, found {len(slug_endpoints)}"

        # Verify different HTTP methods on slug endpoints
        slug_methods = {ep.method for ep in slug_endpoints}
        assert len(slug_methods) >= 3, \
            "Slug endpoints should support multiple HTTP methods"

    def test_profile_endpoints(self, flask_realworld_path: str) -> None:
        """Test that user profile endpoints are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(flask_realworld_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for profile-related endpoints
        profile_paths = [p for p in paths if "profile" in p.lower()]

        if len(profile_paths) > 0:
            assert len(profile_paths) >= 2, \
                "Should find multiple profile endpoints"
