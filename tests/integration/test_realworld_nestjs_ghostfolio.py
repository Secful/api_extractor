"""Integration tests for NestJS extractor with Ghostfolio."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.nestjs import NestJSExtractor


@pytest.fixture
def ghostfolio_path():
    """Get path to Ghostfolio fixture (monorepo /apps/api directory)."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "javascript",
        "nestjs",
        "ghostfolio",
        "apps",
        "api",
    )
    if not os.path.exists(path):
        pytest.skip("Ghostfolio fixture not available (run: git submodule update --init)")
    return path


class TestNestJSGhostfolio:
    """Integration tests for Ghostfolio wealth management platform."""

    def test_extraction(self, ghostfolio_path: str) -> None:
        """Test extraction from Ghostfolio.

        Repository: https://github.com/ghostfolio/ghostfolio
        Domain: Financial Technology (FinTech) - Portfolio & Wealth Management
        """
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count (exact match per coding standards)
        assert len(result.endpoints) == 113, \
            f"Expected exactly 113 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, ghostfolio_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"
        assert HTTPMethod.PATCH in methods, "Should find PATCH endpoints"

    def test_portfolio_endpoints(self, ghostfolio_path: str) -> None:
        """Test that portfolio management endpoints are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find portfolio endpoints
        portfolio_endpoints = [ep for ep in result.endpoints if "portfolio" in ep.path]
        assert len(portfolio_endpoints) == 9, \
            f"Expected exactly 9 portfolio endpoints, found {len(portfolio_endpoints)}"

        # Verify key portfolio paths exist
        paths = {ep.path for ep in result.endpoints}
        assert any("portfolio" in p for p in paths), "Should find portfolio endpoints"

    def test_admin_endpoints(self, ghostfolio_path: str) -> None:
        """Test that admin operation endpoints are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find admin endpoints
        admin_endpoints = [ep for ep in result.endpoints if "admin" in ep.path]
        assert len(admin_endpoints) == 20, \
            f"Expected exactly 20 admin endpoints, found {len(admin_endpoints)}"

        # Verify admin paths exist
        paths = {ep.path for ep in result.endpoints}
        assert "/admin" in paths, "Should find admin base endpoint"
        assert any("admin/gather" in p for p in paths), "Should find gather endpoints"
        assert any("admin/queue" in p for p in paths), "Should find queue management"

    def test_account_endpoints(self, ghostfolio_path: str) -> None:
        """Test that account management endpoints are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find account endpoints
        account_endpoints = [ep for ep in result.endpoints if "account" in ep.path]
        assert len(account_endpoints) == 9, \
            f"Expected exactly 9 account endpoints, found {len(account_endpoints)}"

        # Verify key account patterns
        paths = {ep.path for ep in result.endpoints}
        assert "/account" in paths, "Should find account listing endpoint"
        assert "/account/{id}" in paths, "Should find account detail endpoint"
        assert "/account/transfer-balance" in paths, "Should find transfer endpoint"

    def test_access_token_endpoints(self, ghostfolio_path: str) -> None:
        """Test that access token management endpoints are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find access endpoints
        access_endpoints = [ep for ep in result.endpoints if ep.path.startswith("/access")]
        assert len(access_endpoints) >= 3, \
            f"Expected at least 3 access endpoints, found {len(access_endpoints)}"

        paths = {ep.path for ep in result.endpoints}
        assert "/access" in paths, "Should find access token endpoint"

    def test_path_parameters(self, ghostfolio_path: str) -> None:
        """Test that path parameters are properly extracted in OpenAPI format."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 50, \
            f"Expected exactly 50 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify OpenAPI format (not NestJS :param format)
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path, \
                f"Path parameter should use OpenAPI format: {ep.path}"
            assert ":" not in ep.path.split("/")[-1], \
                f"Path should not contain NestJS :param format: {ep.path}"

        # Verify specific parameter patterns
        paths = {ep.path for ep in result.endpoints}
        assert any("{id}" in p for p in paths), "Should find {id} parameter"
        assert any("{dataSource}" in p for p in paths), "Should find {dataSource} parameter"
        assert any("{symbol}" in p for p in paths), "Should find {symbol} parameter"

    def test_complex_path_parameters(self, ghostfolio_path: str) -> None:
        """Test that complex multi-parameter paths are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find paths with multiple parameters
        multi_param_paths = [ep.path for ep in result.endpoints
                            if ep.path.count("{") >= 2]
        assert len(multi_param_paths) >= 10, \
            f"Expected at least 10 paths with multiple parameters, found {len(multi_param_paths)}"

        # Verify specific complex paths
        paths = {ep.path for ep in result.endpoints}
        assert any("{dataSource}/{symbol}" in p for p in paths), \
            "Should find paths with dataSource and symbol parameters"

    def test_source_tracking(self, ghostfolio_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".ts"), \
                f"Expected .ts file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_crud_operations(self, ghostfolio_path: str) -> None:
        """Test that full CRUD operations are detected."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Group by path to find CRUD patterns
        path_methods = {}
        for ep in result.endpoints:
            if ep.path not in path_methods:
                path_methods[ep.path] = set()
            path_methods[ep.path].add(ep.method)

        # Find paths with multiple methods (likely CRUD)
        multi_method_paths = [p for p, methods in path_methods.items() if len(methods) >= 2]
        assert len(multi_method_paths) >= 5, \
            f"Expected at least 5 paths with multiple methods, found {len(multi_method_paths)}"

    def test_market_data_endpoints(self, ghostfolio_path: str) -> None:
        """Test that market data endpoints are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find market data endpoints
        market_endpoints = [ep for ep in result.endpoints
                           if "market-data" in ep.path or "profile-data" in ep.path]
        assert len(market_endpoints) >= 5, \
            f"Expected at least 5 market data endpoints, found {len(market_endpoints)}"

    def test_gather_endpoints(self, ghostfolio_path: str) -> None:
        """Test that data gathering endpoints are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find gather endpoints (background job triggers)
        gather_endpoints = [ep for ep in result.endpoints if "gather" in ep.path]
        assert len(gather_endpoints) >= 5, \
            f"Expected at least 5 gather endpoints, found {len(gather_endpoints)}"

    def test_unique_paths(self, ghostfolio_path: str) -> None:
        """Test that correct number of unique paths are found."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) == 92, \
            f"Expected exactly 92 unique paths, found {len(unique_paths)}"

    def test_patch_method_support(self, ghostfolio_path: str) -> None:
        """Test that PATCH method is properly extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find PATCH endpoints
        patch_endpoints = [ep for ep in result.endpoints if ep.method == HTTPMethod.PATCH]
        assert len(patch_endpoints) >= 1, \
            f"Expected at least 1 PATCH endpoint, found {len(patch_endpoints)}"

    def test_delete_operations(self, ghostfolio_path: str) -> None:
        """Test that DELETE operations are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find DELETE endpoints
        delete_endpoints = [ep for ep in result.endpoints if ep.method == HTTPMethod.DELETE]
        assert len(delete_endpoints) >= 10, \
            f"Expected at least 10 DELETE endpoints, found {len(delete_endpoints)}"

    def test_root_endpoint(self, ghostfolio_path: str) -> None:
        """Test that root endpoint is extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        paths = {ep.path for ep in result.endpoints}
        assert "/" in paths, "Should find root endpoint"

    def test_balance_management_endpoints(self, ghostfolio_path: str) -> None:
        """Test that balance management endpoints are extracted."""
        extractor = NestJSExtractor()
        result = extractor.extract(ghostfolio_path)

        assert result.success

        # Find balance-related endpoints
        balance_endpoints = [ep for ep in result.endpoints if "balance" in ep.path]
        assert len(balance_endpoints) >= 3, \
            f"Expected at least 3 balance endpoints, found {len(balance_endpoints)}"
