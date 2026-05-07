"""Tests for FastAPI schema extraction."""

import os
import pytest
from pathlib import Path
from api_extractor.extractors.python.fastapi import FastAPIExtractor
from api_extractor.core.models import HTTPMethod


def test_fastapi_pydantic_request_body():
    """Test Pydantic model extraction for request body."""
    # Get fixture path
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_fastapi.py")

    # Extract routes
    extractor = FastAPIExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success
    assert len(result.endpoints) > 0

    # Find POST /api/users endpoint (uses User model)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/api/users" and ep.method == HTTPMethod.POST:
            endpoint = ep
            break

    assert endpoint is not None, "POST /api/users endpoint not found"

    # Verify request body schema
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "id" in endpoint.request_body.properties
    assert "username" in endpoint.request_body.properties
    assert "email" in endpoint.request_body.properties

    # Verify required fields
    assert "id" in endpoint.request_body.required
    assert "username" in endpoint.request_body.required
    assert "email" in endpoint.request_body.required


def test_fastapi_pydantic_optional_fields():
    """Test Pydantic model with optional fields."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_fastapi.py")

    extractor = FastAPIExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find POST /api/products endpoint (uses Item model with optional fields)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/api/products" and ep.method == HTTPMethod.POST:
            endpoint = ep
            break

    assert endpoint is not None, "POST /api/products endpoint not found"

    # Verify Item model schema
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "name" in endpoint.request_body.properties
    assert "description" in endpoint.request_body.properties
    assert "price" in endpoint.request_body.properties
    assert "tax" in endpoint.request_body.properties

    # name and price are required, description and tax are optional
    assert "name" in endpoint.request_body.required
    assert "price" in endpoint.request_body.required
    assert "description" not in endpoint.request_body.required
    assert "tax" not in endpoint.request_body.required


def test_fastapi_query_parameters():
    """Test Query parameter extraction with descriptions."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_fastapi.py")

    extractor = FastAPIExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /api/items endpoint (has Query parameters) from sample_fastapi.py specifically
    endpoint = None
    for ep in result.endpoints:
        if (
            ep.path == "/api/items"
            and ep.method == HTTPMethod.GET
            and "sample_fastapi.py" in ep.source_file
        ):
            endpoint = ep
            break

    assert endpoint is not None, "GET /api/items endpoint not found in sample_fastapi.py"

    # Find query parameters
    query_params = [p for p in endpoint.parameters if p.location.value == "query"]
    assert len(query_params) >= 2

    # Check skip parameter
    skip_param = next((p for p in query_params if p.name == "skip"), None)
    assert skip_param is not None
    assert skip_param.type == "integer"
    assert skip_param.description == "Number of items to skip"
    assert not skip_param.required  # Has default value

    # Check limit parameter
    limit_param = next((p for p in query_params if p.name == "limit"), None)
    assert limit_param is not None
    assert limit_param.type == "integer"
    assert limit_param.description == "Maximum number of items"
    assert not limit_param.required  # Has default value


def test_fastapi_header_parameters():
    """Test Header parameter extraction."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_fastapi.py")

    extractor = FastAPIExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /api/users/{user_id} endpoint (has Header parameter)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/api/users/{user_id}" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "GET /api/users/{user_id} endpoint not found"

    # Find header parameters
    header_params = [p for p in endpoint.parameters if p.location.value == "header"]
    assert len(header_params) >= 1

    # Check token header
    token_param = next((p for p in header_params if p.name == "token"), None)
    assert token_param is not None
    assert token_param.type == "string"
    assert token_param.required  # Header(...) means required


def test_fastapi_type_mapping():
    """Test Python type to OpenAPI type mapping."""
    import tempfile

    code = """
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()

class TestModel(BaseModel):
    str_field: str
    int_field: int
    float_field: float
    bool_field: bool
    optional_str: Optional[str] = None
    list_field: List[str]

@app.post("/test")
def test_endpoint(data: TestModel):
    return data
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = FastAPIExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert endpoint.request_body is not None

        props = endpoint.request_body.properties
        assert props["str_field"]["type"] == "string"
        assert props["int_field"]["type"] == "integer"
        assert props["float_field"]["type"] == "number"
        assert props["bool_field"]["type"] == "boolean"
        assert props["optional_str"]["type"] == "string"
        assert props["list_field"]["type"] == "array"

        # Required fields (not Optional and no default)
        assert "str_field" in endpoint.request_body.required
        assert "int_field" in endpoint.request_body.required
        assert "float_field" in endpoint.request_body.required
        assert "bool_field" in endpoint.request_body.required
        assert "list_field" in endpoint.request_body.required
        assert "optional_str" not in endpoint.request_body.required


def test_fastapi_response_model():
    """Test response_model extraction."""
    import tempfile

    code = """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class UserResponse(BaseModel):
    id: int
    username: str

@app.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    return {"id": user_id, "username": "test"}
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = FastAPIExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert len(endpoint.responses) > 0

        response_200 = endpoint.responses[0]
        assert response_200.response_schema is not None
        assert response_200.response_schema.type == "object"
        assert "id" in response_200.response_schema.properties
        assert "username" in response_200.response_schema.properties


def test_fastapi_mixed_parameters():
    """Test endpoint with path, query, and header parameters."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_fastapi.py")

    extractor = FastAPIExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /api/products/{product_id} endpoint
    endpoint = None
    for ep in result.endpoints:
        if "/products/{product_id}" in ep.path and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None

    # Should have path and query parameters
    path_params = [p for p in endpoint.parameters if p.location.value == "path"]
    query_params = [p for p in endpoint.parameters if p.location.value == "query"]

    assert len(path_params) >= 1
    assert len(query_params) >= 1

    # Check path parameter
    assert path_params[0].name == "product_id"

    # Check query parameter
    include_param = next((p for p in query_params if p.name == "include_details"), None)
    assert include_param is not None
    assert include_param.type == "boolean"


def test_fastapi_return_type_annotation():
    """Test return type annotation extraction (list[Model] and Model)."""
    import tempfile

    code = """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    id: int
    name: str
    price: float

@app.get("/items")
def get_items() -> list[Item]:
    return []

@app.get("/item/{item_id}")
def get_item(item_id: int) -> Item:
    return Item(id=item_id, name="test", price=9.99)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = FastAPIExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 2

        # Test list[Item] return type
        list_endpoint = next((ep for ep in result.endpoints if ep.path == "/items"), None)
        assert list_endpoint is not None
        assert len(list_endpoint.responses) > 0

        list_response = list_endpoint.responses[0]
        assert list_response.response_schema is not None
        assert list_response.response_schema.type == "array"
        assert list_response.response_schema.items is not None
        assert list_response.response_schema.items.type == "object"
        assert "id" in list_response.response_schema.items.properties
        assert "name" in list_response.response_schema.items.properties
        assert "price" in list_response.response_schema.items.properties

        # Test Item return type
        item_endpoint = next((ep for ep in result.endpoints if "/item/{item_id}" in ep.path), None)
        assert item_endpoint is not None
        assert len(item_endpoint.responses) > 0

        item_response = item_endpoint.responses[0]
        assert item_response.response_schema is not None
        assert item_response.response_schema.type == "object"
        assert "id" in item_response.response_schema.properties
        assert "name" in item_response.response_schema.properties
        assert "price" in item_response.response_schema.properties
