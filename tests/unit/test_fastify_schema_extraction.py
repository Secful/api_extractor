"""Tests for Fastify schema extraction."""

import os
import pytest
from api_extractor.extractors.javascript.fastify import FastifyExtractor
from api_extractor.core.models import HTTPMethod


def test_fastify_request_body_schema():
    """Test request body schema extraction from inline JSON schema."""
    # Get fixture path
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_fastify.js",
    )

    # Extract routes
    extractor = FastifyExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Check that we found endpoints
    assert result.success
    assert len(result.endpoints) > 0

    # Find POST /products endpoint from sample_fastify.js file specifically
    endpoint = None
    for ep in result.endpoints:
        if (
            ep.path == "/products"
            and ep.method == HTTPMethod.POST
            and "sample_fastify.js" in ep.source_file
        ):
            endpoint = ep
            break

    assert endpoint is not None, "POST /products endpoint not found in sample_fastify.js"

    # Verify request body schema
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "name" in endpoint.request_body.properties
    assert "price" in endpoint.request_body.properties

    # Verify required fields
    assert "name" in endpoint.request_body.required
    assert "price" in endpoint.request_body.required

    # Verify property types
    name_prop = endpoint.request_body.properties["name"]
    assert name_prop["type"] == "string"

    price_prop = endpoint.request_body.properties["price"]
    assert price_prop["type"] == "number"


def test_fastify_no_schema():
    """Test endpoints without schemas still work."""
    # Get fixture path
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_fastify.js",
    )

    # Extract routes
    extractor = FastifyExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET / endpoint (no schema)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None
    assert endpoint.request_body is None  # No schema defined


def test_fastify_complex_schema():
    """Test extraction with more complex nested schema."""
    import tempfile

    # Create a file with nested schema
    schema_code = """
const fastify = require('fastify')();

fastify.post('/complex', {
  schema: {
    body: {
      type: 'object',
      required: ['user'],
      properties: {
        user: {
          type: 'object',
          required: ['name', 'email'],
          properties: {
            name: { type: 'string' },
            email: { type: 'string' },
            age: { type: 'number' }
          }
        },
        tags: {
          type: 'array',
          items: { type: 'string' }
        }
      }
    }
  }
}, async (request, reply) => {
  return request.body;
});

module.exports = fastify;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_complex.js")
        with open(test_file, "w") as f:
            f.write(schema_code)

        extractor = FastifyExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert endpoint.request_body is not None
        assert endpoint.request_body.type == "object"
        assert "user" in endpoint.request_body.properties
        assert "tags" in endpoint.request_body.properties

        # Verify nested user object
        user_prop = endpoint.request_body.properties["user"]
        assert user_prop["type"] == "object"
        assert "name" in user_prop["properties"]
        assert "email" in user_prop["properties"]
        assert "age" in user_prop["properties"]
        assert "name" in user_prop["required"]
        assert "email" in user_prop["required"]

        # Verify array with items
        tags_prop = endpoint.request_body.properties["tags"]
        assert tags_prop["type"] == "array"
        assert "items" in tags_prop
        assert tags_prop["items"]["type"] == "string"


def test_fastify_response_schema():
    """Test response schema extraction."""
    import tempfile

    # Create a file with response schema
    schema_code = """
const fastify = require('fastify')();

fastify.get('/user/:id', {
  schema: {
    response: {
      200: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          name: { type: 'string' },
          email: { type: 'string' }
        }
      }
    }
  }
}, async (request, reply) => {
  return { id: request.params.id, name: 'John', email: 'john@example.com' };
});

module.exports = fastify;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_response.js")
        with open(test_file, "w") as f:
            f.write(schema_code)

        extractor = FastifyExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert len(endpoint.responses) > 0

        # Find 200 response
        response_200 = None
        for resp in endpoint.responses:
            if resp.status_code == "200":
                response_200 = resp
                break

        assert response_200 is not None
        assert response_200.response_schema is not None
        assert response_200.response_schema.type == "object"
        assert "id" in response_200.response_schema.properties
        assert "name" in response_200.response_schema.properties
        assert "email" in response_200.response_schema.properties


def test_fastify_both_request_and_response_schemas():
    """Test extraction of both request and response schemas."""
    import tempfile

    schema_code = """
const fastify = require('fastify')();

fastify.post('/create', {
  schema: {
    body: {
      type: 'object',
      required: ['title'],
      properties: {
        title: { type: 'string' },
        description: { type: 'string' }
      }
    },
    response: {
      201: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          title: { type: 'string' }
        }
      }
    }
  }
}, async (request, reply) => {
  reply.code(201).send({ id: '123', title: request.body.title });
});

module.exports = fastify;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_both.js")
        with open(test_file, "w") as f:
            f.write(schema_code)

        extractor = FastifyExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]

        # Verify request body
        assert endpoint.request_body is not None
        assert endpoint.request_body.type == "object"
        assert "title" in endpoint.request_body.properties
        assert "description" in endpoint.request_body.properties
        assert "title" in endpoint.request_body.required

        # Verify response
        response_201 = None
        for resp in endpoint.responses:
            if resp.status_code == "201":
                response_201 = resp
                break

        assert response_201 is not None
        assert response_201.response_schema is not None
        assert "id" in response_201.response_schema.properties
        assert "title" in response_201.response_schema.properties
