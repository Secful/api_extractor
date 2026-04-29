"""Tests for Flask schema extraction (Pydantic support)."""

import os
import pytest
import tempfile
from pathlib import Path
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.core.models import HTTPMethod


def test_flask_pydantic_request_body():
    """Test Pydantic model extraction for request body in Flask."""
    code = """
from flask import Flask
from pydantic import BaseModel

app = Flask(__name__)

class User(BaseModel):
    id: int
    username: str
    email: str

@app.post("/users")
def create_user(user: User):
    return user.dict()
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = FlaskExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) >= 1

        # Find POST /users endpoint
        endpoint = None
        for ep in result.endpoints:
            if ep.path == "/users" and ep.method == HTTPMethod.POST:
                endpoint = ep
                break

        assert endpoint is not None, "POST /users endpoint not found"

        # Verify request body schema
        assert endpoint.request_body is not None
        assert endpoint.request_body.type == "object"
        assert "id" in endpoint.request_body.properties
        assert "username" in endpoint.request_body.properties
        assert "email" in endpoint.request_body.properties

        # All fields are required (no Optional, no defaults)
        assert "id" in endpoint.request_body.required
        assert "username" in endpoint.request_body.required
        assert "email" in endpoint.request_body.required


def test_flask_pydantic_optional_fields():
    """Test Pydantic model with optional fields in Flask."""
    code = """
from flask import Flask
from pydantic import BaseModel
from typing import Optional

app = Flask(__name__)

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

@app.post("/items")
def create_item(item: Item):
    return item.dict()
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = FlaskExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) >= 1

        endpoint = result.endpoints[0]
        assert endpoint.request_body is not None

        # name and price are required, description is optional
        assert "name" in endpoint.request_body.required
        assert "price" in endpoint.request_body.required
        assert "description" not in endpoint.request_body.required


def test_flask_query_parameter_extraction():
    """Test query parameter extraction from request.args.get()."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_flask.py")

    extractor = FlaskExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success

    # Find GET /items endpoint (has request.args.get calls)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/items" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "GET /items endpoint not found"

    # Should have extracted query parameters
    query_params = [p for p in endpoint.parameters if p.location.value == "query"]
    assert len(query_params) >= 2

    param_names = {p.name for p in query_params}
    assert "skip" in param_names
    assert "limit" in param_names


def test_flask_no_pydantic():
    """Test endpoints without Pydantic still work."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_flask.py")

    extractor = FlaskExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success
    assert len(result.endpoints) > 0

    # Find POST /items endpoint (no Pydantic model)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/items" and ep.method == HTTPMethod.POST:
            endpoint = ep
            break

    assert endpoint is not None
    assert endpoint.request_body is None  # No Pydantic model


def test_flask_pydantic_type_mapping():
    """Test Python type to OpenAPI type mapping."""
    code = """
from flask import Flask
from pydantic import BaseModel
from typing import List

app = Flask(__name__)

class TestModel(BaseModel):
    str_field: str
    int_field: int
    float_field: float
    bool_field: bool
    list_field: List[str]

@app.post("/test")
def test_endpoint(data: TestModel):
    return data.dict()
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = FlaskExtractor()
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
        assert props["list_field"]["type"] == "array"


def test_flask_blueprint_with_pydantic():
    """Test Pydantic extraction works with blueprints."""
    code = """
from flask import Flask, Blueprint
from pydantic import BaseModel

app = Flask(__name__)
api = Blueprint('api', __name__, url_prefix='/api')

class Product(BaseModel):
    id: int
    name: str

@api.post("/products")
def create_product(product: Product):
    return product.dict()

app.register_blueprint(api)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = FlaskExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) >= 1

        # Find POST /api/products endpoint
        endpoint = None
        for ep in result.endpoints:
            if "/api/products" in ep.path and ep.method == HTTPMethod.POST:
                endpoint = ep
                break

        assert endpoint is not None
        assert endpoint.request_body is not None
        assert "name" in endpoint.request_body.properties
