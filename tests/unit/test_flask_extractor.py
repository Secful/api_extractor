"""Tests for Flask extractor."""

import os
import pytest
from api_extractor.extractors.python.flask import FlaskExtractor
from api_extractor.core.models import HTTPMethod


def test_flask_extractor():
    """Test Flask route extraction."""
    # Get fixture path
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "python", "sample_flask.py"
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
    api_products_endpoints = [ep for ep in result.endpoints if ep.path == "/api/products/{product_id}"]
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
        extractor._extract_blueprints_query(tree, source_code)

        assert "api" in extractor.blueprints
        assert extractor.blueprints["api"] == "/api/v1"
        assert "admin" in extractor.blueprints
        assert extractor.blueprints["admin"] == "/admin"


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
    params = extractor._extract_path_parameters("/users/<int:user_id>/posts/<string:post_id>")
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
