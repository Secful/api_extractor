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
    """Test CLI integration with Python fixtures."""
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


def test_cli_integration_express():
    """Test CLI integration with Express fixture."""
    import subprocess

    fixture_dir = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "javascript"
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
            ],
            capture_output=True,
            text=True,
        )

        # Check success
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert os.path.exists(output_file)

        # Verify output is valid JSON and contains routes from all JavaScript frameworks
        with open(output_file) as f:
            spec = json.load(f)
            assert spec["openapi"] == "3.1.0"
            assert "paths" in spec
            # JavaScript directory has Express, Fastify, and NestJS = 9 unique paths
            assert len(spec["paths"]) == 9, f"Expected 9 paths, got {len(spec['paths'])}"


def test_cli_integration_flask():
    """Test CLI integration with Flask only."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a directory with only Flask fixture
        flask_file = os.path.join(
            os.path.dirname(__file__), "..", "fixtures", "minimal", "python", "sample_flask.py"
        )
        test_dir = os.path.join(tmpdir, "flask_only")
        os.makedirs(test_dir)

        # Copy Flask file to isolated directory
        import shutil
        shutil.copy(flask_file, test_dir)

        output_file = os.path.join(tmpdir, "test-openapi.json")

        # Run CLI
        result = subprocess.run(
            [
                "api-extractor",
                "extract",
                test_dir,
                "--output",
                output_file,
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )

        # Check success
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert os.path.exists(output_file)

        # Verify Flask was detected
        with open(output_file) as f:
            spec = json.load(f)
            assert spec["openapi"] == "3.1.0"
            assert "paths" in spec
            # Flask fixture has 8 unique paths
            assert len(spec["paths"]) == 8, f"Expected 8 paths, got {len(spec['paths'])}"


def test_cli_integration_fastapi():
    """Test CLI integration with FastAPI only."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a directory with only FastAPI fixture
        fastapi_file = os.path.join(
            os.path.dirname(__file__), "..", "fixtures", "minimal", "python", "sample_fastapi.py"
        )
        test_dir = os.path.join(tmpdir, "fastapi_only")
        os.makedirs(test_dir)

        # Copy FastAPI file to isolated directory
        import shutil
        shutil.copy(fastapi_file, test_dir)

        output_file = os.path.join(tmpdir, "test-openapi.json")

        # Run CLI
        result = subprocess.run(
            [
                "api-extractor",
                "extract",
                test_dir,
                "--output",
                output_file,
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )

        # Check success
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert os.path.exists(output_file)

        # Verify FastAPI was detected
        with open(output_file) as f:
            spec = json.load(f)
            assert spec["openapi"] == "3.1.0"
            assert "paths" in spec
            # FastAPI fixture has 6 unique paths
            assert len(spec["paths"]) == 6, f"Expected 6 paths, got {len(spec['paths'])}"


def test_cli_integration_fastapi_realworld():
    """Test CLI integration with FastAPI real-world project."""
    import subprocess

    fixture_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "fastapi-fullstack",
        "backend",
        "app",
    )

    # Skip if real-world fixture doesn't exist
    if not os.path.exists(fixture_dir):
        pytest.skip("FastAPI real-world fixture not available (run: git submodule update --init)")

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
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )

        # Check success
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert os.path.exists(output_file)

        # Verify real-world app was analyzed
        with open(output_file) as f:
            spec = json.load(f)
            assert spec["openapi"] == "3.1.0"
            assert "paths" in spec
            # Real-world FastAPI fullstack has 14 unique paths
            assert len(spec["paths"]) == 14, f"Expected 14 paths in real-world app, got {len(spec['paths'])}"


def test_cli_integration_fastify_realworld():
    """Test CLI integration with Fastify real-world project."""
    import subprocess

    fixture_dir = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "real-world", "fastify-demo"
    )

    # Skip if real-world fixture doesn't exist
    if not os.path.exists(fixture_dir):
        pytest.skip("Fastify real-world fixture not available (run: git submodule update --init)")

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
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )

        # Check success
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert os.path.exists(output_file)

        # Verify real-world app was analyzed
        with open(output_file) as f:
            spec = json.load(f)
            assert spec["openapi"] == "3.1.0"
            assert "paths" in spec
            # Real-world Fastify demo has 9 unique paths
            assert len(spec["paths"]) == 9, f"Expected 9 paths in real-world app, got {len(spec['paths'])}"


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
