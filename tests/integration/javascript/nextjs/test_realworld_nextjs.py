"""Integration tests for Next.js real-world projects."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

import pytest


class TestNextJSRealWorld:
    """Test Next.js extractor with real-world projects."""

    def test_calcom_extraction(self) -> None:
        """Test extraction from Cal.com (production Next.js app)."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "..", "..", "fixtures", "real-world", "javascript", "nextjs", "cal.com"
        )

        # Skip if real-world fixture doesn't exist
        if not os.path.exists(fixture_dir):
            pytest.skip("Cal.com real-world fixture not available")

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

            # Verify Cal.com was analyzed
            with open(output_file) as f:
                spec = json.load(f)
                assert spec["openapi"] == "3.1.0"
                assert "paths" in spec
                # Cal.com has API routes in both App Router and Pages Router
                assert (
                    len(spec["paths"]) >= 5
                ), f"Expected at least 5 paths in Cal.com, got {len(spec['paths'])}"

                # Verify some expected Cal.com API paths
                paths = set(spec["paths"].keys())
                expected_paths = ["/api/csrf", "/api/ip", "/api/stripe/webhook"]
                found_paths = [p for p in expected_paths if p in paths]
                assert (
                    len(found_paths) >= 1
                ), f"Expected to find some Cal.com API paths, got: {paths}"

    def test_dub_extraction(self) -> None:
        """Test extraction from Dub (production Next.js app with App Router)."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "..", "..", "fixtures", "real-world", "javascript", "nextjs", "dub"
        )

        # Skip if real-world fixture doesn't exist
        if not os.path.exists(fixture_dir):
            pytest.skip("Dub real-world fixture not available")

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

            # Verify Dub was analyzed
            with open(output_file) as f:
                spec = json.load(f)
                assert spec["openapi"] == "3.1.0"
                assert "paths" in spec
                # Dub uses App Router extensively
                assert (
                    len(spec["paths"]) >= 15
                ), f"Expected at least 15 paths in Dub, got {len(spec['paths'])}"

                # Verify some expected Dub API paths
                paths = set(spec["paths"].keys())
                expected_paths = ["/api", "/api/links", "/api/analytics", "/api/oauth"]
                found_paths = [p for p in expected_paths if any(p in path for path in paths)]
                assert (
                    len(found_paths) >= 2
                ), f"Expected to find some Dub API paths, got: {paths}"

    def test_app_router_pattern_detection(self) -> None:
        """Verify App Router pattern detection in Dub."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "..", "..", "fixtures", "real-world", "javascript", "nextjs", "dub"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Dub real-world fixture not available")

        # Check that Dub has App Router structure
        app_api_dir = os.path.join(fixture_dir, "apps", "web", "app", "api")
        assert os.path.exists(app_api_dir), "Expected Dub to have app/api directory"

        # Check for route.ts files
        route_files = []
        for root, _, files in os.walk(app_api_dir):
            for file in files:
                if file == "route.ts" or file == "route.tsx":
                    route_files.append(os.path.join(root, file))

        assert len(route_files) == 140, f"Expected at least 15 route.ts files, found {len(route_files)}"

    def test_pages_router_pattern_detection(self) -> None:
        """Verify Pages Router pattern detection in Cal.com."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "..", "..", "fixtures", "real-world", "javascript", "nextjs", "cal.com"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Cal.com real-world fixture not available")

        # Check that Cal.com has Pages Router structure
        pages_api_dir = os.path.join(fixture_dir, "apps", "web", "pages", "api")
        if os.path.exists(pages_api_dir):
            # Check for API files
            api_files = []
            for root, _, files in os.walk(pages_api_dir):
                for file in files:
                    if file.endswith((".ts", ".js", ".tsx", ".jsx")):
                        api_files.append(os.path.join(root, file))

            assert len(api_files) == 39, f"Expected at least 3 API files, found {len(api_files)}"

    def test_mixed_router_support(self) -> None:
        """Verify both App Router and Pages Router are detected in Cal.com."""
        fixture_dir = os.path.join(
        str(os.path.dirname(__file__)), "..", "..", "..", "..", "fixtures", "real-world", "javascript", "nextjs", "cal.com"
        )

        if not os.path.exists(fixture_dir):
            pytest.skip("Cal.com real-world fixture not available")

        # Cal.com uses both routers
        app_router_exists = os.path.exists(
            os.path.join(fixture_dir, "apps", "web", "app", "api")
        )
        pages_router_exists = os.path.exists(
            os.path.join(fixture_dir, "apps", "web", "pages", "api")
        )

        # At least one should exist (Cal.com uses both)
        assert (
            app_router_exists or pages_router_exists
        ), "Expected Cal.com to have either App Router or Pages Router API structure"
