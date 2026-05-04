"""Integration tests for Fastify extractor with @fastify/autoload support (fastify/demo)."""

import os
import pytest
from api_extractor.extractors.javascript.fastify import FastifyExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def fastify_demo_path():
    """Get path to fastify/demo real-world fixture."""
    return os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "javascript",
        "fastify",
        "fastify-demo",
        "src"
    )


def test_fastify_demo_autoload_detection(fastify_demo_path):
    """Test that @fastify/autoload registrations are detected.

    This tests against fastify/demo from:
    https://github.com/fastify/demo

    Expected: Routes are automatically loaded from src/routes/ directory
    using @fastify/autoload plugin.
    """
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on Fastify demo"
    assert len(result.endpoints) > 0, "Should find endpoints in Fastify demo"

    # Create lookup dict for easier assertions
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Home route
    assert ("/", HTTPMethod.GET) in paths, "Should find home endpoint"

    # API routes
    assert ("/api", HTTPMethod.GET) in paths, "Should find /api endpoint"


def test_fastify_demo_autoload_api_routes(fastify_demo_path):
    """Test that API routes under /api are extracted with correct prefixes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Create lookup dict
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Auth routes
    assert ("/api/auth/login", HTTPMethod.POST) in paths, "Should find POST /api/auth/login"

    # Task routes
    assert ("/api/tasks", HTTPMethod.GET) in paths, "Should find GET /api/tasks"
    assert ("/api/tasks", HTTPMethod.POST) in paths, "Should find POST /api/tasks"
    assert ("/api/tasks/{id}", HTTPMethod.PATCH) in paths, "Should find PATCH /api/tasks/{id}"
    assert ("/api/tasks/{id}", HTTPMethod.DELETE) in paths, "Should find DELETE /api/tasks/{id}"

    # User routes
    assert ("/api/users/update-password", HTTPMethod.PUT) in paths, "Should find PUT /api/users/update-password"


def test_fastify_demo_autoload_prefix_calculation(fastify_demo_path):
    """Test that URL prefixes are correctly calculated from directory structure."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # All /api/* routes should have /api prefix
    api_routes = [ep for ep in result.endpoints if ep.path.startswith("/api")]
    assert len(api_routes) > 0, "Should find routes with /api prefix"

    # Check specific prefixes
    for endpoint in result.endpoints:
        if "auth" in endpoint.source_file:
            assert endpoint.path.startswith("/api/auth"), f"Auth routes should have /api/auth prefix: {endpoint.path}"
        elif "tasks" in endpoint.source_file:
            assert endpoint.path.startswith("/api/tasks"), f"Task routes should have /api/tasks prefix: {endpoint.path}"
        elif "users" in endpoint.source_file:
            assert endpoint.path.startswith("/api/users"), f"User routes should have /api/users prefix: {endpoint.path}"


def test_fastify_demo_autoload_http_methods(fastify_demo_path):
    """Test that various HTTP methods are extracted from autoloaded routes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    methods_found = {ep.method for ep in result.endpoints}

    # Should have multiple HTTP methods
    assert HTTPMethod.GET in methods_found, "Should find GET endpoints"
    assert HTTPMethod.POST in methods_found, "Should find POST endpoints"
    assert HTTPMethod.PUT in methods_found, "Should find PUT endpoints"
    assert HTTPMethod.PATCH in methods_found, "Should find PATCH endpoints"
    assert HTTPMethod.DELETE in methods_found, "Should find DELETE endpoints"


def test_fastify_demo_autoload_path_parameters(fastify_demo_path):
    """Test that path parameters are correctly extracted from autoloaded routes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Find endpoints with path parameters
    id_endpoints = [ep for ep in result.endpoints if "{id}" in ep.path]
    assert len(id_endpoints) >= 2, "Should find at least 2 endpoints with {id} parameter"

    # Check task endpoints with ID
    task_id_endpoints = [ep for ep in id_endpoints if ep.path.startswith("/api/tasks/")]
    assert len(task_id_endpoints) >= 2, "Should find task endpoints with ID parameter"

    # Verify parameters are extracted
    for endpoint in task_id_endpoints:
        id_params = [p for p in endpoint.parameters if p.name == "id"]
        assert len(id_params) == 1, f"Endpoint {endpoint.path} should have id parameter"
        assert id_params[0].location.value == "path", "ID should be a path parameter"


def test_fastify_demo_autoload_source_tracking(fastify_demo_path):
    """Test that source file and line information is preserved for autoloaded routes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    for endpoint in result.endpoints:
        # Should have source file
        assert endpoint.source_file is not None, f"Endpoint {endpoint.path} should have source file"
        assert endpoint.source_file.endswith((".ts", ".js")), "Source file should be .ts or .js"

        # Should have source line
        assert endpoint.source_line is not None, f"Endpoint {endpoint.path} should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"

        # Source file should be within src/routes/
        assert "routes" in endpoint.source_file, f"Source file should be in routes/ directory: {endpoint.source_file}"


def test_fastify_demo_autoload_no_duplicate_routes(fastify_demo_path):
    """Test that autoload doesn't create duplicate routes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Check for duplicates
    seen = set()
    duplicates = []

    for endpoint in result.endpoints:
        key = (endpoint.path, endpoint.method.value)
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    assert len(duplicates) == 0, f"Should not have duplicate routes: {duplicates}"


def test_fastify_demo_autoload_index_files(fastify_demo_path):
    """Test that index.ts files are correctly handled with directory-based prefixes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Find endpoints from index.ts files
    index_endpoints = [ep for ep in result.endpoints if "index.ts" in ep.source_file]
    assert len(index_endpoints) > 0, "Should find routes from index.ts files"

    # Check that index endpoints have correct prefixes based on directory
    for endpoint in index_endpoints:
        if "api/auth" in endpoint.source_file:
            assert endpoint.path.startswith("/api/auth"), "Auth index should have /api/auth prefix"
        elif "api/tasks" in endpoint.source_file:
            assert endpoint.path.startswith("/api/tasks"), "Tasks index should have /api/tasks prefix"
        elif "api/users" in endpoint.source_file:
            assert endpoint.path.startswith("/api/users"), "Users index should have /api/users prefix"


def test_fastify_demo_autoload_autohooks_ignored(fastify_demo_path):
    """Test that autohooks.ts files are not processed as route files."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Check that no endpoints claim to be from autohooks files
    autohooks_endpoints = [ep for ep in result.endpoints if "autohooks" in ep.source_file]
    assert len(autohooks_endpoints) == 0, "Autohooks files should not be processed as routes"
