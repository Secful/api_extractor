"""Unit tests for Zod cross-file import resolution."""

import pytest
from pathlib import Path

from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture
def extractor():
    """Create Express extractor instance."""
    return ExpressExtractor()


@pytest.fixture
def zod_cross_file_fixture():
    """Path to Zod cross-file import test fixture."""
    return Path(__file__).parent.parent / "fixtures" / "javascript" / "validation" / "zod_cross_file.ts"


def test_zod_cross_file_import_body_validation(extractor, zod_cross_file_fixture):
    """Test extraction of Zod body schemas from cross-file imports."""
    result = extractor.extract(str(zod_cross_file_fixture))

    # Find the /users POST endpoint
    users_post = next(
        (e for e in result.endpoints if e.path == "/users" and e.method.value == "POST"),
        None
    )
    assert users_post is not None, "Should find POST /users endpoint"

    # Check request body schema
    assert users_post.request_body is not None, "Should have request body schema"
    assert users_post.request_body.type == "object"
    assert "email" in users_post.request_body.properties
    assert "password" in users_post.request_body.properties
    assert "name" in users_post.request_body.properties
    assert "age" in users_post.request_body.properties

    # Check field types
    assert users_post.request_body.properties["email"]["type"] == "string"
    assert users_post.request_body.properties["email"]["format"] == "email"
    assert users_post.request_body.properties["password"]["type"] == "string"
    assert users_post.request_body.properties["password"]["minLength"] == 8

    # Check required fields (in Zod, fields are required by default unless .optional())
    assert "email" in users_post.request_body.required
    assert "password" in users_post.request_body.required
    assert "name" in users_post.request_body.required
    assert "age" not in users_post.request_body.required  # age is optional


def test_zod_cross_file_import_query_validation(extractor, zod_cross_file_fixture):
    """Test extraction of Zod query schemas from cross-file imports."""
    result = extractor.extract(str(zod_cross_file_fixture))

    # Find the /users GET endpoint
    users_get = next(
        (e for e in result.endpoints if e.path == "/users" and e.method.value == "GET"),
        None
    )
    assert users_get is not None, "Should find GET /users endpoint"

    # Query parameters should be extracted as parameters, not request body
    # Note: This might fail if query parameter handling isn't fixed yet
    assert users_get.parameters is not None

    # If this fails, it means query schemas are still going to request_body
    # which is a known issue we need to fix
    query_params = [p for p in users_get.parameters if p.location.value == "query"]
    assert len(query_params) >= 3, f"Should have query parameters, found {len(query_params)}"


def test_zod_cross_file_multiple_routes(extractor, zod_cross_file_fixture):
    """Test that multiple routes with cross-file imports are extracted."""
    result = extractor.extract(str(zod_cross_file_fixture))

    assert len(result.endpoints) == 3, f"Should find 3 endpoints, found {len(result.endpoints)}"

    # Check all endpoints are extracted
    paths = [e.path for e in result.endpoints]
    assert "/users" in paths
    assert any("/users/" in p for p in paths)  # PUT /users/:id

    # Count endpoints with validation
    with_body_schema = sum(1 for e in result.endpoints if e.request_body)
    assert with_body_schema >= 2, f"Expected at least 2 endpoints with body schemas, found {with_body_schema}"
