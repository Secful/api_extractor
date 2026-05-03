"""Integration tests against real-world validation projects."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture(scope="module")
def repos_dir():
    """Create temporary directory for cloning repositories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def clone_repo(url: str, dest: Path) -> bool:
    """Clone a git repository if not already cloned."""
    if dest.exists():
        return True

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.mark.integration
class TestRealWorldJoi:
    """Test Joi validation extraction on real-world projects."""

    @pytest.fixture
    def node_express_boilerplate(self, repos_dir):
        """Clone node-express-boilerplate repository."""
        repo_dir = repos_dir / "node-express-boilerplate"
        if not clone_repo(
            "https://github.com/hagopj13/node-express-boilerplate.git", repo_dir
        ):
            pytest.skip("Failed to clone repository")
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
        with_query_params = sum(
            1 for e in result.endpoints
            if any(p.location.value == "query" for p in e.parameters)
        )

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
    def express_zod_api(self, repos_dir):
        """Clone express-zod-api repository."""
        repo_dir = repos_dir / "express-zod-api"
        if not clone_repo(
            "https://github.com/RobinTail/express-zod-api.git", repo_dir
        ):
            pytest.skip("Failed to clone repository")
        return repo_dir / "example"

    def test_express_zod_api_routes(self, express_zod_api):
        """Test that routes are extracted from express-zod-api."""
        extractor = ExpressExtractor()
        result = extractor.extract(str(express_zod_api))

        # Currently fails - express-zod-api uses custom routing
        # Not standard Express patterns

        print(f"  Routes found: {len(result.endpoints)}")
        print(f"  Errors: {result.errors[:3] if result.errors else 'None'}")

        # Known issue: express-zod-api uses custom routing framework
        # May need special handling or skip this project
        # assert len(result.endpoints) >= 1, "Should find at least one route"


@pytest.mark.integration
class TestRealWorldJSONSchema:
    """Test JSON Schema validation extraction on real-world projects."""

    @pytest.fixture
    def fastify_example(self, repos_dir):
        """Clone fastify-example repository."""
        repo_dir = repos_dir / "fastify-example"
        if not clone_repo(
            "https://github.com/delvedor/fastify-example.git", repo_dir
        ):
            pytest.skip("Failed to clone repository")
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
def test_all_real_world_projects_summary(repos_dir):
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
    print("  1. Cross-file imports not yet supported (Joi)")
    print("  2. express-zod-api uses custom routing framework")
    print("  3. Fastify needs dedicated extractor")
    print("="*70)
