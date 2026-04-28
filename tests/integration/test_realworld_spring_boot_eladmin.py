"""Integration tests for Spring Boot extractor with eladmin."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.java.spring_boot import SpringBootExtractor


@pytest.fixture
def eladmin_path():
    """Get path to eladmin fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "java",
        "spring-boot",
        "eladmin",
    )
    if not os.path.exists(path):
        pytest.skip("eladmin fixture not available (run: git submodule update --init)")
    return path


class TestSpringBootEladmin:
    """Integration tests for eladmin."""

    def test_extraction(self, eladmin_path: str) -> None:
        """Test extraction from eladmin.

        Repository: https://github.com/elunez/eladmin
        Domain: Enterprise Backend Management System / Admin Dashboard
        """
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count (exact match per coding standards)
        assert len(result.endpoints) == 133, \
            f"Expected exactly 133 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, eladmin_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_unique_paths(self, eladmin_path: str) -> None:
        """Test that correct number of unique paths are found."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success

        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) == 88, \
            f"Expected exactly 88 unique paths, found {len(unique_paths)}"

    def test_authentication_endpoints(self, eladmin_path: str) -> None:
        """Test that authentication endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Auth endpoints
        assert "/auth/info" in paths, "Should find user info endpoint"
        assert "/auth/online" in paths, "Should find online users endpoint"

    def test_user_management_endpoints(self, eladmin_path: str) -> None:
        """Test that user management endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # User management
        assert "/api/users" in paths, "Should find users endpoint"
        user_endpoints = [ep for ep in result.endpoints if "/api/users" in ep.path]
        assert len(user_endpoints) >= 4, "Should have multiple user operations"

    def test_rbac_endpoints(self, eladmin_path: str) -> None:
        """Test that RBAC (role/permission) endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # RBAC endpoints
        assert any("roles" in p for p in paths), "Should find role endpoints"
        assert any("menus" in p for p in paths), "Should find menu endpoints"

    def test_monitoring_endpoints(self, eladmin_path: str) -> None:
        """Test that monitoring endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Monitoring
        assert "/api/monitor" in paths, "Should find server monitoring endpoint"

    def test_system_management_endpoints(self, eladmin_path: str) -> None:
        """Test that system management endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # System management
        assert "/api/dict" in paths, "Should find dictionary endpoint"
        assert "/api/job" in paths, "Should find job/timed task endpoint"
        assert any("dept" in p for p in paths), "Should find department endpoints"

    def test_logging_endpoints(self, eladmin_path: str) -> None:
        """Test that logging endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Logging
        assert any("logs" in p for p in paths), "Should find log endpoints"

    def test_file_storage_endpoints(self, eladmin_path: str) -> None:
        """Test that file storage endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # File storage
        assert any("localStorage" in p or "storage" in p for p in paths), \
            "Should find file storage endpoints"

    def test_path_parameters(self, eladmin_path: str) -> None:
        """Test that path parameters are properly extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 9, \
            f"Expected exactly 9 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify OpenAPI format {param}
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path, \
                f"Path parameter should use OpenAPI format: {ep.path}"

    def test_source_tracking(self, eladmin_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".java"), \
                f"Expected .java file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_download_endpoints(self, eladmin_path: str) -> None:
        """Test that download/export endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success

        # Find download endpoints
        download_endpoints = [ep for ep in result.endpoints if "download" in ep.path]
        assert len(download_endpoints) >= 5, \
            f"Expected at least 5 download endpoints, found {len(download_endpoints)}"

    def test_code_generator_endpoints(self, eladmin_path: str) -> None:
        """Test that code generator endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Code generator
        assert any("generator" in p for p in paths), "Should find code generator endpoints"

    def test_multi_module_extraction(self, eladmin_path: str) -> None:
        """Test that endpoints are extracted from multiple Maven modules."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success

        # Check that we have endpoints from different modules
        source_files = {ep.source_file for ep in result.endpoints if ep.source_file}

        # Should have files from system, tools, logging, and generator modules
        modules_found = set()
        for source_file in source_files:
            if "eladmin-system" in source_file:
                modules_found.add("system")
            elif "eladmin-tools" in source_file:
                modules_found.add("tools")
            elif "eladmin-logging" in source_file:
                modules_found.add("logging")
            elif "eladmin-generator" in source_file:
                modules_found.add("generator")

        assert len(modules_found) >= 2, \
            f"Should extract from multiple modules, found: {modules_found}"

    def test_multiple_methods_per_path(self, eladmin_path: str) -> None:
        """Test that paths with multiple HTTP methods are correctly extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(eladmin_path)

        assert result.success

        # Group endpoints by path
        path_methods = {}
        for ep in result.endpoints:
            if ep.path not in path_methods:
                path_methods[ep.path] = set()
            path_methods[ep.path].add(ep.method)

        # Find paths with multiple methods
        multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
        assert len(multi_method_paths) == 18, \
            f"Expected exactly 18 paths with multiple HTTP methods, found {len(multi_method_paths)}"
