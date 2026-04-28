"""Integration tests for Spring Boot extractor against real-world applications."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.java.spring_boot import SpringBootExtractor


@pytest.fixture
def spring_boot_realworld_path():
    """Get path to Spring Boot RealWorld fixture."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "java",
        "spring-boot",
        "spring-boot-realworld-example-app",
    )


class TestSpringBootRealWorld:
    """Test Spring Boot extractor with real-world RealWorld application."""

    def test_realworld_extraction(self, spring_boot_realworld_path: str) -> None:
        """Test extraction from Spring Boot RealWorld example app.

        This tests against the official RealWorld implementation:
        https://github.com/gothinkster/spring-boot-realworld-example-app

        Expected: Conduit blogging platform API with users, articles,
        comments, favorites, following, profiles, and tags.
        """
        # Skip if real-world fixture doesn't exist
        if not os.path.exists(spring_boot_realworld_path):
            pytest.skip("Spring Boot real-world fixture not available")

        extractor = SpringBootExtractor()
        result = extractor.extract(spring_boot_realworld_path)

        # Check extraction succeeded
        assert result.success, "Extraction should succeed on Spring Boot RealWorld app"
        assert len(result.endpoints) > 0, "Should find endpoints in Spring Boot RealWorld"

        # Real-world Spring Boot app has 19 endpoints across multiple paths
        assert (
            len(result.endpoints) >= 15
        ), f"Should find at least 15 endpoints, found {len(result.endpoints)}"

    def test_realworld_standard_paths(self, spring_boot_realworld_path: str) -> None:
        """Verify standard RealWorld API paths are found."""
        if not os.path.exists(spring_boot_realworld_path):
            pytest.skip("Spring Boot real-world fixture not available")

        extractor = SpringBootExtractor()
        result = extractor.extract(spring_boot_realworld_path)

        # Get all unique paths
        paths = {ep.path for ep in result.endpoints}

        # RealWorld spec defines standard endpoints
        expected_path_patterns = [
            "/users",
            "/articles",
            "/profiles",
            "/tags",
        ]

        found_patterns = []
        for pattern in expected_path_patterns:
            if any(pattern in path for path in paths):
                found_patterns.append(pattern)

        assert (
            len(found_patterns) >= 3
        ), f"Should find at least 3 standard RealWorld paths, found: {found_patterns}"

    def test_realworld_http_methods(self, spring_boot_realworld_path: str) -> None:
        """Verify various HTTP methods are detected."""
        if not os.path.exists(spring_boot_realworld_path):
            pytest.skip("Spring Boot real-world fixture not available")

        extractor = SpringBootExtractor()
        result = extractor.extract(spring_boot_realworld_path)

        # Collect all HTTP methods used
        methods = {ep.method for ep in result.endpoints}

        # RealWorld API should use various HTTP methods
        assert HTTPMethod.GET in methods, "Should have GET endpoints"
        assert HTTPMethod.POST in methods, "Should have POST endpoints"
        assert HTTPMethod.PUT in methods, "Should have PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should have DELETE endpoints"

    def test_realworld_path_parameters(self, spring_boot_realworld_path: str) -> None:
        """Test that path parameters are correctly extracted."""
        if not os.path.exists(spring_boot_realworld_path):
            pytest.skip("Spring Boot real-world fixture not available")

        extractor = SpringBootExtractor()
        result = extractor.extract(spring_boot_realworld_path)

        # Find endpoints with path parameters (OpenAPI format: {param})
        param_endpoints = [
            ep for ep in result.endpoints if "{" in ep.path and "}" in ep.path
        ]
        assert (
            len(param_endpoints) > 0
        ), "Should find endpoints with path parameters (e.g., /users/{username})"

        # Check specific parameter patterns from RealWorld spec
        profile_endpoints = [ep for ep in param_endpoints if "profiles" in ep.path]
        assert (
            len(profile_endpoints) > 0
        ), "Should find profile endpoints with username parameter"

        # Verify parameter format
        for ep in param_endpoints:
            assert (
                "{" in ep.path and "}" in ep.path
            ), "Path parameters should use OpenAPI format {param}"
            # Should have corresponding parameter definitions
            path_params = [p for p in ep.parameters if p.location.value == "path"]
            assert (
                len(path_params) > 0
            ), f"Endpoint {ep.path} should have path parameter definitions"

    def test_realworld_source_file_tracking(self, spring_boot_realworld_path: str) -> None:
        """Verify source file and line tracking for all endpoints."""
        if not os.path.exists(spring_boot_realworld_path):
            pytest.skip("Spring Boot real-world fixture not available")

        extractor = SpringBootExtractor()
        result = extractor.extract(spring_boot_realworld_path)

        # Verify all endpoints have source tracking
        for endpoint in result.endpoints:
            assert endpoint.source_file is not None, "Endpoint should have source file"
            assert endpoint.source_file.endswith(".java"), "Source file should be Java"
            assert endpoint.source_line is not None, "Endpoint should have source line"
            assert endpoint.source_line > 0, "Source line should be positive"

    def test_realworld_controller_structure(self, spring_boot_realworld_path: str) -> None:
        """Test that endpoints from multiple controllers are extracted."""
        if not os.path.exists(spring_boot_realworld_path):
            pytest.skip("Spring Boot real-world fixture not available")

        extractor = SpringBootExtractor()
        result = extractor.extract(spring_boot_realworld_path)

        # Group endpoints by source file (controller)
        files = {ep.source_file for ep in result.endpoints}

        # RealWorld app has multiple domain controllers
        assert (
            len(files) >= 2
        ), f"Should find endpoints from multiple source files, found {len(files)}"

        # All source files should be Java files
        for f in files:
            assert f.endswith(".java"), f"Source file should be Java: {f}"

    def test_realworld_rest_annotations(self, spring_boot_realworld_path: str) -> None:
        """Verify Spring Boot REST annotations are properly detected."""
        if not os.path.exists(spring_boot_realworld_path):
            pytest.skip("Spring Boot real-world fixture not available")

        extractor = SpringBootExtractor()
        result = extractor.extract(spring_boot_realworld_path)

        # Group by HTTP methods to verify annotation detection
        methods_count = {}
        for endpoint in result.endpoints:
            method = endpoint.method.value
            methods_count[method] = methods_count.get(method, 0) + 1

        # Should have extracted various method types from annotations
        # @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, etc.
        assert len(methods_count) >= 3, "Should detect multiple HTTP method types"
        assert methods_count.get("GET", 0) > 0, "Should find @GetMapping endpoints"
        assert methods_count.get("POST", 0) > 0, "Should find @PostMapping endpoints"
