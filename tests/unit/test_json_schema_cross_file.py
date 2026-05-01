"""Tests for JSON Schema cross-file import resolution."""

from pathlib import Path

import pytest

from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture
def extractor():
    """Create ExpressExtractor instance."""
    return ExpressExtractor()


@pytest.fixture
def json_schema_cross_file_fixture_path():
    """Path to JSON Schema cross-file test fixture."""
    return str(
        Path(__file__).parent.parent
        / "fixtures"
        / "javascript"
        / "validation"
        / "json_schema_cross_file.js"
    )


def test_json_schema_cross_file_import_body_validation(
    extractor, json_schema_cross_file_fixture_path
):
    """Test extraction of JSON Schema body validation from imported schemas."""
    result = extractor.extract(json_schema_cross_file_fixture_path)

    # Find the POST /users endpoint
    users_endpoint = next(
        (e for e in result.endpoints if e.path == "/users" and e.method.value == "POST"),
        None,
    )
    assert users_endpoint is not None

    # Check request body schema
    assert users_endpoint.request_body is not None
    assert users_endpoint.request_body.type == "object"
    assert "email" in users_endpoint.request_body.properties
    assert "password" in users_endpoint.request_body.properties
    assert "name" in users_endpoint.request_body.properties
    assert "age" in users_endpoint.request_body.properties
    assert users_endpoint.request_body.required == ["email", "password", "name"]


def test_json_schema_cross_file_import_query_validation(
    extractor, json_schema_cross_file_fixture_path
):
    """Test extraction of JSON Schema query validation from imported schemas."""
    result = extractor.extract(json_schema_cross_file_fixture_path)

    # Find the GET /users endpoint
    users_endpoint = next(
        (e for e in result.endpoints if e.path == "/users" and e.method.value == "GET"),
        None,
    )
    assert users_endpoint is not None

    # Check query parameters
    assert users_endpoint.parameters is not None
    assert len(users_endpoint.parameters) == 3

    # Check page parameter (required)
    page_param = next((p for p in users_endpoint.parameters if p.name == "page"), None)
    assert page_param is not None
    assert page_param.required is True
    assert page_param.location.value == "query"
    assert page_param.type == "integer"

    # Check limit parameter (optional with default)
    limit_param = next((p for p in users_endpoint.parameters if p.name == "limit"), None)
    assert limit_param is not None
    assert limit_param.required is False
    assert limit_param.location.value == "query"
    assert limit_param.type == "integer"


def test_json_schema_cross_file_multiple_routes(
    extractor, json_schema_cross_file_fixture_path
):
    """Test that cross-file imports work for multiple routes."""
    result = extractor.extract(json_schema_cross_file_fixture_path)

    # Should have extracted at least 2 endpoints (POST and GET)
    # PUT endpoint might not be extracted if path param handling isn't implemented
    assert len(result.endpoints) >= 2

    # Verify POST and GET endpoints have validation
    post_users = next(
        (e for e in result.endpoints if e.path == "/users" and e.method.value == "POST"),
        None,
    )
    get_users = next(
        (e for e in result.endpoints if e.path == "/users" and e.method.value == "GET"),
        None,
    )

    assert post_users is not None
    assert get_users is not None

    # POST should have body validation with all 4 fields
    assert post_users.request_body is not None
    assert len(post_users.request_body.properties) == 4
    assert "email" in post_users.request_body.properties
    assert "password" in post_users.request_body.properties
    assert "name" in post_users.request_body.properties
    assert "age" in post_users.request_body.properties

    # GET should have query validation with 3 parameters
    assert get_users.parameters is not None
    assert len(get_users.parameters) == 3
