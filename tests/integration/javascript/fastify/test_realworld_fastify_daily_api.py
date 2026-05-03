"""Integration tests for Fastify extractor with daily-api."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.fastify import FastifyExtractor


@pytest.fixture
def daily_api_path():
    """Get path to daily-api fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "..", "fixtures",
        "real-world",
        "javascript",
        "fastify",
        "daily-api",
    )
    if not os.path.exists(path):
        pytest.skip("daily-api fixture not available (run: git submodule update --init)")
    return path


class TestFastifyDailyAPI:
    """Integration tests for dailydotdev/daily-api."""

    def test_extraction(self, daily_api_path: str) -> None:
        """Test extraction from daily-api.

        Repository: https://github.com/dailydotdev/daily-api
        Domain: Developer News & Content Delivery Platform
        """
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count (exact match per coding standards)
        assert len(result.endpoints) == 153, \
            f"Expected exactly 153 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, daily_api_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"
        assert HTTPMethod.PATCH in methods, "Should find PATCH endpoints"

    def test_large_scale_extraction(self, daily_api_path: str) -> None:
        """Test that extractor handles large codebases efficiently."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        # Verify substantial number of unique paths
        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) == 116, \
            f"Expected exactly 116 unique paths, found {len(unique_paths)}"

    def test_documentation_endpoints(self, daily_api_path: str) -> None:
        """Test that API documentation endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Swagger/OpenAPI documentation
        assert "/docs/json" in paths, "Should find JSON docs endpoint"
        assert "/docs/yaml" in paths, "Should find YAML docs endpoint"

    def test_content_endpoints(self, daily_api_path: str) -> None:
        """Test that content-related endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Content delivery paths
        assert "/discussed" in paths, "Should find discussed posts endpoint"
        assert "/companion" in paths, "Should find companion endpoint"

    def test_xml_feed_endpoints(self, daily_api_path: str) -> None:
        """Test that XML feed endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # RSS/XML feeds
        assert "/archive-index.xml" in paths, "Should find archive index XML"
        assert "/collections.xml" in paths, "Should find collections XML"

    def test_authentication_endpoints(self, daily_api_path: str) -> None:
        """Test that authentication endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Auth endpoints
        assert "/auth/callback" in paths, "Should find auth callback endpoint"

    def test_user_endpoints(self, daily_api_path: str) -> None:
        """Test that user-related endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # User management
        assert "/checkUsername" in paths, "Should find username check endpoint"
        assert "/confirmUserEmail" in paths, "Should find email confirmation endpoint"

    def test_path_parameters(self, daily_api_path: str) -> None:
        """Test that path parameters are properly extracted in OpenAPI format."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 43, \
            f"Expected exactly 43 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify OpenAPI format (not Fastify :param format)
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path, \
                f"Path parameter should use OpenAPI format: {ep.path}"

    def test_complex_path_parameters(self, daily_api_path: str) -> None:
        """Test that complex multi-parameter paths are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        # Find paths with multiple parameters
        multi_param_paths = [ep.path for ep in result.endpoints
                            if ep.path.count("{") >= 2]
        assert len(multi_param_paths) == 2, \
            f"Expected exactly 2 paths with multiple parameters, found {len(multi_param_paths)}"

        # Verify specific complex patterns exist
        paths = {ep.path for ep in result.endpoints}
        assert any("{user_id}" in p and "{action_name}" in p for p in paths), \
            "Should find paths with user_id and action_name parameters"

    def test_source_tracking(self, daily_api_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".ts"), \
                f"Expected .ts file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_digest_endpoint(self, daily_api_path: str) -> None:
        """Test that digest sending endpoint is extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        assert "/digest/send" in paths, "Should find digest send endpoint"

    def test_delete_operations(self, daily_api_path: str) -> None:
        """Test that DELETE operations are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        # Find DELETE endpoints
        delete_endpoints = [ep for ep in result.endpoints if ep.method == HTTPMethod.DELETE]
        assert len(delete_endpoints) == 6, \
            f"Expected exactly 6 DELETE endpoints, found {len(delete_endpoints)}"

    def test_patch_operations(self, daily_api_path: str) -> None:
        """Test that PATCH operations are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        # Find PATCH endpoints
        patch_endpoints = [ep for ep in result.endpoints if ep.method == HTTPMethod.PATCH]
        assert len(patch_endpoints) == 5, \
            f"Expected exactly 5 PATCH endpoints, found {len(patch_endpoints)}"

    def test_api_user_endpoint(self, daily_api_path: str) -> None:
        """Test that API user briefing endpoint is extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        assert "/api/user/briefing" in paths, "Should find user briefing API endpoint"

    def test_root_endpoints(self, daily_api_path: str) -> None:
        """Test that root endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        # Find root path endpoints (may be multiple from different route files)
        root_endpoints = [ep for ep in result.endpoints if ep.path == "/"]
        assert len(root_endpoints) == 23, \
            f"Expected exactly 23 root endpoints from different routes, found {len(root_endpoints)}"

    def test_slug_based_routing(self, daily_api_path: str) -> None:
        """Test that slug-based routing is properly extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(daily_api_path)

        assert result.success

        # Find slug parameter endpoints
        slug_endpoints = [ep for ep in result.endpoints if "{slug}" in ep.path]
        assert len(slug_endpoints) == 1, \
            f"Expected exactly 1 endpoint with {{slug}} parameter, found {len(slug_endpoints)}"

        # Verify specific slug pattern
        paths = {ep.path for ep in result.endpoints}
        assert "/b/{slug}" in paths, "Should find /b/{slug} endpoint"
