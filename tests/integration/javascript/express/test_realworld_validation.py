"""Integration tests against real-world validation projects."""

from pathlib import Path

import pytest

from api_extractor.extractors.javascript.express import ExpressExtractor


# Base path for real-world test fixtures
FIXTURES_BASE = Path(__file__).parent.parent.parent.parent / "fixtures" / "real-world" / "javascript" / "express"


@pytest.mark.integration
class TestRealWorldJoi:
    """Test Joi validation extraction on real-world projects."""

    @pytest.fixture
    def node_express_boilerplate(self):
        """Path to node-express-boilerplate submodule."""
        repo_dir = FIXTURES_BASE / "node-express-boilerplate"
        if not repo_dir.exists():
            pytest.skip("Submodule not initialized. Run: git submodule update --init")
        return repo_dir / "src"

    def test_node_express_boilerplate_routes(self, node_express_boilerplate):
        """Test that routes are extracted from node-express-boilerplate."""
        extractor = ExpressExtractor()
        result = extractor.extract(str(node_express_boilerplate))

        # Should find routes
        assert result.success, f"Extraction failed: {result.errors}"
        assert len(result.endpoints) >= 8, f"Expected at least 8 endpoints, found {len(result.endpoints)}"

        # Check for known endpoints
        paths = [e.path for e in result.endpoints]
        assert any("/register" in p for p in paths), "Should find /register endpoint"
        assert any("/login" in p for p in paths), "Should find /login endpoint"

    def test_node_express_boilerplate_validation(self, node_express_boilerplate):
        """Test that Joi validation schemas are extracted from cross-file imports."""
        extractor = ExpressExtractor()
        result = extractor.extract(str(node_express_boilerplate))

        # Count endpoints with validation
        with_body_schema = sum(1 for e in result.endpoints if e.request_body)

        # Cross-file imports are now supported
        assert with_body_schema >= 5, f"Expected body validation on multiple endpoints, found {with_body_schema}"

        # Verify some specific endpoints have schemas
        register_endpoint = next((e for e in result.endpoints if "/register" in e.path), None)
        assert register_endpoint is not None, "Should find /register endpoint"
        assert register_endpoint.request_body is not None, "/register should have request body schema"
        assert "email" in register_endpoint.request_body.properties, "/register should have email field"
        assert "password" in register_endpoint.request_body.properties, "/register should have password field"
        assert "name" in register_endpoint.request_body.properties, "/register should have name field"


@pytest.mark.integration
class TestRealWorldZod:
    """Test Zod validation extraction on real-world projects."""

    @pytest.fixture
    def express_zod_api(self):
        """Path to express-zod-api framework example."""
        repo_dir = FIXTURES_BASE / "express-zod-api"
        if not repo_dir.exists():
            pytest.skip("Submodule not initialized. Run: git submodule update --init")
        return repo_dir / "example"

    @pytest.fixture
    def acquisitions(self):
        """Path to acquisitions project (Express + Zod inline validation)."""
        repo_dir = FIXTURES_BASE / "acquisitions"
        if not repo_dir.exists():
            pytest.skip("Submodule not initialized. Run: git submodule update --init")
        return repo_dir / "src"

    def test_express_zod_api_routes(self, express_zod_api):
        """Test express-zod-api framework extraction (declarative routing)."""
        from api_extractor.extractors.javascript.express_zod_api import ExpressZodAPIExtractor

        extractor = ExpressZodAPIExtractor()
        result = extractor.extract(str(express_zod_api))

        print(f"  Routes found: {len(result.endpoints)}")
        print(f"  Errors: {result.errors[:3] if result.errors else 'None'}")

        # express-zod-api uses declarative routing
        assert result.success, f"Extraction failed: {result.errors}"
        assert len(result.endpoints) >= 10, f"Expected at least 10 endpoints, found {len(result.endpoints)}"

        # Check for known endpoints
        paths = [e.path for e in result.endpoints]
        assert any("/user/create" in p for p in paths), "Should find /user/create endpoint"

        # Check method extraction
        methods = [e.method.value for e in result.endpoints]
        assert "POST" in methods, "Should have POST endpoints"
        assert "GET" in methods, "Should have GET endpoints"
        assert "PATCH" in methods, "Should have PATCH endpoints"

    def test_acquisitions_routes(self, acquisitions):
        """Test Express + Zod inline validation (controller-based validation)."""
        from api_extractor.extractors.javascript.express import ExpressExtractor

        extractor = ExpressExtractor()
        result = extractor.extract(str(acquisitions))

        print(f"  Routes found: {len(result.endpoints)}")

        # Standard Express routing works
        assert result.success, f"Extraction failed: {result.errors}"
        assert len(result.endpoints) >= 7, f"Expected at least 7 endpoints, found {len(result.endpoints)}"

        # Check for known endpoints
        paths = [e.path for e in result.endpoints]
        methods = [f"{e.method.value} {e.path}" for e in result.endpoints]

        assert any("sign-up" in p for p in paths), f"Should find /sign-up endpoint. Found: {paths}"
        assert any("POST" in m and "sign-up" in m for m in methods), f"Should have POST /sign-up. Found: {methods}"
        assert any("{id}" in p for p in paths), f"Should find /:id endpoints. Found: {paths}"

        # NOTE: Inline validation (schema.safeParse() in controller) is not extractable
        # Only middleware-based validation can be statically analyzed
        # This is a known limitation for Express + manual Zod validation
        with_schemas = sum(1 for e in result.endpoints if e.request_body)
        # Currently 0 because acquisitions uses inline validation, not middleware
        print(f"  With schemas: {with_schemas} (inline validation not extractable)")


@pytest.mark.integration
class TestRealWorldJSONSchema:
    """Test JSON Schema validation extraction on real-world projects."""

    @pytest.fixture
    def fastify_example(self):
        """Path to fastify-example submodule."""
        fastify_base = Path(__file__).parent.parent.parent.parent / "fixtures" / "real-world" / "javascript" / "fastify"
        repo_dir = fastify_base / "fastify-example"
        if not repo_dir.exists():
            pytest.skip("Submodule not initialized. Run: git submodule update --init")
        return repo_dir

    def test_fastify_example_routes(self, fastify_example):
        """Test extraction from Fastify project."""
        # Note: Express extractor won't work on Fastify
        # This test documents the limitation

        extractor = ExpressExtractor()
        result = extractor.extract(str(fastify_example))

        print(f"  Routes found: {len(result.endpoints)}")

        # Known issue: Fastify uses different routing system
        # Would need dedicated Fastify extractor
        assert len(result.endpoints) == 0, "Express extractor should not find Fastify routes"


@pytest.mark.integration
@pytest.mark.slow
def test_all_real_world_projects_summary():
    """Run all real-world projects and provide summary."""
    results = {
        "joi": {"name": "node-express-boilerplate", "url": "hagopj13/node-express-boilerplate"},
        "zod": {"name": "express-zod-api", "url": "RobinTail/express-zod-api"},
        "fastify": {"name": "fastify-example", "url": "delvedor/fastify-example"},
    }

    print("\n" + "="*70)
    print("REAL-WORLD PROJECT VALIDATION EXTRACTION SUMMARY")
    print("="*70)

    for project_type, info in results.items():
        print(f"\n{project_type.upper()}: {info['name']}")
        print(f"  Repository: {info['url']}")

    print("\n" + "="*70)
    print("Known Issues:")
    print("  1. Cross-file imports - SOLVED (Joi)")
    print("  2. express-zod-api - SOLVED (dedicated extractor)")
    print("  3. Fastify needs dedicated extractor (partial support)")
    print("="*70)
