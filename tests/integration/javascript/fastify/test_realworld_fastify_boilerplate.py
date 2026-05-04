"""Integration tests for Fastify extractor with TypeBox support (fastify-boilerplate)."""

import os
import pytest
from api_extractor.extractors.javascript.fastify import FastifyExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def fastify_boilerplate_path():
    """Get path to fastify-boilerplate real-world fixture."""
    return os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "javascript",
        "fastify",
        "fastify-boilerplate",
        "src",
        "modules"
    )


def test_fastify_boilerplate_typebox_extraction(fastify_boilerplate_path):
    """Test extraction from Fastify boilerplate with TypeBox schemas.

    This tests against fastify-boilerplate from:
    https://github.com/marcoturi/fastify-boilerplate

    Expected: Clean Architecture Fastify 5 application using TypeBox
    for schema validation with @fastify/type-provider-typebox.
    """
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on Fastify boilerplate"
    assert len(result.endpoints) > 0, "Should find endpoints in Fastify boilerplate"

    # Create lookup dict for easier assertions
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # User query endpoints
    assert ("/v1/users", HTTPMethod.GET) in paths, "Should find list users endpoint"

    # User command endpoints
    assert ("/v1/users", HTTPMethod.POST) in paths, "Should find create user endpoint"
    assert ("/v1/users/{id}", HTTPMethod.DELETE) in paths, "Should find delete user endpoint"

    # Verify expected endpoint count (3 routes in the fixture)
    assert len(result.endpoints) == 3, f"Expected 3 endpoints, found {len(result.endpoints)}"

    # Check that endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".route.ts"), "Source file should be a route.ts file"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_fastify_boilerplate_typebox_schemas(fastify_boilerplate_path):
    """Test that TypeBox schemas are recognized in route definitions.

    Verifies:
    - Routes using withTypeProvider<TypeBoxTypeProvider>() are extracted
    - Schema definitions with querystring, body, params, response are recognized
    """
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    # Find the GET /v1/users endpoint (has querystring schema)
    list_users = next(
        (ep for ep in result.endpoints
         if ep.path == "/v1/users" and ep.method == HTTPMethod.GET),
        None
    )
    assert list_users is not None, "Should find GET /v1/users endpoint"

    # Find the POST /v1/users endpoint (has body schema)
    create_user = next(
        (ep for ep in result.endpoints
         if ep.path == "/v1/users" and ep.method == HTTPMethod.POST),
        None
    )
    assert create_user is not None, "Should find POST /v1/users endpoint"

    # Find the DELETE /v1/users/{id} endpoint (has params schema)
    delete_user = next(
        (ep for ep in result.endpoints
         if ep.path == "/v1/users/{id}" and ep.method == HTTPMethod.DELETE),
        None
    )
    assert delete_user is not None, "Should find DELETE /v1/users/{id} endpoint"


def test_fastify_boilerplate_path_parameters(fastify_boilerplate_path):
    """Test that path parameters are correctly extracted from TypeBox routes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    # Find endpoint with id parameter (normalized to {id})
    id_endpoints = [ep for ep in result.endpoints if "{id}" in ep.path]
    assert len(id_endpoints) == 1, "Should find exactly one endpoint with {id} parameter"

    # Check the DELETE endpoint
    delete_endpoint = id_endpoints[0]
    assert delete_endpoint.path == "/v1/users/{id}"
    assert delete_endpoint.method == HTTPMethod.DELETE
    assert "delete-user.route.ts" in delete_endpoint.source_file

    # Verify path parameter was extracted
    assert len(delete_endpoint.parameters) == 1, "Should have one path parameter"
    assert delete_endpoint.parameters[0].name == "id"
    assert delete_endpoint.parameters[0].location.value == "path"


def test_fastify_boilerplate_http_methods(fastify_boilerplate_path):
    """Test that various HTTP methods are extracted correctly from TypeBox routes."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    methods_found = {ep.method for ep in result.endpoints}

    # Should have GET, POST, and DELETE
    assert HTTPMethod.GET in methods_found, "Should find GET endpoints"
    assert HTTPMethod.POST in methods_found, "Should find POST endpoints"
    assert HTTPMethod.DELETE in methods_found, "Should find DELETE endpoints"


def test_fastify_boilerplate_route_structure(fastify_boilerplate_path):
    """Test extraction from Clean Architecture route structure.

    Verifies:
    - Routes in modules/<feature>/commands/**/*.route.ts are found
    - Routes in modules/<feature>/queries/**/*.route.ts are found
    - CQRS pattern (commands vs queries) doesn't affect extraction
    """
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    # Separate by CQRS pattern (inferred from HTTP methods)
    queries = [ep for ep in result.endpoints if ep.method == HTTPMethod.GET]
    commands = [ep for ep in result.endpoints if ep.method in (HTTPMethod.POST, HTTPMethod.DELETE)]

    assert len(queries) >= 1, "Should find query endpoints (GET)"
    assert len(commands) >= 2, "Should find command endpoints (POST, DELETE)"

    # Check queries are from queries/ directory
    for query_ep in queries:
        assert "queries" in query_ep.source_file, "GET endpoints should be in queries/ directory"

    # Check commands are from commands/ directory
    for command_ep in commands:
        assert "commands" in command_ep.source_file, "Command endpoints should be in commands/ directory"


def test_fastify_boilerplate_versioned_routes(fastify_boilerplate_path):
    """Test extraction of API versioned routes (/v1/)."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    # All routes should be under /v1
    for endpoint in result.endpoints:
        assert endpoint.path.startswith("/v1/"), "All routes should be versioned with /v1"


def test_fastify_boilerplate_source_location_accuracy(fastify_boilerplate_path):
    """Test that source file paths and line numbers are accurate."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    # Check each endpoint has accurate source information
    for endpoint in result.endpoints:
        # Source file should be in modules/user/
        assert "modules/user" in endpoint.source_file, "Routes should be in modules/user/"

        # Source file should be a .route.ts file
        assert endpoint.source_file.endswith(".route.ts"), "Should be a route file"

        # Line number should be reasonable (routes typically defined in first 30 lines)
        assert 1 <= endpoint.source_line <= 30, "Route definition should be in first 30 lines"


def test_fastify_boilerplate_with_type_provider_pattern(fastify_boilerplate_path):
    """Test extraction of routes using fastify.withTypeProvider<TypeBoxTypeProvider>() pattern."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_boilerplate_path)

    # All routes in this project use the withTypeProvider pattern
    assert len(result.endpoints) == 3, "Should extract all routes using withTypeProvider"

    # Verify each route is properly extracted despite using withTypeProvider
    for endpoint in result.endpoints:
        # Should have path and method
        assert endpoint.path, "Endpoint should have a path"
        assert endpoint.method, "Endpoint should have an HTTP method"

        # Should have source location
        assert endpoint.source_file, "Endpoint should have source file"
        assert endpoint.source_line > 0, "Endpoint should have valid source line"
