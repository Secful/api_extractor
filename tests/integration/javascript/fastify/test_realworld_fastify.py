"""Integration tests for Fastify extractor against real-world applications."""

import os
import pytest
from api_extractor.extractors.javascript.fastify import FastifyExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def fastify_demo_path():
    """Get path to fastify-demo real-world fixture."""
    return os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "..", "fixtures",
        "real-world",
        "javascript",
        "fastify",
        "fastify-demo",
        "src",
        "routes"
    )


def test_fastify_demo_extraction(fastify_demo_path):
    """Test extraction from official Fastify demo application.

    This tests against the official Fastify demo from:
    https://github.com/fastify/demo

    Expected: Task management API with authentication, file uploads,
    CSV export, and role-based access control.
    """
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on Fastify demo"
    assert len(result.endpoints) > 0, "Should find endpoints in Fastify demo"

    # Create lookup dict for easier assertions
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Home route
    assert ("/", HTTPMethod.GET) in paths, "Should find home route"

    # Task endpoints (core functionality)
    assert ("/", HTTPMethod.GET) in paths, "Should find list tasks"
    assert ("/", HTTPMethod.POST) in paths, "Should find create task"
    assert ("/{id}", HTTPMethod.GET) in paths, "Should find get task by ID"
    assert ("/{id}", HTTPMethod.PATCH) in paths, "Should find update task"
    assert ("/{id}", HTTPMethod.DELETE) in paths, "Should find delete task"

    # Task assignment (with role-based access)
    assert ("/{id}/assign", HTTPMethod.POST) in paths, "Should find task assignment endpoint"

    # File upload functionality
    assert ("/{id}/upload", HTTPMethod.POST) in paths, "Should find file upload endpoint"

    # Image management
    assert ("/{filename}/image", HTTPMethod.GET) in paths, "Should find get image endpoint"
    assert ("/{filename}/image", HTTPMethod.DELETE) in paths, "Should find delete image endpoint"

    # CSV export
    assert ("/download/csv", HTTPMethod.GET) in paths, "Should find CSV export endpoint"

    # Authentication
    assert ("/login", HTTPMethod.POST) in paths, "Should find login endpoint"

    # User management
    assert ("/update-password", HTTPMethod.PUT) in paths, "Should find password update endpoint"

    # Verify total endpoint count is reasonable
    assert len(result.endpoints) == 14

    # Check that endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".ts"), "Source file should be TypeScript"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_fastify_demo_path_parameters(fastify_demo_path):
    """Test that path parameters are correctly extracted."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Find endpoint with id parameter
    id_endpoints = [ep for ep in result.endpoints if "{id}" in ep.path]
    assert len(id_endpoints) > 0, "Should find endpoints with {id} parameter"

    # Check that parameters are extracted
    for ep in id_endpoints:
        # Path should be normalized from :id to {id}
        assert ":id" not in ep.path, "Path parameters should be normalized"


def test_fastify_demo_http_methods(fastify_demo_path):
    """Test that various HTTP methods are extracted correctly."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Collect all HTTP methods found
    methods = {ep.method for ep in result.endpoints}

    # Verify we found various HTTP methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    assert HTTPMethod.POST in methods, "Should find POST endpoints"
    assert HTTPMethod.PUT in methods or HTTPMethod.PATCH in methods, "Should find PUT or PATCH endpoints"
    assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"


def test_fastify_demo_plugin_structure(fastify_demo_path):
    """Test that routes from plugin-based structure are extracted."""
    extractor = FastifyExtractor()
    result = extractor.extract(fastify_demo_path)

    # Group endpoints by source file
    files = {ep.source_file for ep in result.endpoints}

    # Should find routes from multiple files (plugin architecture)
    assert len(files) == 5

    # Check for expected route files
    source_files = [os.path.basename(f) for f in files]
    assert "index.ts" in source_files, "Should find routes from index.ts files"
