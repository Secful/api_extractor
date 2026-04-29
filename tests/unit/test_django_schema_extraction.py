"""Tests for Django REST Framework schema extraction."""

import os
import pytest
from pathlib import Path
from api_extractor.extractors.python.django_rest import DjangoRESTExtractor
from api_extractor.core.models import HTTPMethod


def test_django_serializer_extraction():
    """Test serializer class extraction."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success
    assert len(result.endpoints) > 0

    # Find POST /users endpoint (create method uses UserSerializer for request)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users" and ep.method == HTTPMethod.POST:
            endpoint = ep
            break

    assert endpoint is not None, "POST /users endpoint not found"

    # Verify request body schema from UserSerializer
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "id" in endpoint.request_body.properties
    assert "username" in endpoint.request_body.properties
    assert "email" in endpoint.request_body.properties

    # All fields are required by default in DRF
    assert "id" in endpoint.request_body.required
    assert "username" in endpoint.request_body.required
    assert "email" in endpoint.request_body.required


def test_django_field_type_mapping():
    """Test DRF field types to OpenAPI type mapping."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find POST /users endpoint
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users" and ep.method == HTTPMethod.POST:
            endpoint = ep
            break

    assert endpoint is not None

    # Check field types
    props = endpoint.request_body.properties
    assert props["id"]["type"] == "integer"  # IntegerField
    assert props["username"]["type"] == "string"  # CharField
    assert props["email"]["type"] == "string"  # EmailField
    assert props["email"].get("format") == "email"  # EmailField has format


def test_django_field_constraints():
    """Test field constraint extraction (max_length, max_digits, etc.)."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # UserSerializer has CharField with max_length=100
    # Find POST /users endpoint
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users" and ep.method == HTTPMethod.POST:
            endpoint = ep
            break

    assert endpoint is not None, "POST /users endpoint not found"

    # Check constraints
    props = endpoint.request_body.properties
    assert "username" in props
    assert props["username"].get("maxLength") == 100  # max_length=100

    # Also test ItemSerializer on GET (retrieve) since ItemViewSet is read-only
    get_item = None
    for ep in result.endpoints:
        if "/items/{pk}" in ep.path and ep.method == HTTPMethod.GET:
            get_item = ep
            break

    if get_item:
        # Check response schema has ItemSerializer fields
        response_props = get_item.responses[0].response_schema.properties
        assert "price" in response_props
        assert response_props["price"]["type"] == "number"  # DecimalField


def test_django_response_schema():
    """Test response schema extraction for GET methods."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /users/{pk} endpoint (retrieve method returns UserSerializer)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users/{pk}" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "GET /users/{pk} endpoint not found"

    # Verify response schema
    assert len(endpoint.responses) > 0
    response_200 = endpoint.responses[0]
    assert response_200.response_schema is not None
    assert response_200.response_schema.type == "object"
    assert "id" in response_200.response_schema.properties
    assert "username" in response_200.response_schema.properties
    assert "email" in response_200.response_schema.properties


def test_django_list_response_schema():
    """Test list response schema (array of objects)."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find GET /users endpoint (list method returns array of UserSerializer)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "GET /users endpoint not found"

    # Verify response is array
    response_200 = endpoint.responses[0]
    assert response_200.response_schema is not None
    assert response_200.response_schema.type == "array"
    assert response_200.response_schema.items is not None


def test_django_update_request_schema():
    """Test PUT/PATCH methods use serializer for request body."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Find PUT /users/{pk} endpoint
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/users/{pk}" and ep.method == HTTPMethod.PUT:
            endpoint = ep
            break

    assert endpoint is not None, "PUT /users/{pk} endpoint not found"

    # Verify request body schema
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "username" in endpoint.request_body.properties


def test_django_readonly_viewset():
    """Test ReadOnlyModelViewSet (only list and retrieve)."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # ItemViewSet is ReadOnlyModelViewSet - should have GET methods with schemas
    get_items = [ep for ep in result.endpoints if "/items" in ep.path and ep.method == HTTPMethod.GET]
    assert len(get_items) >= 2  # list and retrieve

    # Check list endpoint
    list_endpoint = next((ep for ep in get_items if ep.path == "/items"), None)
    assert list_endpoint is not None
    assert list_endpoint.responses[0].response_schema is not None
    assert list_endpoint.responses[0].response_schema.type == "array"

    # Check retrieve endpoint
    retrieve_endpoint = next((ep for ep in get_items if "/items/{pk}" in ep.path), None)
    assert retrieve_endpoint is not None
    assert retrieve_endpoint.responses[0].response_schema is not None
    assert retrieve_endpoint.responses[0].response_schema.type == "object"


def test_django_no_serializer():
    """Test endpoints without serializers still work."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "python" / "sample_django.py")

    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # ProductAPIView has no serializer_class
    product_endpoints = [ep for ep in result.endpoints if "/products" in ep.path]
    assert len(product_endpoints) >= 1

    for ep in product_endpoints:
        # Should not have schemas
        assert ep.request_body is None
