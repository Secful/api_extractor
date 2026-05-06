"""Unit tests for Next.js inline response object extraction."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.nextjs import NextJSExtractor


@pytest.fixture
def inline_response_path():
    """Get path to inline response fixture."""
    return os.path.join(
        str(os.path.dirname(__file__)),
        "..", "fixtures", "minimal", "javascript", "nextjs-inline-response"
    )


def test_inline_object_response_extraction(inline_response_path):
    """Test extraction of response schemas from inline object literals."""
    extractor = NextJSExtractor()
    result = extractor.extract(inline_response_path)

    assert result.success is True
    assert len(result.endpoints) == 2

    # GET endpoint with inline response
    get_endpoint = next(ep for ep in result.endpoints if ep.method == HTTPMethod.GET)
    assert get_endpoint.path == "/api/status"
    assert len(get_endpoint.responses) == 1

    response = get_endpoint.responses[0]
    assert response.response_schema is not None
    assert response.response_schema.type == "object"
    assert "status" in response.response_schema.properties
    assert "version" in response.response_schema.properties
    # timestamp skipped - call expression Date.now() not inferable

    # Verify inferred types
    assert response.response_schema.properties["status"]["type"] == "string"
    assert response.response_schema.properties["version"]["type"] == "string"

    # POST endpoint with inline response
    post_endpoint = next(ep for ep in result.endpoints if ep.method == HTTPMethod.POST)
    assert post_endpoint.path == "/api/status"
    assert len(post_endpoint.responses) == 1

    response = post_endpoint.responses[0]
    assert response.response_schema is not None
    assert response.response_schema.type == "object"
    # received skipped - identifier (variable reference)
    assert "processed" in response.response_schema.properties
    assert "id" in response.response_schema.properties

    assert response.response_schema.properties["processed"]["type"] == "boolean"
    assert response.response_schema.properties["id"]["type"] == "string"
