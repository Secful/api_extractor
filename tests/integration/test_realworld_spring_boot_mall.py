"""Integration tests for Spring Boot extractor with mall."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.java.spring_boot import SpringBootExtractor


@pytest.fixture
def mall_path():
    """Get path to mall fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "mall",
    )
    if not os.path.exists(path):
        pytest.skip("mall fixture not available (run: git submodule update --init)")
    return path


class TestSpringBootMall:
    """Integration tests for mall e-commerce platform."""

    def test_extraction(self, mall_path: str) -> None:
        """Test extraction from mall.

        Repository: https://github.com/macrozheng/mall
        Domain: E-commerce Platform (Front Store + Backend Management)
        """
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count (exact match per coding standards)
        assert len(result.endpoints) == 246, \
            f"Expected exactly 246 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, mall_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"

    def test_unique_paths(self, mall_path: str) -> None:
        """Test that correct number of unique paths are found."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success

        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) == 239, \
            f"Expected exactly 239 unique paths, found {len(unique_paths)}"

    def test_product_endpoints(self, mall_path: str) -> None:
        """Test that product management endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Product management
        assert any("product" in p for p in paths), "Should find product endpoints"
        product_endpoints = [ep for ep in result.endpoints if "product" in ep.path.lower()]
        assert len(product_endpoints) >= 10, \
            f"Expected at least 10 product endpoints, found {len(product_endpoints)}"

    def test_order_endpoints(self, mall_path: str) -> None:
        """Test that order management endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Order management
        assert any("order" in p for p in paths), "Should find order endpoints"
        order_endpoints = [ep for ep in result.endpoints if "order" in ep.path.lower()]
        assert len(order_endpoints) >= 5, \
            f"Expected at least 5 order endpoints, found {len(order_endpoints)}"

    def test_brand_endpoints(self, mall_path: str) -> None:
        """Test that brand management endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Brand management
        assert any("brand" in p for p in paths), "Should find brand endpoints"

    def test_member_endpoints(self, mall_path: str) -> None:
        """Test that member/user endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Member management
        assert any("member" in p for p in paths), "Should find member endpoints"

    def test_coupon_endpoints(self, mall_path: str) -> None:
        """Test that promotion/coupon endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Promotion/coupon system
        assert any("coupon" in p for p in paths), "Should find coupon endpoints"

    def test_return_management_endpoints(self, mall_path: str) -> None:
        """Test that return/refund management endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Return/refund management
        assert any("return" in p.lower() for p in paths), "Should find return endpoints"
        assert "/returnApply/list" in paths, "Should find return application list"
        assert any("returnReason" in p for p in paths), "Should find return reason endpoints"

    def test_flash_sale_endpoints(self, mall_path: str) -> None:
        """Test that flash sale endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Flash sales
        assert any("flashSession" in p or "flash" in p.lower() for p in paths), \
            "Should find flash sale endpoints"

    def test_cms_endpoints(self, mall_path: str) -> None:
        """Test that CMS/content endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # CMS content
        assert any("subject" in p for p in paths), "Should find subject/topic endpoints"
        assert "/subject/listAll" in paths or "/subject/list" in paths, \
            "Should find subject list endpoint"

    def test_role_endpoints(self, mall_path: str) -> None:
        """Test that role management endpoints are extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Role management
        assert any("role" in p for p in paths), "Should find role endpoints"

    def test_path_parameters(self, mall_path: str) -> None:
        """Test that path parameters are properly extracted."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 86, \
            f"Expected exactly 86 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify OpenAPI format {param}
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path, \
                f"Path parameter should use OpenAPI format: {ep.path}"

    def test_source_tracking(self, mall_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".java"), \
                f"Expected .java file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_multi_module_extraction(self, mall_path: str) -> None:
        """Test that endpoints are extracted from multiple Maven modules."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success

        # Check that we have endpoints from different modules
        source_files = {ep.source_file for ep in result.endpoints if ep.source_file}

        # Should have files from admin, portal, or other modules
        modules_found = set()
        for source_file in source_files:
            if "mall-admin" in source_file:
                modules_found.add("admin")
            elif "mall-portal" in source_file:
                modules_found.add("portal")
            elif "mall-search" in source_file:
                modules_found.add("search")

        assert len(modules_found) >= 1, \
            f"Should extract from at least one module, found: {modules_found}"

    def test_large_scale_extraction(self, mall_path: str) -> None:
        """Test that extractor handles large codebases efficiently."""
        extractor = SpringBootExtractor()
        result = extractor.extract(mall_path)

        assert result.success

        # Verify substantial number of endpoints
        assert len(result.endpoints) >= 200, \
            f"Expected at least 200 endpoints for large e-commerce platform"

        # Verify unique paths
        unique_paths = set(ep.path for ep in result.endpoints)
        assert len(unique_paths) >= 200, \
            f"Expected at least 200 unique paths"
