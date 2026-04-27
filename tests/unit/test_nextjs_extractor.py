"""Unit tests for Next.js extractor."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api_extractor.core.models import FrameworkType, HTTPMethod
from api_extractor.extractors.javascript.nextjs import NextJSExtractor


class TestNextJSExtractor:
    """Test Next.js route extraction."""

    @pytest.fixture
    def extractor(self) -> NextJSExtractor:
        """Create extractor instance."""
        return NextJSExtractor()

    def test_framework_type(self, extractor: NextJSExtractor) -> None:
        """Test framework type is correct."""
        assert extractor.framework == FrameworkType.NEXTJS

    def test_file_extensions(self, extractor: NextJSExtractor) -> None:
        """Test supported file extensions."""
        extensions = extractor.get_file_extensions()
        assert ".ts" in extensions
        assert ".js" in extensions
        assert ".tsx" in extensions
        assert ".jsx" in extensions

    def test_detect_router_type_app(self, extractor: NextJSExtractor) -> None:
        """Test App Router detection."""
        app_path = "/project/app/api/users/route.ts"
        assert extractor._detect_router_type(app_path) == "app"

    def test_detect_router_type_pages(self, extractor: NextJSExtractor) -> None:
        """Test Pages Router detection."""
        pages_path = "/project/pages/api/users.ts"
        assert extractor._detect_router_type(pages_path) == "pages"

    def test_detect_router_type_unknown(self, extractor: NextJSExtractor) -> None:
        """Test unknown file detection."""
        unknown_path = "/project/src/components/Header.tsx"
        assert extractor._detect_router_type(unknown_path) == "unknown"

    def test_derive_route_path_app_simple(self, extractor: NextJSExtractor) -> None:
        """Test App Router path derivation for simple route."""
        file_path = "/project/app/api/users/route.ts"
        assert extractor._derive_route_path_app(file_path) == "/api/users"

    def test_derive_route_path_app_dynamic(self, extractor: NextJSExtractor) -> None:
        """Test App Router path derivation for dynamic route."""
        file_path = "/project/app/api/users/[id]/route.ts"
        assert extractor._derive_route_path_app(file_path) == "/api/users/:id"

    def test_derive_route_path_app_nested_dynamic(self, extractor: NextJSExtractor) -> None:
        """Test App Router path derivation for nested dynamic route."""
        file_path = "/project/app/api/users/[userId]/posts/[postId]/route.ts"
        expected = "/api/users/:userId/posts/:postId"
        assert extractor._derive_route_path_app(file_path) == expected

    def test_derive_route_path_app_catch_all(self, extractor: NextJSExtractor) -> None:
        """Test App Router path derivation for catch-all route."""
        file_path = "/project/app/api/posts/[...slug]/route.ts"
        assert extractor._derive_route_path_app(file_path) == "/api/posts/:...slug"

    def test_derive_route_path_app_root(self, extractor: NextJSExtractor) -> None:
        """Test App Router path derivation for root API route."""
        file_path = "/project/app/api/route.ts"
        assert extractor._derive_route_path_app(file_path) == "/api"

    def test_derive_route_path_pages_simple(self, extractor: NextJSExtractor) -> None:
        """Test Pages Router path derivation for simple route."""
        file_path = "/project/pages/api/users.ts"
        assert extractor._derive_route_path_pages(file_path) == "/api/users"

    def test_derive_route_path_pages_dynamic(self, extractor: NextJSExtractor) -> None:
        """Test Pages Router path derivation for dynamic route."""
        file_path = "/project/pages/api/users/[id].ts"
        assert extractor._derive_route_path_pages(file_path) == "/api/users/:id"

    def test_derive_route_path_pages_nested_dynamic(self, extractor: NextJSExtractor) -> None:
        """Test Pages Router path derivation for nested dynamic route."""
        file_path = "/project/pages/api/users/[userId]/posts/[postId].ts"
        expected = "/api/users/:userId/posts/:postId"
        assert extractor._derive_route_path_pages(file_path) == expected

    def test_derive_route_path_pages_catch_all(self, extractor: NextJSExtractor) -> None:
        """Test Pages Router path derivation for catch-all route."""
        file_path = "/project/pages/api/posts/[...slug].ts"
        assert extractor._derive_route_path_pages(file_path) == "/api/posts/:...slug"

    def test_derive_route_path_pages_index(self, extractor: NextJSExtractor) -> None:
        """Test Pages Router path derivation for index route."""
        file_path = "/project/pages/api/index.ts"
        assert extractor._derive_route_path_pages(file_path) == "/api"

    def test_derive_route_path_pages_nested_index(self, extractor: NextJSExtractor) -> None:
        """Test Pages Router path derivation for nested index route."""
        file_path = "/project/pages/api/users/index.ts"
        assert extractor._derive_route_path_pages(file_path) == "/api/users"

    def test_extract_http_methods_from_body_single(self, extractor: NextJSExtractor) -> None:
        """Test HTTP method extraction for single method."""
        body_text = b"""
        if (req.method === 'GET') {
            res.status(200).json({ users: [] });
        }
        """
        # Create a mock node
        class MockNode:
            def __init__(self, text):
                self.text = text
                self.children = []

        mock_node = MockNode(body_text)
        extractor.parser.get_node_text = lambda node, source: body_text.decode()

        methods = extractor._extract_http_methods_from_body(mock_node, body_text)
        assert HTTPMethod.GET in methods
        assert len(methods) == 1

    def test_extract_http_methods_from_body_multiple(self, extractor: NextJSExtractor) -> None:
        """Test HTTP method extraction for multiple methods."""
        body_text = b"""
        if (req.method === 'GET') {
            res.status(200).json({ users: [] });
        }
        if (req.method === 'POST') {
            res.status(201).json({ success: true });
        }
        if (req.method === 'DELETE') {
            res.status(204).send();
        }
        """
        class MockNode:
            def __init__(self, text):
                self.text = text
                self.children = []

        mock_node = MockNode(body_text)
        extractor.parser.get_node_text = lambda node, source: body_text.decode()

        methods = extractor._extract_http_methods_from_body(mock_node, body_text)
        assert HTTPMethod.GET in methods
        assert HTTPMethod.POST in methods
        assert HTTPMethod.DELETE in methods
        assert len(methods) == 3

    def test_extract_http_methods_from_body_double_equals(self, extractor: NextJSExtractor) -> None:
        """Test HTTP method extraction with == operator."""
        body_text = b"""
        if (req.method == 'PUT') {
            res.status(200).json({ success: true });
        }
        """
        class MockNode:
            def __init__(self, text):
                self.text = text
                self.children = []

        mock_node = MockNode(body_text)
        extractor.parser.get_node_text = lambda node, source: body_text.decode()

        methods = extractor._extract_http_methods_from_body(mock_node, body_text)
        assert HTTPMethod.PUT in methods

    def test_extract_http_methods_from_body_default_get(self, extractor: NextJSExtractor) -> None:
        """Test HTTP method extraction defaults to GET when none found."""
        body_text = b"""
        const users = await db.users.findMany();
        res.status(200).json({ users });
        """
        class MockNode:
            def __init__(self, text):
                self.text = text
                self.children = []

        mock_node = MockNode(body_text)
        extractor.parser.get_node_text = lambda node, source: body_text.decode()

        methods = extractor._extract_http_methods_from_body(mock_node, body_text)
        assert HTTPMethod.GET in methods
        assert len(methods) == 1

    def test_normalize_path_simple(self, extractor: NextJSExtractor) -> None:
        """Test path normalization for simple path."""
        assert extractor._normalize_path("/api/users") == "/api/users"

    def test_normalize_path_dynamic(self, extractor: NextJSExtractor) -> None:
        """Test path normalization for dynamic parameter."""
        assert extractor._normalize_path("/api/users/:id") == "/api/users/{id}"

    def test_normalize_path_multiple_params(self, extractor: NextJSExtractor) -> None:
        """Test path normalization for multiple parameters."""
        path = "/api/users/:userId/posts/:postId"
        expected = "/api/users/{userId}/posts/{postId}"
        assert extractor._normalize_path(path) == expected

    def test_normalize_path_catch_all(self, extractor: NextJSExtractor) -> None:
        """Test path normalization for catch-all parameter."""
        assert extractor._normalize_path("/api/posts/:...slug") == "/api/posts/{slug}"

    def test_extract_path_parameters_simple(self, extractor: NextJSExtractor) -> None:
        """Test path parameter extraction for simple parameter."""
        params = extractor._extract_path_parameters("/api/users/:id")
        assert len(params) == 1
        assert params[0].name == "id"
        assert params[0].type == "string"
        assert params[0].required is True

    def test_extract_path_parameters_multiple(self, extractor: NextJSExtractor) -> None:
        """Test path parameter extraction for multiple parameters."""
        params = extractor._extract_path_parameters("/api/users/:userId/posts/:postId")
        assert len(params) == 2
        assert params[0].name == "userId"
        assert params[1].name == "postId"

    def test_extract_path_parameters_catch_all(self, extractor: NextJSExtractor) -> None:
        """Test path parameter extraction for catch-all parameter."""
        params = extractor._extract_path_parameters("/api/posts/:...slug")
        assert len(params) == 1
        assert params[0].name == "slug"
        assert params[0].type == "array"
        assert params[0].required is True
        assert "catch-all" in params[0].description.lower()


class TestNextJSExtractorIntegration:
    """Integration tests with real fixture files."""

    @pytest.fixture
    def extractor(self) -> NextJSExtractor:
        """Create extractor instance."""
        return NextJSExtractor()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "minimal"

    def test_extract_app_router_basic(self, extractor: NextJSExtractor, fixtures_dir: Path) -> None:
        """Test extraction from App Router basic endpoint."""
        fixture_path = fixtures_dir / "nextjs-app" / "app" / "api" / "users" / "route.ts"
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        routes = extractor.extract_routes_from_file(str(fixture_path))

        assert len(routes) == 2  # GET and POST
        paths = {route.path for route in routes}
        methods = {method for route in routes for method in route.methods}

        assert "/api/users" in paths
        assert HTTPMethod.GET in methods
        assert HTTPMethod.POST in methods

    def test_extract_app_router_dynamic(
        self, extractor: NextJSExtractor, fixtures_dir: Path
    ) -> None:
        """Test extraction from App Router dynamic route."""
        fixture_path = (
            fixtures_dir / "nextjs-app" / "app" / "api" / "users" / "[id]" / "route.ts"
        )
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        routes = extractor.extract_routes_from_file(str(fixture_path))

        assert len(routes) == 3  # GET, PUT, DELETE
        paths = {route.path for route in routes}
        methods = {method for route in routes for method in route.methods}

        assert "/api/users/:id" in paths
        assert HTTPMethod.GET in methods
        assert HTTPMethod.PUT in methods
        assert HTTPMethod.DELETE in methods

    def test_extract_pages_router_basic(
        self, extractor: NextJSExtractor, fixtures_dir: Path
    ) -> None:
        """Test extraction from Pages Router basic endpoint."""
        fixture_path = fixtures_dir / "nextjs-pages" / "pages" / "api" / "products.ts"
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        routes = extractor.extract_routes_from_file(str(fixture_path))

        assert len(routes) == 2  # GET and POST
        paths = {route.path for route in routes}
        methods = {method for route in routes for method in route.methods}

        assert "/api/products" in paths
        assert HTTPMethod.GET in methods
        assert HTTPMethod.POST in methods

    def test_extract_pages_router_dynamic(
        self, extractor: NextJSExtractor, fixtures_dir: Path
    ) -> None:
        """Test extraction from Pages Router dynamic route."""
        fixture_path = (
            fixtures_dir / "nextjs-pages" / "pages" / "api" / "products" / "[slug].ts"
        )
        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        routes = extractor.extract_routes_from_file(str(fixture_path))

        assert len(routes) == 3  # GET, PUT, DELETE
        paths = {route.path for route in routes}
        methods = {method for route in routes for method in route.methods}

        assert "/api/products/:slug" in paths
        assert HTTPMethod.GET in methods
        assert HTTPMethod.PUT in methods
        assert HTTPMethod.DELETE in methods

    def test_full_extraction_app_router(
        self, extractor: NextJSExtractor, fixtures_dir: Path
    ) -> None:
        """Test full extraction pipeline on App Router fixture."""
        fixture_path = fixtures_dir / "nextjs-app"
        if not fixture_path.exists():
            pytest.skip("Fixture directory not found")

        result = extractor.extract(str(fixture_path))

        assert result.success is True
        assert len(result.endpoints) >= 5  # 2 from users + 3 from users/[id]
        assert result.frameworks_detected == [FrameworkType.NEXTJS]

        # Check endpoint details
        paths = {ep.path for ep in result.endpoints}
        assert "/api/users" in paths
        assert "/api/users/{id}" in paths

    def test_full_extraction_pages_router(
        self, extractor: NextJSExtractor, fixtures_dir: Path
    ) -> None:
        """Test full extraction pipeline on Pages Router fixture."""
        fixture_path = fixtures_dir / "nextjs-pages"
        if not fixture_path.exists():
            pytest.skip("Fixture directory not found")

        result = extractor.extract(str(fixture_path))

        assert result.success is True
        assert len(result.endpoints) >= 5  # 2 from products + 3 from products/[slug]
        assert result.frameworks_detected == [FrameworkType.NEXTJS]

        # Check endpoint details
        paths = {ep.path for ep in result.endpoints}
        assert "/api/products" in paths
        assert "/api/products/{slug}" in paths
