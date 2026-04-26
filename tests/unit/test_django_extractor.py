"""Tests for Django REST Framework extractor."""

import os
import pytest
from api_extractor.extractors.python.django_rest import DjangoRESTExtractor
from api_extractor.core.models import HTTPMethod


def test_django_extractor():
    """Test Django REST route extraction."""
    # Get fixture path
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "minimal", "python", "sample_django.py"
    )

    # Extract routes
    extractor = DjangoRESTExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    # Check that we found endpoints
    assert result.success
    assert len(result.endpoints) > 0

    # Check specific endpoints
    paths = {(ep.path, ep.method.value): ep for ep in result.endpoints}

    # Check ViewSet endpoints (UserViewSet)
    assert ("/users", "GET") in paths  # list
    assert ("/users", "POST") in paths  # create
    assert ("/users/{pk}", "GET") in paths  # retrieve
    assert ("/users/{pk}", "PUT") in paths  # update
    assert ("/users/{pk}", "DELETE") in paths  # destroy

    # Note: Custom @action extraction is a future enhancement
    # assert ("/users/{pk}/set_password", "POST") in paths

    # Check APIView endpoints
    assert ("/products", "GET") in paths
    assert ("/products", "POST") in paths

    # Check function-based views
    order_endpoints = [ep for ep in result.endpoints if "order" in ep.path]
    assert len(order_endpoints) >= 1


def test_django_path_parameter_extraction():
    """Test path parameter extraction."""
    extractor = DjangoRESTExtractor()

    # Test pk parameter
    params = extractor._extract_path_parameters("/users/{pk}")
    assert len(params) == 1
    assert params[0].name == "pk"
    assert params[0].type == "integer"

    # Test custom parameter
    params = extractor._extract_path_parameters("/items/{item_id}")
    assert len(params) == 1
    assert params[0].name == "item_id"
    assert params[0].type == "string"


def test_django_path_generation():
    """Test path generation from class names."""
    extractor = DjangoRESTExtractor()

    # ViewSet
    assert extractor._generate_path_from_class_name("UserViewSet") == "/users"
    assert extractor._generate_path_from_class_name("ItemViewSet") == "/items"

    # APIView
    assert extractor._generate_path_from_class_name("ProductAPIView") == "/products"
    assert extractor._generate_path_from_class_name("OrderAPIView") == "/orders"


def test_django_path_normalization():
    """Test path normalization."""
    extractor = DjangoRESTExtractor()

    # Django REST paths are already in OpenAPI format
    assert extractor._normalize_path("/users/{pk}") == "/users/{pk}"
    assert extractor._normalize_path("/items/{item_id}") == "/items/{item_id}"
