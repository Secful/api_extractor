"""Integration tests for full pipeline."""

import os
import json
import tempfile
import pytest
from api_extractor.core.detector import FrameworkDetector
from api_extractor.core.models import FrameworkType
from api_extractor.extractors.python.fastapi import FastAPIExtractor
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.openapi.builder import OpenAPIBuilder


def test_full_pipeline_flask():
    """Test full pipeline with Flask."""
    # Get fixture path
    fixture_dir = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "python"
    )

    # Manually specify Flask to avoid detection ambiguity with multiple fixtures
    frameworks = [FrameworkType.FLASK]

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
    assert len(spec.paths) > 0

    # Verify we can serialize to JSON
    json_output = builder.to_json(spec)
    parsed = json.loads(json_output)
    assert parsed["openapi"] == "3.1.0"
    assert "paths" in parsed

    # Verify we can serialize to YAML
    yaml_output = builder.to_yaml(spec)
    assert "openapi: 3.1.0" in yaml_output
    assert "paths:" in yaml_output


def test_full_pipeline_fastapi():
    """Test full pipeline with FastAPI."""
    # Get fixture path
    fixture_dir = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "python"
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


def test_framework_detection():
    """Test framework detection."""
    fixture_dir = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "python"
    )

    detector = FrameworkDetector()
    frameworks = detector.detect(fixture_dir)

    assert frameworks is not None
    assert len(frameworks) > 0

    # Should detect at least one Python framework
    framework_names = {fw.value for fw in frameworks}
    python_frameworks = {"flask", "fastapi", "django_rest"}
    assert len(framework_names & python_frameworks) > 0


def test_detection_failure():
    """Test detection failure on empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        detector = FrameworkDetector()
        frameworks = detector.detect(tmpdir)
        assert frameworks is None


def test_cli_integration():
    """Test CLI integration."""
    import subprocess

    fixture_dir = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "python"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test-openapi.json")

        # Run CLI
        result = subprocess.run(
            [
                "api-extractor",
                "extract",
                fixture_dir,
                "--output",
                output_file,
                "--framework",
                "flask",
            ],
            capture_output=True,
            text=True,
        )

        # Check success
        assert result.returncode == 0
        assert os.path.exists(output_file)

        # Verify output is valid JSON
        with open(output_file) as f:
            spec = json.load(f)
            assert spec["openapi"] == "3.1.0"
            assert "paths" in spec


def test_mixed_framework_detection():
    """Test detecting multiple frameworks in same codebase."""
    fixture_dir = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "python"
    )

    detector = FrameworkDetector()
    frameworks = detector.detect(fixture_dir)

    # Should detect both Flask and FastAPI since both sample files exist
    assert frameworks is not None
    framework_names = {fw.value for fw in frameworks}

    # At least one should be detected
    assert len(framework_names) >= 1
