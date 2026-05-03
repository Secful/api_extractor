"""Integration tests for OpenAPI spec builder."""

from __future__ import annotations

import json
import os

import pytest

from api_extractor.extractors.java.spring_boot import SpringBootExtractor
from api_extractor.extractors.python.fastapi import FastAPIExtractor
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.openapi.builder import OpenAPIBuilder


class TestOpenAPIBuilder:
    """Test OpenAPI specification building and serialization."""

    def test_build_from_flask_endpoints(self) -> None:
        """Test building OpenAPI spec from Flask endpoints."""
        # Get fixture path
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        # Extract routes
        extractor = FlaskExtractor()
        result = extractor.extract(fixture_dir)
        assert result.success
        assert len(result.endpoints) > 0

        # Build OpenAPI spec
        builder = OpenAPIBuilder(title="Test API", version="1.0.0")
        spec = builder.build(result.endpoints)

        # Verify spec structure
        assert spec.openapi == "3.1.0"
        assert spec.info.title == "Test API"
        assert spec.info.version == "1.0.0"
        assert len(spec.paths) > 0

    def test_build_from_fastapi_endpoints(self) -> None:
        """Test building OpenAPI spec from FastAPI endpoints."""
        # Get fixture path
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        # Extract routes
        extractor = FastAPIExtractor()
        result = extractor.extract(fixture_dir)
        assert result.success
        assert len(result.endpoints) > 0

        # Build OpenAPI spec
        builder = OpenAPIBuilder(title="FastAPI Test", version="2.0.0")
        spec = builder.build(result.endpoints)

        # Verify spec structure
        assert spec.openapi == "3.1.0"
        assert spec.info.title == "FastAPI Test"
        assert spec.info.version == "2.0.0"
        assert len(spec.paths) > 0

        # Verify endpoints have tags
        assert spec.tags is not None
        tag_names = {tag.name for tag in spec.tags}
        assert "fastapi" in tag_names

    def test_build_from_spring_boot_endpoints(self) -> None:
        """Test building OpenAPI spec from Spring Boot endpoints."""
        # Get fixture path
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "java"
        )

        # Extract routes
        extractor = SpringBootExtractor()
        result = extractor.extract(fixture_dir)
        assert result.success
        assert len(result.endpoints) > 0

        # Build OpenAPI spec
        builder = OpenAPIBuilder(title="Spring Boot Test", version="1.0.0")
        spec = builder.build(result.endpoints)

        # Verify spec structure
        assert spec.openapi == "3.1.0"
        assert spec.info.title == "Spring Boot Test"
        assert spec.info.version == "1.0.0"
        assert len(spec.paths) > 0

        # Verify endpoints have tags
        assert spec.tags is not None
        tag_names = {tag.name for tag in spec.tags}
        assert "spring_boot" in tag_names

    def test_json_serialization(self) -> None:
        """Test JSON serialization of OpenAPI spec."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        extractor = FlaskExtractor()
        result = extractor.extract(fixture_dir)

        builder = OpenAPIBuilder(title="Test API", version="1.0.0")
        spec = builder.build(result.endpoints)

        # Serialize to JSON
        json_output = builder.to_json(spec)

        # Verify it's valid JSON and has expected structure
        parsed = json.loads(json_output)
        assert parsed["openapi"] == "3.1.0"
        assert parsed["info"]["title"] == "Test API"
        assert parsed["info"]["version"] == "1.0.0"
        assert "paths" in parsed
        assert isinstance(parsed["paths"], dict)

    def test_yaml_serialization(self) -> None:
        """Test YAML serialization of OpenAPI spec."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        extractor = FlaskExtractor()
        result = extractor.extract(fixture_dir)

        builder = OpenAPIBuilder(title="Test API", version="1.0.0")
        spec = builder.build(result.endpoints)

        # Serialize to YAML
        yaml_output = builder.to_yaml(spec)

        # Verify it's valid YAML with expected content
        assert "openapi: 3.1.0" in yaml_output or "openapi: '3.1.0'" in yaml_output
        assert "title: Test API" in yaml_output
        assert "version: 1.0.0" in yaml_output or "version: '1.0.0'" in yaml_output
        assert "paths:" in yaml_output

    def test_custom_title_and_version(self) -> None:
        """Test that custom title and version are correctly set."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        extractor = FastAPIExtractor()
        result = extractor.extract(fixture_dir)

        # Build with custom metadata
        builder = OpenAPIBuilder(title="My Custom API", version="3.5.2")
        spec = builder.build(result.endpoints)

        assert spec.info.title == "My Custom API"
        assert spec.info.version == "3.5.2"

        # Verify it persists through serialization
        json_output = builder.to_json(spec)
        parsed = json.loads(json_output)
        assert parsed["info"]["title"] == "My Custom API"
        assert parsed["info"]["version"] == "3.5.2"

    def test_paths_structure(self) -> None:
        """Test that paths are properly structured in the spec."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        extractor = FlaskExtractor()
        result = extractor.extract(fixture_dir)

        builder = OpenAPIBuilder(title="Test API", version="1.0.0")
        spec = builder.build(result.endpoints)

        # Verify paths structure
        assert spec.paths is not None
        assert len(spec.paths) > 0

        # Each path should have operations
        for path, path_item in spec.paths.items():
            assert path.startswith("/"), f"Path should start with /: {path}"
            # Should have at least one HTTP method
            has_operation = any(
                [
                    path_item.get,
                    path_item.post,
                    path_item.put,
                    path_item.delete,
                    path_item.patch,
                ]
            )
            assert has_operation, f"Path {path} should have at least one operation"

    def test_tags_generation(self) -> None:
        """Test that tags are properly generated from framework types."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "fixtures", "minimal", "python"
        )

        extractor = FastAPIExtractor()
        result = extractor.extract(fixture_dir)

        builder = OpenAPIBuilder(title="Test API", version="1.0.0")
        spec = builder.build(result.endpoints)

        # Should have tags
        assert spec.tags is not None
        assert len(spec.tags) > 0

        # Tags should correspond to frameworks
        tag_names = {tag.name for tag in spec.tags}
        assert "fastapi" in tag_names

    def test_empty_endpoints_handling(self) -> None:
        """Test that builder handles empty endpoint list gracefully."""
        builder = OpenAPIBuilder(title="Empty API", version="1.0.0")
        spec = builder.build([])

        # Should still produce valid spec
        assert spec.openapi == "3.1.0"
        assert spec.info.title == "Empty API"
        assert spec.paths == {} or len(spec.paths) == 0
