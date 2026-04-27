"""Tests for Spring Boot extractor."""

from __future__ import annotations

import pytest
from pathlib import Path
from api_extractor.extractors.java.spring_boot import SpringBootExtractor
from api_extractor.core.models import HTTPMethod, FrameworkType


@pytest.fixture
def extractor():
    """Create Spring Boot extractor instance."""
    return SpringBootExtractor()


@pytest.fixture
def fixture_path():
    """Get path to test fixtures."""
    return str(Path(__file__).parent.parent / "fixtures" / "minimal" / "java")


def test_spring_boot_basic_extraction(extractor, fixture_path):
    """Test basic Spring Boot route extraction."""
    result = extractor.extract(fixture_path)

    assert result.success
    assert len(result.endpoints) >= 7

    paths = {(ep.path, ep.method) for ep in result.endpoints}

    # UserController endpoints
    assert ("/api/users", HTTPMethod.GET) in paths
    assert ("/api/users/{id}", HTTPMethod.GET) in paths
    assert ("/api/users", HTTPMethod.POST) in paths
    assert ("/api/users/{id}", HTTPMethod.PUT) in paths
    assert ("/api/users/{id}", HTTPMethod.DELETE) in paths
    assert ("/api/users/search", HTTPMethod.GET) in paths

    # HealthController endpoint (no @RequestMapping on class)
    assert ("/health", HTTPMethod.GET) in paths


def test_spring_boot_path_parameters(extractor):
    """Test path parameter extraction."""
    params = extractor._extract_path_parameters("/users/{id}")

    assert len(params) == 1
    assert params[0].name == "id"
    assert params[0].location.value == "path"
    assert params[0].required is True


def test_spring_boot_path_normalization(extractor):
    """Test path normalization (Spring Boot already uses OpenAPI format)."""
    assert extractor._normalize_path("/users/{id}") == "/users/{id}"
    assert extractor._normalize_path("/api/{version}/users") == "/api/{version}/users"


def test_spring_boot_no_routes(extractor, tmp_path):
    """Test extraction from file with no routes."""
    test_file = tmp_path / "Empty.java"
    test_file.write_text("package com.example; public class Empty { }")

    result = extractor.extract(str(tmp_path))
    assert not result.success
    assert len(result.endpoints) == 0


def test_spring_boot_framework_type(extractor):
    """Test framework type is correctly set."""
    assert extractor.framework == FrameworkType.SPRING_BOOT


def test_spring_boot_file_extensions(extractor):
    """Test correct file extensions are returned."""
    extensions = extractor.get_file_extensions()
    assert extensions == [".java"]


def test_spring_boot_path_parameters_with_multiple(extractor):
    """Test extraction of multiple path parameters."""
    params = extractor._extract_path_parameters("/articles/{slug}/comments/{id}")

    assert len(params) == 2
    assert params[0].name == "slug"
    assert params[0].location.value == "path"
    assert params[1].name == "id"
    assert params[1].location.value == "path"


def test_spring_boot_path_combination(extractor):
    """Test path combination logic."""
    # Base path + method path
    assert extractor._combine_paths("/api", "/users") == "/api/users"

    # Empty base path
    assert extractor._combine_paths("", "/users") == "/users"

    # Empty method path
    assert extractor._combine_paths("/api", "") == "/api"

    # No leading slashes
    assert extractor._combine_paths("api", "users") == "/api/users"

    # Trailing slash handling
    assert extractor._combine_paths("/api/", "/users") == "/api/users"


def test_spring_boot_java_type_mapping(extractor):
    """Test Java type to OpenAPI type mapping."""
    assert extractor._parse_java_type("String") == "string"
    assert extractor._parse_java_type("Integer") == "integer"
    assert extractor._parse_java_type("int") == "integer"
    assert extractor._parse_java_type("Long") == "integer"
    assert extractor._parse_java_type("Boolean") == "boolean"
    assert extractor._parse_java_type("Double") == "number"
    assert extractor._parse_java_type("List<User>") == "array"
    assert extractor._parse_java_type("Map<String, Object>") == "object"


def test_spring_boot_real_world_extraction(extractor):
    """Test extraction from real-world Spring Boot application."""
    real_world_path = (
        Path(__file__).parent.parent
        / "fixtures"
        / "real-world"
        / "spring-boot-realworld-example-app"
        / "src"
        / "main"
    )

    if not real_world_path.exists():
        pytest.skip("Real-world fixture not available")

    result = extractor.extract(str(real_world_path))

    assert result.success
    # RealWorld app should have multiple endpoints
    assert len(result.endpoints) >= 15

    paths = {ep.path for ep in result.endpoints}

    # Check for some expected RealWorld API paths
    assert "/users" in paths or any("/user" in p for p in paths)
    assert any("/articles" in p for p in paths)
    assert any("/profiles" in p for p in paths)
