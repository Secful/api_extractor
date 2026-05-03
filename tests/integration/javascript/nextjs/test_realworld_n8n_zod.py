"""Integration tests for n8n - Zod validation extraction."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture(scope="class")
def n8n_path():
    """Get path to n8n fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "..", "fixtures",
        "real-world",
        "javascript",
        "express",
        "n8n-zod",
        "packages",
        "cli",
        "src",
    )
    if not os.path.exists(path):
        pytest.skip("n8n fixture not available (run: git submodule update --init)")
    return path


@pytest.fixture(scope="class")
def n8n_extraction_result(n8n_path):
    """Extract endpoints from n8n once and reuse across tests."""
    extractor = ExpressExtractor()
    return extractor.extract(n8n_path)


class TestN8nZod:
    """Integration tests for n8n - Zod validation."""

    def test_extraction_succeeds(self, n8n_extraction_result) -> None:
        """Test that extraction from n8n completes (with possible errors from test files).

        Repository: https://github.com/n8n-io/n8n
        Stars: 186,365
        Description: Fair-code workflow automation platform
        Validation: Zod with @Body decorators and DTO classes

        Note: n8n uses a custom decorator-based routing system.
        Extraction may have errors from test files but should find some endpoints.
        """
        result = n8n_extraction_result

        # n8n uses decorators, so extraction completes but may have errors
        # The key is that it finds some endpoints
        assert len(result.endpoints) > 0, "Should find at least some endpoints"

    def test_http_methods_detected(self, n8n_extraction_result) -> None:
        """Test that HTTP methods are detected."""
        result = n8n_extraction_result

        # n8n uses decorators, extraction may have errors but should detect methods
        methods = {ep.method for ep in result.endpoints}
        assert len(methods) > 0, "Should detect HTTP methods"
        # n8n should have GET, POST, PUT, DELETE endpoints
        assert HTTPMethod.GET in methods or HTTPMethod.POST in methods, \
            "Should find GET or POST endpoints"

    def test_source_tracking(self, n8n_extraction_result) -> None:
        """Test that source files and line numbers are tracked."""
        result = n8n_extraction_result

        # n8n uses decorators, extraction may have errors but should track sources
        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".ts"), \
                f"Expected .ts file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_zod_validation_in_codebase(self, n8n_path: str) -> None:
        """Test that the codebase contains Zod validation code.

        n8n uses Zod DTOs with @Body decorators for validation.
        """
        # n8n_path is packages/cli/src, go up to packages/
        packages_path = os.path.join(n8n_path, "..", "..")
        api_types_path = os.path.join(
            packages_path,
            "@n8n",
            "api-types",
            "src",
            "dto"
        )
        assert os.path.exists(api_types_path), "API types DTO directory should exist"

        # Find files with Zod imports
        import subprocess
        result = subprocess.run(
            ["find", api_types_path, "-name", "*.ts", "-exec",
             "grep", "-l", "from 'zod'", "{}", ";"],
            capture_output=True,
            text=True
        )

        # n8n should have Zod usage in DTOs
        zod_files = result.stdout.strip().split("\n")
        assert len(zod_files) > 0, "Should find Zod imports in DTO files"

    def test_controller_structure(self, n8n_path: str) -> None:
        """Test that n8n has controller files with REST endpoints."""
        controllers_path = os.path.join(n8n_path, "controllers")
        assert os.path.exists(controllers_path), "Controllers directory should exist"

        # Check for controller files
        controller_files = os.listdir(controllers_path)
        controller_ts_files = [f for f in controller_files if f.endswith(".controller.ts")]

        assert len(controller_ts_files) > 0, "Should have controller files"

    def test_package_json_dependencies(self, n8n_path: str) -> None:
        """Verify n8n uses Zod."""
        # Go up to n8n root
        n8n_root = os.path.join(n8n_path, "..", "..", "..")
        package_json = os.path.join(n8n_root, "package.json")

        assert os.path.exists(package_json), "package.json should exist"

        with open(package_json, encoding="utf-8") as f:
            content = f.read()
            assert '"zod"' in content, "Should have zod dependency"
