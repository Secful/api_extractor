"""Test Express validation schema extraction (Joi and Zod)."""

import pytest
from pathlib import Path

from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture
def extractor():
    """Create Express extractor instance."""
    return ExpressExtractor()


@pytest.fixture
def joi_fixture_path():
    """Get path to Joi test fixture."""
    return str(Path(__file__).parent.parent / "fixtures" / "javascript" / "validation" / "joi_express.js")


@pytest.fixture
def zod_fixture_path():
    """Get path to Zod test fixture."""
    return str(Path(__file__).parent.parent / "fixtures" / "javascript" / "validation" / "zod_express.ts")


@pytest.fixture
def json_schema_fixture_path():
    """Get path to JSON Schema test fixture."""
    return str(Path(__file__).parent.parent / "fixtures" / "javascript" / "validation" / "json_schema_express.js")


class TestJoiValidation:
    """Test Joi validation schema extraction."""

    def test_joi_separate_schema_body_validation(self, extractor, joi_fixture_path):
        """Test extraction of Joi schema defined separately and used in celebrate."""
        result = extractor.extract(joi_fixture_path)

        assert result.success
        assert len(result.endpoints) >= 1

        # Find the /users POST endpoint
        users_endpoint = next(
            (e for e in result.endpoints if e.path == "/users" and e.method.value == "POST"),
            None
        )
        assert users_endpoint is not None

        # Check request body schema
        assert users_endpoint.request_body is not None
        assert users_endpoint.request_body.type == "object"
        assert "email" in users_endpoint.request_body.properties
        assert "name" in users_endpoint.request_body.properties
        assert "age" in users_endpoint.request_body.properties
        assert "role" in users_endpoint.request_body.properties

        # Check required fields
        assert "email" in users_endpoint.request_body.required
        assert "name" in users_endpoint.request_body.required

        # Check field types and validation
        email_prop = users_endpoint.request_body.properties["email"]
        assert email_prop["type"] == "string"
        assert email_prop.get("format") == "email"

        name_prop = users_endpoint.request_body.properties["name"]
        assert name_prop["type"] == "string"
        assert name_prop.get("minLength") == 3
        assert name_prop.get("maxLength") == 50

        age_prop = users_endpoint.request_body.properties["age"]
        assert age_prop["type"] in ("number", "integer")
        assert age_prop.get("minimum") == 18

        role_prop = users_endpoint.request_body.properties["role"]
        assert role_prop["type"] == "string"
        assert role_prop.get("enum") == ["user", "admin"]
        assert role_prop.get("default") == "user"

    def test_joi_inline_schema(self, extractor, joi_fixture_path):
        """Test extraction of inline Joi schema."""
        result = extractor.extract(joi_fixture_path)

        # Find the /products POST endpoint
        products_endpoint = next(
            (e for e in result.endpoints if e.path == "/products" and e.method.value == "POST"),
            None
        )
        assert products_endpoint is not None

        # Check request body schema
        assert products_endpoint.request_body is not None
        assert products_endpoint.request_body.type == "object"
        assert "name" in products_endpoint.request_body.properties
        assert "price" in products_endpoint.request_body.properties
        assert "description" in products_endpoint.request_body.properties

        # Check required fields
        assert "name" in products_endpoint.request_body.required
        assert "price" in products_endpoint.request_body.required
        assert "description" not in products_endpoint.request_body.required

    def test_joi_query_validation(self, extractor, joi_fixture_path):
        """Test extraction of Joi query parameter validation."""
        result = extractor.extract(joi_fixture_path)

        # Find the /search GET endpoint
        search_endpoint = next(
            (e for e in result.endpoints if e.path == "/search" and e.method.value == "GET"),
            None
        )
        assert search_endpoint is not None

        # Check query parameters
        assert search_endpoint.parameters is not None
        assert len(search_endpoint.parameters) >= 3

        # Find specific query params
        q_param = next((p for p in search_endpoint.parameters if p.name == "q"), None)
        assert q_param is not None
        assert q_param.location.value == "query"
        assert q_param.type == "string"
        assert q_param.required is True

        limit_param = next((p for p in search_endpoint.parameters if p.name == "limit"), None)
        assert limit_param is not None
        assert limit_param.type in ("number", "integer")
        assert limit_param.required is False


class TestZodValidation:
    """Test Zod validation schema extraction."""

    def test_zod_separate_schema_body_validation(self, extractor, zod_fixture_path):
        """Test extraction of Zod schema defined separately."""
        result = extractor.extract(zod_fixture_path)

        assert result.success
        assert len(result.endpoints) >= 1

        # Find the /users POST endpoint
        users_endpoint = next(
            (e for e in result.endpoints if e.path == "/users" and e.method.value == "POST"),
            None
        )
        assert users_endpoint is not None

        # Check request body schema
        assert users_endpoint.request_body is not None
        assert users_endpoint.request_body.type == "object"
        assert "email" in users_endpoint.request_body.properties
        assert "name" in users_endpoint.request_body.properties
        assert "age" in users_endpoint.request_body.properties
        assert "role" in users_endpoint.request_body.properties

        # Check required fields (Zod is required by default unless .optional())
        assert "email" in users_endpoint.request_body.required
        assert "name" in users_endpoint.request_body.required
        assert "age" not in users_endpoint.request_body.required  # .optional()

        # Check field types and validation
        email_prop = users_endpoint.request_body.properties["email"]
        assert email_prop["type"] == "string"
        assert email_prop.get("format") == "email"

        name_prop = users_endpoint.request_body.properties["name"]
        assert name_prop["type"] == "string"
        assert name_prop.get("minLength") == 3
        assert name_prop.get("maxLength") == 50

    def test_zod_inline_schema(self, extractor, zod_fixture_path):
        """Test extraction of inline Zod schema."""
        result = extractor.extract(zod_fixture_path)

        # Find the /products POST endpoint
        products_endpoint = next(
            (e for e in result.endpoints if e.path == "/products" and e.method.value == "POST"),
            None
        )
        assert products_endpoint is not None

        # Check request body schema
        assert products_endpoint.request_body is not None
        assert products_endpoint.request_body.type == "object"
        assert "name" in products_endpoint.request_body.properties
        assert "price" in products_endpoint.request_body.properties
        assert "description" in products_endpoint.request_body.properties

        # Check required fields
        assert "name" in products_endpoint.request_body.required
        assert "price" in products_endpoint.request_body.required
        assert "description" not in products_endpoint.request_body.required

    def test_zod_query_validation(self, extractor, zod_fixture_path):
        """Test extraction of Zod query parameter validation."""
        result = extractor.extract(zod_fixture_path)

        # Find the /search GET endpoint
        search_endpoint = next(
            (e for e in result.endpoints if e.path == "/search" and e.method.value == "GET"),
            None
        )
        assert search_endpoint is not None

        # Check query parameters
        assert search_endpoint.parameters is not None
        assert len(search_endpoint.parameters) >= 3

        # Find specific query params
        q_param = next((p for p in search_endpoint.parameters if p.name == "q"), None)
        assert q_param is not None
        assert q_param.location.value == "query"
        assert q_param.type == "string"
        assert q_param.required is True

        limit_param = next((p for p in search_endpoint.parameters if p.name == "limit"), None)
        assert limit_param is not None
        assert limit_param.type in ("number", "integer")
        assert limit_param.required is False


class TestJSONSchemaValidation:
    """Test JSON Schema validation extraction."""

    def test_json_schema_separate_schema_body_validation(self, extractor, json_schema_fixture_path):
        """Test extraction of JSON Schema defined separately."""
        result = extractor.extract(json_schema_fixture_path)

        assert result.success
        assert len(result.endpoints) >= 1

        # Find the /users POST endpoint
        users_endpoint = next(
            (e for e in result.endpoints if e.path == "/users" and e.method.value == "POST"),
            None
        )
        assert users_endpoint is not None

        # Check request body schema
        assert users_endpoint.request_body is not None
        assert users_endpoint.request_body.type == "object"
        assert "email" in users_endpoint.request_body.properties
        assert "name" in users_endpoint.request_body.properties
        assert "age" in users_endpoint.request_body.properties
        assert "role" in users_endpoint.request_body.properties

        # Check required fields
        assert "email" in users_endpoint.request_body.required
        assert "name" in users_endpoint.request_body.required

        # Check field properties
        email_prop = users_endpoint.request_body.properties["email"]
        assert email_prop["type"] == "string"
        assert email_prop.get("format") == "email"

        name_prop = users_endpoint.request_body.properties["name"]
        assert name_prop["type"] == "string"
        assert name_prop.get("minLength") == 3
        assert name_prop.get("maxLength") == 50

        age_prop = users_endpoint.request_body.properties["age"]
        assert age_prop["type"] == "integer"
        assert age_prop.get("minimum") == 18

        role_prop = users_endpoint.request_body.properties["role"]
        assert role_prop["type"] == "string"
        assert role_prop.get("enum") == ["user", "admin"]
        assert role_prop.get("default") == "user"

    def test_json_schema_inline_schema(self, extractor, json_schema_fixture_path):
        """Test extraction of inline JSON Schema."""
        result = extractor.extract(json_schema_fixture_path)

        # Find the /products POST endpoint
        products_endpoint = next(
            (e for e in result.endpoints if e.path == "/products" and e.method.value == "POST"),
            None
        )
        assert products_endpoint is not None

        # Check request body schema
        assert products_endpoint.request_body is not None
        assert products_endpoint.request_body.type == "object"
        assert "name" in products_endpoint.request_body.properties
        assert "price" in products_endpoint.request_body.properties
        assert "description" in products_endpoint.request_body.properties

        # Check required fields
        assert "name" in products_endpoint.request_body.required
        assert "price" in products_endpoint.request_body.required
        assert "description" not in products_endpoint.request_body.required

    def test_json_schema_query_validation(self, extractor, json_schema_fixture_path):
        """Test extraction of JSON Schema query parameter validation."""
        result = extractor.extract(json_schema_fixture_path)

        # Find the /search GET endpoint
        search_endpoint = next(
            (e for e in result.endpoints if e.path == "/search" and e.method.value == "GET"),
            None
        )
        assert search_endpoint is not None

        # Check query parameters
        assert search_endpoint.parameters is not None
        assert len(search_endpoint.parameters) >= 3

        # Find specific query params
        q_param = next((p for p in search_endpoint.parameters if p.name == "q"), None)
        assert q_param is not None
        assert q_param.location.value == "query"
        assert q_param.type == "string"
        assert q_param.required is True

        limit_param = next((p for p in search_endpoint.parameters if p.name == "limit"), None)
        assert limit_param is not None
        assert limit_param.type == "integer"
        assert limit_param.required is False
