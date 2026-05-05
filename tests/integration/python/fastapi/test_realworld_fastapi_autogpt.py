"""Integration tests for FastAPI extractor with AutoGPT backend."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.fastapi import FastAPIExtractor


@pytest.fixture
def autogpt_path():
    """Get path to AutoGPT real-world fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "python",
        "fastapi",
        "autogpt",
        "autogpt_platform",
        "backend",
    )
    if not os.path.exists(path):
        pytest.skip("AutoGPT fixture not available")
    return path


class TestFastAPIAutoGPT:
    """Integration tests for AutoGPT platform backend."""

    def test_extraction(self, autogpt_path: str) -> None:
        """Test extraction from AutoGPT.

        Repository: https://github.com/Significant-Gravitas/AutoGPT
        Domain: AI Agent Platform
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify significant endpoint count (AutoGPT has many routes)
        assert len(result.endpoints) >= 50, \
            f"Expected at least 50 endpoints, found {len(result.endpoints)}"

    def test_include_router_with_prefix(self, autogpt_path: str) -> None:
        """Test that include_router(prefix=...) is properly extracted."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check that router_include_prefixes mapping is populated
        assert len(extractor.router_include_prefixes) > 0, \
            "Should extract include_router prefix mappings"

        # Verify specific prefixes are captured
        assert "integrations_router" in extractor.router_include_prefixes
        assert extractor.router_include_prefixes["integrations_router"] == "/api/integrations"

        assert "analytics_router" in extractor.router_include_prefixes
        assert extractor.router_include_prefixes["analytics_router"] == "/api/analytics"

        # app.include_router(..., prefix="/api/integrations")
        integration_routes = [p for p in paths if p.startswith("/api/integrations")]
        assert len(integration_routes) > 0, "Should find /api/integrations routes"

    def test_dotted_router_names(self, autogpt_path: str) -> None:
        """Test extraction of routers with dotted import names.

        Pattern: app.include_router(backend.api.features.v1.v1_router, prefix="/api")
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # v1 routes should have /api prefix
        api_routes = [p for p in paths if p.startswith("/api")]
        assert len(api_routes) >= 10, "Should find many /api routes"

    def test_http_methods(self, autogpt_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_admin_endpoints(self, autogpt_path: str) -> None:
        """Test that admin endpoints with prefixes are extracted."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # app.include_router(...admin.store_admin_routes.router, prefix="/api/store")
        # app.include_router(...admin.credit_admin_routes.router, prefix="/api/credits")
        # app.include_router(...admin.diagnostics_admin_routes.router, prefix="/api")
        admin_keywords = ["store", "credits", "executions", "copilot", "admin"]
        admin_routes = [
            p for p in paths
            if any(keyword in p.lower() for keyword in admin_keywords)
        ]
        assert len(admin_routes) >= 5, \
            f"Should find admin-related routes, found {len(admin_routes)}"

    def test_v2_endpoints(self, autogpt_path: str) -> None:
        """Test that API endpoints are extracted from v2 features."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check that routes from v2 features are extracted
        # Note: Prefix application requires import resolution (future enhancement)
        v2_keywords = ["graph", "block", "execution", "library", "agent"]
        v2_routes = [p for p in paths if any(kw in p.lower() for kw in v2_keywords)]

        assert len(v2_routes) >= 10, \
            f"Should find v2 feature routes, found {len(v2_routes)}"

    def test_source_tracking(self, autogpt_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".py")
            assert ep.source_line is not None
            assert ep.source_line > 0

    def test_health_endpoint(self, autogpt_path: str) -> None:
        """Test that health check endpoint is found."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # @app.get(path="/health", ...) - may have prefix depending on app structure
        health_endpoints = [p for p in paths if "health" in p.lower()]
        assert len(health_endpoints) > 0, "Should find health check endpoint(s)"

    def test_oauth_endpoints(self, autogpt_path: str) -> None:
        """Test that OAuth endpoints are extracted."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # app.include_router(...oauth.router, prefix="/api/oauth")
        oauth_routes = [p for p in paths if "oauth" in p.lower()]
        assert len(oauth_routes) > 0, "Should find OAuth-related routes"

    def test_router_prefix_extraction(self, autogpt_path: str) -> None:
        """Test that include_router prefixes are extracted."""
        extractor = FastAPIExtractor()
        result = extractor.extract(autogpt_path)

        assert result.success

        # Verify router prefix mappings were extracted
        assert len(extractor.router_include_prefixes) >= 4, \
            f"Should extract multiple router prefixes, found {len(extractor.router_include_prefixes)}"

        # Check for expected prefixes
        prefix_values = set(extractor.router_include_prefixes.values())
        assert "/api/integrations" in prefix_values, "Should find /api/integrations prefix"
