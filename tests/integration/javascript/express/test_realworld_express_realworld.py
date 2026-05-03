"""Integration tests for Express extractor with node-express-realworld-example-app."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture
def realworld_path():
    """Get path to node-express-realworld-example-app fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "..", "fixtures",
        "real-world",
        "javascript",
        "express",
        "realworld",
    )
    if not os.path.exists(path):
        pytest.skip("RealWorld Express fixture not available (run: git submodule update --init)")
    return path


class TestExpressRealWorld:
    """Integration tests for node-express-realworld-example-app."""

    def test_extraction(self, realworld_path: str) -> None:
        """Test extraction from node-express-realworld-example-app.

        Repository: https://github.com/gothinkster/node-express-realworld-example-app
        Domain: Blogging Platform (Medium clone)
        """
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count (exact match per coding standards)
        assert len(result.endpoints) == 20, \
            f"Expected exactly 20 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, realworld_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_path_parameters(self, realworld_path: str) -> None:
        """Test that path parameters are properly extracted in OpenAPI format."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 11, \
            f"Expected exactly 11 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify OpenAPI format (not Express :param format)
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path, \
                f"Path parameter should use OpenAPI format: {ep.path}"
            assert ":" not in ep.path, \
                f"Path should not contain Express :param format: {ep.path}"

    def test_slug_based_routing(self, realworld_path: str) -> None:
        """Test that slug-based routing is properly extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        # Find endpoints using {slug} parameter
        slug_endpoints = [ep for ep in result.endpoints if "{slug}" in ep.path]
        assert len(slug_endpoints) == 8, \
            f"Expected exactly 8 endpoints with {{slug}} parameter, found {len(slug_endpoints)}"

        # Verify article slug endpoints
        paths = {ep.path for ep in result.endpoints}
        assert "/articles/{slug}" in paths, "Should find /articles/{slug}"
        assert "/articles/{slug}/comments" in paths, "Should find nested comment route"
        assert "/articles/{slug}/favorite" in paths, "Should find favorite action route"

    def test_nested_routes(self, realworld_path: str) -> None:
        """Test that nested resource routes are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        # Comments nested under articles
        comment_paths = [ep.path for ep in result.endpoints if "comments" in ep.path]
        assert len(comment_paths) == 3, \
            f"Expected exactly 3 comment endpoints, found {len(comment_paths)}"

        # Verify specific nested patterns
        paths = {ep.path for ep in result.endpoints}
        assert "/articles/{slug}/comments" in paths, "Should find list/create comments"
        assert "/articles/{slug}/comments/{id}" in paths, "Should find delete comment"

    def test_profile_endpoints(self, realworld_path: str) -> None:
        """Test that profile endpoints with username parameter are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        # Find profile endpoints
        profile_endpoints = [ep for ep in result.endpoints if "profiles" in ep.path]
        assert len(profile_endpoints) == 3, \
            f"Expected exactly 3 profile endpoints, found {len(profile_endpoints)}"

        # Verify {username} parameter
        paths = {ep.path for ep in result.endpoints}
        assert "/profiles/{username}" in paths, "Should find get profile endpoint"
        assert "/profiles/{username}/follow" in paths, "Should find follow/unfollow endpoint"

    def test_source_tracking(self, realworld_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith((".ts", ".js")), \
                f"Expected .ts or .js file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_authentication_endpoints(self, realworld_path: str) -> None:
        """Test that authentication endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        paths = {ep.path for ep in result.endpoints}

        # User registration and login
        assert "/users" in paths, "Should find user registration endpoint"
        assert "/users/login" in paths, "Should find login endpoint"
        assert "/user" in paths, "Should find get/update current user endpoint"

    def test_article_endpoints(self, realworld_path: str) -> None:
        """Test that article CRUD endpoints are extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        paths = {ep.path for ep in result.endpoints}

        # Article CRUD
        assert "/articles" in paths, "Should find list/create articles"
        assert "/articles/feed" in paths, "Should find user feed endpoint"
        assert "/articles/{slug}" in paths, "Should find get/update/delete article"

        # Article actions
        assert "/articles/{slug}/favorite" in paths, "Should find favorite/unfavorite"

    def test_tag_endpoints(self, realworld_path: str) -> None:
        """Test that tag listing endpoint is extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        paths = {ep.path for ep in result.endpoints}
        assert "/tags" in paths, "Should find tags listing endpoint"

    def test_multiple_methods_per_path(self, realworld_path: str) -> None:
        """Test that paths with multiple HTTP methods are correctly extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        # Group endpoints by path
        path_methods = {}
        for ep in result.endpoints:
            if ep.path not in path_methods:
                path_methods[ep.path] = set()
            path_methods[ep.path].add(ep.method)

        # Find paths with multiple methods
        multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
        assert len(multi_method_paths) == 6, \
            f"Expected exactly 6 paths with multiple HTTP methods, found {len(multi_method_paths)}"

        # Verify specific multi-method paths
        assert len(path_methods["/articles"]) == 2, "Should have GET and POST for /articles"
        assert len(path_methods["/articles/{slug}"]) == 3, \
            "Should have GET, PUT, DELETE for /articles/{slug}"
        assert len(path_methods["/user"]) == 2, "Should have GET and PUT for /user"

    def test_unique_paths(self, realworld_path: str) -> None:
        """Test that correct number of unique paths are found."""
        extractor = ExpressExtractor()
        result = extractor.extract(realworld_path)

        assert result.success

        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) == 13, \
            f"Expected exactly 13 unique paths, found {len(unique_paths)}"
