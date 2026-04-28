"""Integration tests for Fastify extractor with fastify-api-boilerplate-jwt."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.fastify import FastifyExtractor


@pytest.fixture
def jwt_boilerplate_path():
    """Get path to fastify-api-boilerplate-jwt fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "javascript",
        "fastify",
        "jwt-boilerplate",
    )
    if not os.path.exists(path):
        pytest.skip("Fastify JWT boilerplate fixture not available (run: git submodule update --init)")
    return path


class TestFastifyJWTBoilerplate:
    """Integration tests for fastify-api-boilerplate-jwt."""

    def test_extraction(self, jwt_boilerplate_path: str) -> None:
        """Test extraction from fastify-api-boilerplate-jwt.

        Repository: https://github.com/Tony133/fastify-api-boilerplate-jwt
        Domain: Authentication & User Management System
        """
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count (exact match per coding standards)
        assert len(result.endpoints) == 18, \
            f"Expected exactly 18 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, jwt_boilerplate_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_authentication_endpoints(self, jwt_boilerplate_path: str) -> None:
        """Test that authentication endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Core authentication paths
        assert "/login" in paths, "Should find login endpoint"
        assert "/refresh-token" in paths, "Should find refresh token endpoint"
        assert "/is-authenticated" in paths, "Should find authentication check endpoint"
        assert "/user-authenticated" in paths, "Should find authenticated user endpoint"

    def test_protected_endpoints(self, jwt_boilerplate_path: str) -> None:
        """Test that protected/secured endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Protected endpoint patterns
        assert "/protected" in paths, "Should find protected endpoint"
        assert "/secure" in paths, "Should find secure endpoint"

    def test_admin_endpoints(self, jwt_boilerplate_path: str) -> None:
        """Test that admin-restricted endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Admin endpoints
        assert "/admin" in paths, "Should find admin endpoint"
        assert "/admin-only" in paths, "Should find admin-only endpoint"

    def test_path_parameters(self, jwt_boilerplate_path: str) -> None:
        """Test that path parameters are properly extracted in OpenAPI format."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 3, \
            f"Expected exactly 3 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify OpenAPI format (not Fastify :param format)
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path, \
                f"Path parameter should use OpenAPI format: {ep.path}"
            assert not any(part.startswith(":") for part in ep.path.split("/")), \
                f"Path should not contain Fastify :param format: {ep.path}"

        # Verify {id} parameter exists
        paths = {ep.path for ep in result.endpoints}
        assert "/{id}" in paths, "Should find {id} parameter endpoint"

    def test_crud_operations_with_id(self, jwt_boilerplate_path: str) -> None:
        """Test that CRUD operations with ID parameter are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success

        # Find endpoints with {id} parameter
        id_endpoints = [ep for ep in result.endpoints if "/{id}" == ep.path]
        assert len(id_endpoints) == 3, \
            f"Expected exactly 3 /{id} endpoints (GET, PUT, DELETE), found {len(id_endpoints)}"

        # Verify methods on /{id}
        id_methods = {ep.method for ep in id_endpoints}
        assert HTTPMethod.GET in id_methods, "Should have GET /{id}"
        assert HTTPMethod.PUT in id_methods, "Should have PUT /{id}"
        assert HTTPMethod.DELETE in id_methods, "Should have DELETE /{id}"

    def test_source_tracking(self, jwt_boilerplate_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".ts"), \
                f"Expected .ts file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_root_endpoint(self, jwt_boilerplate_path: str) -> None:
        """Test that root endpoints are extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success

        # Find root path endpoints
        root_endpoints = [ep for ep in result.endpoints if ep.path == "/"]
        assert len(root_endpoints) >= 2, \
            f"Expected at least 2 root endpoints, found {len(root_endpoints)}"

    def test_unique_paths(self, jwt_boilerplate_path: str) -> None:
        """Test that correct number of unique paths are found."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success

        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) == 11, \
            f"Expected exactly 11 unique paths, found {len(unique_paths)}"

    def test_multiple_methods_per_path(self, jwt_boilerplate_path: str) -> None:
        """Test that paths with multiple HTTP methods are correctly extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success

        # Group endpoints by path
        path_methods = {}
        for ep in result.endpoints:
            if ep.path not in path_methods:
                path_methods[ep.path] = set()
            path_methods[ep.path].add(ep.method)

        # Find paths with multiple methods
        multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
        assert len(multi_method_paths) == 2, \
            f"Expected exactly 2 paths with multiple HTTP methods, found {len(multi_method_paths)}"

        # Verify /{id} has multiple methods (GET, PUT, DELETE)
        assert "/{id}" in multi_method_paths, "/{id} should have multiple methods"
        assert len(path_methods["/{id}"]) == 3, "/{id} should have exactly 3 methods"

    def test_no_user_endpoint(self, jwt_boilerplate_path: str) -> None:
        """Test that no-user endpoint is extracted."""
        extractor = FastifyExtractor()
        result = extractor.extract(jwt_boilerplate_path)

        assert result.success

        paths = {ep.path for ep in result.endpoints}
        assert "/no-user" in paths, "Should find /no-user endpoint"
