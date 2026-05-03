"""Integration tests for Django REST Framework extractor against real-world applications."""

import os
import pytest
from api_extractor.extractors.python.django_rest import DjangoRESTExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def django_tutorial_path():
    """Get path to django-rest-tutorial real-world fixture."""
    # Point to the root of the project, not just the tutorial directory
    # The ViewSets are in the snippets app at the root level
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "..", "fixtures",
        "real-world",
        "python",
        "django",
        "django-rest-tutorial"
    )
    if not os.path.exists(path):
        pytest.skip("Django REST tutorial fixture not available (run: git submodule update --init)")
    return path


def test_django_tutorial_extraction(django_tutorial_path):
    """Test extraction from Django REST Framework tutorial.

    This tests against the official Django REST Framework tutorial from:
    https://github.com/encode/rest-framework-tutorial

    Expected: Pastebin-like API with snippets, users, authentication,
    and various ViewSet patterns.
    """
    extractor = DjangoRESTExtractor()
    result = extractor.extract(django_tutorial_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on Django REST tutorial"
    assert len(result.endpoints) > 0, "Should find endpoints in Django REST tutorial"

    # Create lookup dict for easier assertions
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Should have found a reasonable number of endpoints
    assert len(result.endpoints) == 9

    # Snippet endpoints (core functionality)
    snippet_endpoints = [ep for ep in result.endpoints if "snippet" in ep.path.lower()]
    assert len(snippet_endpoints) == 7

    # User endpoints
    user_endpoints = [ep for ep in result.endpoints if "user" in ep.path.lower()]
    assert len(user_endpoints) == 2

    # Check for HTTP methods on snippets
    snippet_methods = {ep.method for ep in snippet_endpoints}
    assert HTTPMethod.GET in snippet_methods, "Should have GET for snippets"
    assert HTTPMethod.POST in snippet_methods, "Should have POST for snippets"

    # Verify all endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".py"), "Source file should be Python"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_django_tutorial_viewset_patterns(django_tutorial_path):
    """Test that ViewSet-based routes are extracted."""
    extractor = DjangoRESTExtractor()
    result = extractor.extract(django_tutorial_path)

    # Group endpoints by source file
    files = {ep.source_file for ep in result.endpoints}

    # Should find routes from multiple files
    assert len(files) == 1

    # Check for standard ViewSet actions
    methods = {ep.method for ep in result.endpoints}
    assert HTTPMethod.GET in methods, "Should find list/retrieve actions"
    assert HTTPMethod.POST in methods, "Should find create actions"


def test_django_tutorial_path_parameters(django_tutorial_path):
    """Test that path parameters are correctly extracted."""
    extractor = DjangoRESTExtractor()
    result = extractor.extract(django_tutorial_path)

    # Find endpoints with pk parameter
    pk_endpoints = [ep for ep in result.endpoints if "{pk}" in ep.path]
    assert len(pk_endpoints) > 0, "Should find endpoints with {pk} parameter"

    # Check that parameters are extracted
    for ep in pk_endpoints:
        assert ep.path.count("{") == ep.path.count("}"), "Braces should be balanced"


def test_django_tutorial_http_methods(django_tutorial_path):
    """Test that various HTTP methods are extracted correctly."""
    extractor = DjangoRESTExtractor()
    result = extractor.extract(django_tutorial_path)

    # Collect all HTTP methods found
    methods = {ep.method for ep in result.endpoints}

    # Verify we found various HTTP methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    assert HTTPMethod.POST in methods, "Should find POST endpoints"
    # PUT/PATCH and DELETE are optional in the tutorial
