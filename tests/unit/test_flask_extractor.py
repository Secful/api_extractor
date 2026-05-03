"""Tests for Flask extractor."""

import os
import pytest
from pathlib import Path
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.core.models import HTTPMethod


def test_flask_extractor():
    """Test Flask route extraction."""
    # Get fixture path
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "sample_flask.py"
    )

    # Extract routes
    extractor = FlaskExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Check that we found endpoints
    assert result.success
    assert len(result.endpoints) > 0

    # Check specific endpoints
    paths = {ep.path: ep for ep in result.endpoints}

    # Check root endpoint
    assert "/" in paths

    # Check user endpoint with path parameter
    user_endpoints = [ep for ep in result.endpoints if ep.path == "/users/{user_id}"]
    assert len(user_endpoints) >= 1  # Should have GET and POST
    # Check methods
    methods = {ep.method for ep in user_endpoints}
    assert HTTPMethod.GET in methods or HTTPMethod.POST in methods

    # Check blueprint endpoints (with prefix)
    assert "/api/products" in paths
    api_products_endpoints = [
        ep for ep in result.endpoints if ep.path == "/api/products/{product_id}"
    ]
    assert len(api_products_endpoints) >= 1

    # Check admin blueprint
    assert "/admin/dashboard" in paths


def test_flask_blueprint_extraction():
    """Test Blueprint url_prefix extraction."""
    extractor = FlaskExtractor()

    # Create test file with blueprint
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(
                """
from flask import Blueprint

api = Blueprint('api', __name__, url_prefix='/api/v1')
admin = Blueprint('admin', __name__, url_prefix='/admin')
"""
            )

        source_code = open(test_file, "rb").read()
        tree = extractor.parser.parse_source(source_code, "python")
        extractor._extract_imports(tree, source_code, test_file)
        extractor._extract_blueprints_query(tree, source_code)

        assert "api" in extractor.blueprints
        assert extractor.blueprints["api"]["url_prefix"] == "/api/v1"
        assert "admin" in extractor.blueprints
        assert extractor.blueprints["admin"]["url_prefix"] == "/admin"


def test_flask_path_parameter_extraction():
    """Test path parameter extraction."""
    extractor = FlaskExtractor()

    # Test simple parameter
    params = extractor._extract_path_parameters("/users/<user_id>")
    assert len(params) == 1
    assert params[0].name == "user_id"
    assert params[0].type == "string"

    # Test typed parameter
    params = extractor._extract_path_parameters("/users/<int:user_id>")
    assert len(params) == 1
    assert params[0].name == "user_id"
    assert params[0].type == "integer"

    # Test multiple parameters
    params = extractor._extract_path_parameters(
        "/users/<int:user_id>/posts/<string:post_id>"
    )
    assert len(params) == 2
    assert params[0].name == "user_id"
    assert params[0].type == "integer"
    assert params[1].name == "post_id"
    assert params[1].type == "string"


def test_flask_path_normalization():
    """Test path normalization."""
    extractor = FlaskExtractor()

    # Convert Flask format to OpenAPI format
    assert extractor._normalize_path("/users/<user_id>") == "/users/{user_id}"
    assert extractor._normalize_path("/users/<int:user_id>") == "/users/{user_id}"
    assert (
        extractor._normalize_path("/users/<int:user_id>/posts/<post_id>")
        == "/users/{user_id}/posts/{post_id}"
    )


def test_flask_method_extraction():
    """Test HTTP method extraction from decorator."""
    extractor = FlaskExtractor()

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(
                """
from flask import Flask

app = Flask(__name__)

@app.route('/users', methods=['GET', 'POST'])
def users():
    pass

@app.get('/items')
def items():
    pass
"""
            )

        routes = extractor.extract_routes_from_file(test_file)

        # Check /users route has GET and POST methods
        users_route = [r for r in routes if r.path == "/users"][0]
        assert HTTPMethod.GET in users_route.methods
        assert HTTPMethod.POST in users_route.methods

        # Check /items route has GET method
        items_route = [r for r in routes if r.path == "/items"][0]
        assert items_route.methods == [HTTPMethod.GET]


def test_smorest_blueprint_detection():
    """Test flask_smorest Blueprint detection vs standard Flask Blueprint."""
    extractor = FlaskExtractor()

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write(
                """
from flask_smorest import Blueprint

api = Blueprint('api', 'api', url_prefix='/api/v1')
"""
            )

        source_code = open(test_file, "rb").read()
        tree = extractor.parser.parse_source(source_code, "python")
        extractor._extract_imports(tree, source_code, test_file)
        extractor._extract_blueprints_query(tree, source_code)

        assert "api" in extractor.blueprints
        assert extractor.blueprints["api"]["url_prefix"] == "/api/v1"
        assert extractor.blueprints["api"]["type"] == "smorest"


def test_smorest_methodview_extraction():
    """Test extraction of flask-smorest MethodView routes."""
    extractor = FlaskExtractor()
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "flask"
        / "sample_flask_smorest.py"
    )

    routes = extractor.extract_routes_from_file(fixture_path)

    # Should find routes from MethodView classes
    assert len(routes) > 0

    # Check that we have smorest routes
    smorest_routes = [r for r in routes if r.metadata.get("smorest")]
    assert len(smorest_routes) > 0

    # Check that routes have correct paths with blueprint prefix
    paths = [r.path for r in smorest_routes]
    assert "/api/v1/pets/" in paths
    assert "/api/v1/pets/<int:pet_id>" in paths


def test_smorest_http_methods():
    """Test extraction of HTTP methods from MethodView class."""
    extractor = FlaskExtractor()
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "flask"
        / "sample_flask_smorest.py"
    )

    routes = extractor.extract_routes_from_file(fixture_path)

    # Find /pets/ route
    pets_routes = [r for r in routes if r.path == "/api/v1/pets/"]
    assert len(pets_routes) == 2  # GET and POST

    methods = {r.methods[0] for r in pets_routes}
    assert HTTPMethod.GET in methods
    assert HTTPMethod.POST in methods

    # Find /pets/<int:pet_id> route
    pet_by_id_routes = [r for r in routes if r.path == "/api/v1/pets/<int:pet_id>"]
    assert len(pet_by_id_routes) == 3  # GET, PUT, DELETE

    methods = {r.methods[0] for r in pet_by_id_routes}
    assert HTTPMethod.GET in methods
    assert HTTPMethod.PUT in methods
    assert HTTPMethod.DELETE in methods


def test_smorest_arguments_query():
    """Test parsing of @blp.arguments with location='query'."""
    extractor = FlaskExtractor()
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "flask"
        / "sample_flask_smorest.py"
    )

    routes = extractor.extract_routes_from_file(fixture_path)

    # Find GET /pets/ route which has query arguments
    pets_get_routes = [
        r
        for r in routes
        if r.path == "/api/v1/pets/" and r.methods[0] == HTTPMethod.GET
    ]
    assert len(pets_get_routes) == 1

    route = pets_get_routes[0]
    assert "request_schemas" in route.metadata
    assert len(route.metadata["request_schemas"]) > 0

    # Check that query location is captured
    query_schema = [
        s for s in route.metadata["request_schemas"] if s["location"] == "query"
    ]
    assert len(query_schema) == 1
    assert query_schema[0]["schema"] == "PetQuerySchema"


def test_smorest_arguments_body():
    """Test parsing of @blp.arguments for request body (default location)."""
    extractor = FlaskExtractor()
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "flask"
        / "sample_flask_smorest.py"
    )

    routes = extractor.extract_routes_from_file(fixture_path)

    # Find POST /pets/ route which has body arguments
    pets_post_routes = [
        r
        for r in routes
        if r.path == "/api/v1/pets/" and r.methods[0] == HTTPMethod.POST
    ]
    assert len(pets_post_routes) == 1

    route = pets_post_routes[0]
    assert "request_schemas" in route.metadata
    assert len(route.metadata["request_schemas"]) > 0

    # Check that json location is used (default)
    json_schema = [
        s for s in route.metadata["request_schemas"] if s["location"] == "json"
    ]
    assert len(json_schema) == 1
    assert json_schema[0]["schema"] == "PetSchema"


def test_smorest_response():
    """Test parsing of @blp.response decorator."""
    extractor = FlaskExtractor()
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "flask"
        / "sample_flask_smorest.py"
    )

    routes = extractor.extract_routes_from_file(fixture_path)

    # Find POST /pets/ route which has 201 response
    pets_post_routes = [
        r
        for r in routes
        if r.path == "/api/v1/pets/" and r.methods[0] == HTTPMethod.POST
    ]
    assert len(pets_post_routes) == 1

    route = pets_post_routes[0]
    assert "response_schemas" in route.metadata
    assert "201" in route.metadata["response_schemas"]
    assert route.metadata["response_schemas"]["201"]["schema"] == "PetSchema"
    assert route.metadata["response_schemas"]["201"]["many"] is False


def test_smorest_response_many():
    """Test parsing of @blp.response with Schema(many=True) for list responses."""
    extractor = FlaskExtractor()
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "flask"
        / "sample_flask_smorest.py"
    )

    routes = extractor.extract_routes_from_file(fixture_path)

    # Find GET /pets/ route which has many=True
    pets_get_routes = [
        r
        for r in routes
        if r.path == "/api/v1/pets/" and r.methods[0] == HTTPMethod.GET
    ]
    assert len(pets_get_routes) == 1

    route = pets_get_routes[0]
    assert "response_schemas" in route.metadata
    assert "200" in route.metadata["response_schemas"]
    assert route.metadata["response_schemas"]["200"]["schema"] == "PetSchema"
    assert route.metadata["response_schemas"]["200"]["many"] is True


def test_smorest_endpoint_conversion():
    """Test conversion of smorest routes to endpoints."""
    extractor = FlaskExtractor()
    fixture_path = str(
        Path(__file__).parent.parent
        / "fixtures"
        / "minimal"
        / "python"
        / "flask"
        / "sample_flask_smorest.py"
    )

    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success
    assert len(result.endpoints) > 0

    # Find GET /api/v1/pets/ endpoint
    pets_get_endpoints = [
        ep
        for ep in result.endpoints
        if ep.path == "/api/v1/pets/" and ep.method == HTTPMethod.GET
    ]
    assert len(pets_get_endpoints) == 1

    endpoint = pets_get_endpoints[0]

    # Should have responses
    assert len(endpoint.responses) > 0

    # Check that 200 response exists
    response_codes = [r.status_code for r in endpoint.responses]
    assert "200" in response_codes
