"""Tests for NestJS schema extraction."""

import os
import pytest
from api_extractor.extractors.javascript.nestjs import NestJSExtractor
from api_extractor.core.models import HTTPMethod


def test_nestjs_dto_extraction():
    """Test DTO class extraction."""
    # Get fixture path
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_nestjs.ts",
    )

    # Extract routes
    extractor = NestJSExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success
    assert len(result.endpoints) > 0

    # Find POST /users endpoint (uses CreateUserDto)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users" and ep.method == HTTPMethod.POST:
            endpoint = ep
            break

    assert endpoint is not None, "POST /users endpoint not found"

    # Verify request body schema
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "username" in endpoint.request_body.properties
    assert "email" in endpoint.request_body.properties

    # Both fields are required (no ? marker)
    assert "username" in endpoint.request_body.required
    assert "email" in endpoint.request_body.required


def test_nestjs_query_parameters():
    """Test @Query parameter extraction."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_nestjs.ts",
    )

    extractor = NestJSExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /users endpoint (has Query parameters)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "GET /users endpoint not found"

    # Find query parameters
    query_params = [p for p in endpoint.parameters if p.location.value == "query"]
    assert len(query_params) >= 2

    # Check skip parameter
    skip_param = next((p for p in query_params if p.name == "skip"), None)
    assert skip_param is not None
    assert skip_param.type == "number"
    assert not skip_param.required  # Has ? marker (optional)

    # Check limit parameter
    limit_param = next((p for p in query_params if p.name == "limit"), None)
    assert limit_param is not None
    assert limit_param.type == "number"
    assert not limit_param.required  # Has ? marker (optional)


def test_nestjs_param_decorator():
    """Test @Param parameter extraction."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_nestjs.ts",
    )

    extractor = NestJSExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /users/:id endpoint
    endpoint = None
    for ep in result.endpoints:
        if "/users/{id}" in ep.path and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "GET /users/:id endpoint not found"

    # Find path parameters
    path_params = [p for p in endpoint.parameters if p.location.value == "path"]
    assert len(path_params) >= 1

    # Check id parameter
    id_param = path_params[0]
    assert id_param.name == "id"
    assert id_param.type == "string"
    assert id_param.required


def test_nestjs_type_mapping():
    """Test TypeScript type to OpenAPI type mapping."""
    import tempfile

    code = """
import { Controller, Get, Post, Body } from '@nestjs/common';

class TestDto {
  stringField: string;
  numberField: number;
  boolField: boolean;
  optionalField?: string;
  arrayField: string[];
}

@Controller('test')
export class TestController {
  @Post()
  create(@Body() dto: TestDto) {
    return dto;
  }
}
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = NestJSExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) >= 1

        endpoint = result.endpoints[0]
        assert endpoint.request_body is not None

        props = endpoint.request_body.properties
        assert props["stringField"]["type"] == "string"
        assert props["numberField"]["type"] == "number"
        assert props["boolField"]["type"] == "boolean"
        assert props["optionalField"]["type"] == "string"
        assert props["arrayField"]["type"] == "array"

        # Required fields (not optional)
        assert "stringField" in endpoint.request_body.required
        assert "numberField" in endpoint.request_body.required
        assert "boolField" in endpoint.request_body.required
        assert "arrayField" in endpoint.request_body.required
        assert "optionalField" not in endpoint.request_body.required


def test_nestjs_mixed_parameters():
    """Test endpoint with multiple parameter types."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_nestjs.ts",
    )

    extractor = NestJSExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find PUT /users/:id endpoint (has both @Param and @Body)
    endpoint = None
    for ep in result.endpoints:
        if "/users/{id}" in ep.path and ep.method == HTTPMethod.PUT:
            endpoint = ep
            break

    assert endpoint is not None, "PUT /users/:id endpoint not found"

    # Should have path parameter
    path_params = [p for p in endpoint.parameters if p.location.value == "path"]
    assert len(path_params) >= 1
    assert path_params[0].name == "id"

    # Note: In sample file, updateUserDto is typed as 'any', so request_body might be None
    # This is acceptable behavior


def test_nestjs_no_schema():
    """Test endpoints without DTOs still work."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_nestjs.ts",
    )

    extractor = NestJSExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /health endpoint (no parameters, no DTO)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/health" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None
    assert endpoint.request_body is None  # No DTO
    assert len([p for p in endpoint.parameters if p.location.value == "query"]) == 0


def test_nestjs_nested_paths():
    """Test nested path handling."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_nestjs.ts",
    )

    extractor = NestJSExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /api/orders/:orderId/items endpoint
    endpoint = None
    for ep in result.endpoints:
        if "/api/orders/{orderId}/items" in ep.path and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "Nested path endpoint not found"

    # Should have orderId path parameter
    path_params = [p for p in endpoint.parameters if p.location.value == "path"]
    assert len(path_params) >= 1

    order_id_param = next((p for p in path_params if p.name == "orderId"), None)
    assert order_id_param is not None
    assert order_id_param.type == "string"
