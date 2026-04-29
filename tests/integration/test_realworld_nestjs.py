"""Integration tests for NestJS extractor against real-world applications."""

import os
import pytest
from api_extractor.extractors.javascript.nestjs import NestJSExtractor
from api_extractor.core.models import HTTPMethod


@pytest.fixture
def nestjs_realworld_path():
    """Get path to nestjs-realworld real-world fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "javascript",
        "nestjs",
        "nestjs-realworld",
        "src"
    )
    if not os.path.exists(path):
        pytest.skip("NestJS real-world fixture not available (run: git submodule update --init)")
    return path


def test_nestjs_realworld_extraction(nestjs_realworld_path):
    """Test extraction from NestJS RealWorld application.

    This tests against the NestJS implementation of RealWorld API from:
    https://github.com/lujakob/nestjs-realworld-example-app

    Expected: Blogging platform API (Conduit) with users, articles,
    comments, favorites, profiles, and tags.
    """
    extractor = NestJSExtractor()
    result = extractor.extract(nestjs_realworld_path)

    # Check extraction succeeded
    assert result.success, "Extraction should succeed on NestJS RealWorld"
    assert len(result.endpoints) > 0, "Should find endpoints in NestJS RealWorld"

    # Create lookup dict for easier assertions
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Should have found a reasonable number of endpoints
    assert len(result.endpoints) == 21

    # User/authentication endpoints
    user_endpoints = [ep for ep in result.endpoints if "user" in ep.path.lower()]
    assert len(user_endpoints) == 2

    # Article endpoints (core functionality)
    article_endpoints = [ep for ep in result.endpoints if "article" in ep.path.lower()]
    assert len(article_endpoints) == 11

    # Check for HTTP methods on articles
    article_methods = {ep.method for ep in article_endpoints}
    assert HTTPMethod.GET in article_methods, "Should have GET for articles"
    assert HTTPMethod.POST in article_methods, "Should have POST for articles"

    # Verify all endpoints have source file information
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".ts"), "Source file should be TypeScript"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_nestjs_realworld_controller_structure(nestjs_realworld_path):
    """Test that routes from Controller structure are extracted."""
    extractor = NestJSExtractor()
    result = extractor.extract(nestjs_realworld_path)

    # Group endpoints by source file
    files = {ep.source_file for ep in result.endpoints}

    # Should find routes from multiple controller files (modular architecture)
    assert len(files) == 5

    # Check for expected controller files
    source_files = [os.path.basename(f) for f in files]
    controller_files = [f for f in source_files if "controller" in f.lower()]
    assert len(controller_files) == 5


def test_nestjs_realworld_path_parameters(nestjs_realworld_path):
    """Test that path parameters are correctly extracted."""
    extractor = NestJSExtractor()
    result = extractor.extract(nestjs_realworld_path)

    # Find endpoints with path parameters
    param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
    assert len(param_endpoints) > 0, "Should find endpoints with path parameters"

    # Check that parameters are extracted
    for ep in param_endpoints:
        # Path should be normalized from :slug to {slug}
        assert ":" not in ep.path, "Path parameters should be normalized"


def test_nestjs_realworld_http_methods(nestjs_realworld_path):
    """Test that various HTTP methods are extracted correctly."""
    extractor = NestJSExtractor()
    result = extractor.extract(nestjs_realworld_path)

    # Collect all HTTP methods found
    methods = {ep.method for ep in result.endpoints}

    # Verify we found various HTTP methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    assert HTTPMethod.POST in methods, "Should find POST endpoints"
    assert HTTPMethod.PUT in methods or HTTPMethod.PATCH in methods, "Should find PUT or PATCH endpoints"
    assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"


def test_nestjs_realworld_decorator_patterns(nestjs_realworld_path):
    """Test that decorator-based routing is correctly handled."""
    extractor = NestJSExtractor()
    result = extractor.extract(nestjs_realworld_path)

    # NestJS uses decorators like @Get(), @Post(), @Controller()
    # Verify we extracted endpoints with proper HTTP methods
    methods = {ep.method for ep in result.endpoints}
    assert len(methods) == 4

    # Check for @Controller prefix composition
    # Endpoints should have combined paths from @Controller() and method decorators
    paths_with_prefixes = [ep.path for ep in result.endpoints if "/" in ep.path and len(ep.path) > 1]
    assert len(paths_with_prefixes) > 0, "Should find endpoints with controller prefixes"
