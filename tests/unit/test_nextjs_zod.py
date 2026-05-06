"""Unit tests for Next.js + Zod integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from api_extractor.core.models import FrameworkType, HTTPMethod
from api_extractor.extractors.javascript.nextjs import NextJSExtractor


class TestNextJSZodIntegration:
    """Test Next.js with Zod validation schema extraction."""

    @pytest.fixture
    def extractor(self) -> NextJSExtractor:
        """Create extractor instance."""
        return NextJSExtractor()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "minimal" / "javascript" / "nextjs-zod"

    def test_extract_users_post_with_zod(self, extractor: NextJSExtractor, fixtures_dir: Path) -> None:
        """Test POST endpoint with Zod schema extraction."""
        fixture_path = fixtures_dir / "app" / "api" / "users" / "route.ts"

        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        routes = extractor.extract_routes_from_file(str(fixture_path))

        # Should find GET and POST
        assert len(routes) >= 2

        # Find POST route
        post_routes = [r for r in routes if HTTPMethod.POST in r.methods]
        assert len(post_routes) == 1

        post_route = post_routes[0]
        assert post_route.path == "/api/users"

        # Check if Zod schema was linked
        assert "request_body" in post_route.metadata
        request_body = post_route.metadata["request_body"]

        # Verify schema structure
        assert request_body is not None
        assert request_body.type == "object"
        assert request_body.properties is not None

        # Check for expected fields
        assert "name" in request_body.properties
        assert "email" in request_body.properties
        assert "age" in request_body.properties

        # Verify required fields
        assert "name" in request_body.required
        assert "email" in request_body.required

    def test_extract_users_put_with_zod(self, extractor: NextJSExtractor, fixtures_dir: Path) -> None:
        """Test PUT endpoint with Zod schema extraction."""
        fixture_path = fixtures_dir / "app" / "api" / "users" / "[id]" / "route.ts"

        if not fixture_path.exists():
            pytest.skip("Fixture file not found")

        routes = extractor.extract_routes_from_file(str(fixture_path))

        # Should find GET, PUT, DELETE
        assert len(routes) >= 3

        # Find PUT route
        put_routes = [r for r in routes if HTTPMethod.PUT in r.methods]
        assert len(put_routes) == 1

        put_route = put_routes[0]
        assert put_route.path == "/api/users/:id"

        # Check if Zod schema was linked
        assert "request_body" in put_route.metadata
        request_body = put_route.metadata["request_body"]

        # Verify schema structure
        assert request_body is not None
        assert request_body.type == "object"

    def test_full_extraction_with_zod(self, extractor: NextJSExtractor, fixtures_dir: Path) -> None:
        """Test full extraction pipeline with Zod schemas."""
        result = extractor.extract(str(fixtures_dir))

        assert result.success is True
        assert len(result.endpoints) >= 5  # GET /users, POST /users, GET /users/{id}, PUT /users/{id}, DELETE /users/{id}
        assert result.frameworks_detected == [FrameworkType.NEXTJS]

        # Check that at least some endpoints have request bodies (POST, PUT)
        endpoints_with_body = [ep for ep in result.endpoints if ep.request_body is not None]
        assert len(endpoints_with_body) >= 2, "Should find at least POST and PUT with request bodies"

        # Verify POST /api/users has schema
        post_users = [ep for ep in result.endpoints if ep.method == HTTPMethod.POST and "/users" in ep.path]
        assert len(post_users) >= 1
        post_endpoint = post_users[0]
        assert post_endpoint.request_body is not None
        assert post_endpoint.request_body.type == "object"
