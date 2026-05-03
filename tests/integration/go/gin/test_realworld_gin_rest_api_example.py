"""Integration tests for Gin extractor with gin-rest-api-example.

Tests against https://github.com/zacscoding/gin-rest-api-example
A REST API example with Gin framework featuring user authentication, articles, and comments.
"""

from __future__ import annotations

import os

import pytest

from api_extractor.extractors.go.gin import GinExtractor
from api_extractor.core.models import HTTPMethod


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_extraction():
    """Test extraction from gin-rest-api-example."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success
    # gin-rest-api-example has 11 endpoints:
    # - 4 user endpoints (login, signup, get current user, update user)
    # - 7 article endpoints (list, get, create, delete, list comments, create comment, delete comment)
    assert len(result.endpoints) == 11


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_user_endpoints():
    """Test that user-related endpoints are extracted."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    paths = {ep.path for ep in result.endpoints}

    # Check for user authentication endpoints
    assert "/v1/api/users/login" in paths
    assert "/v1/api/users" in paths  # signup
    assert "/v1/api/user/me" in paths  # current user
    assert "/v1/api/user" in paths  # update user

    # Verify HTTP methods for user endpoints
    endpoints_dict = {(ep.path, ep.method): ep for ep in result.endpoints}
    assert (("/v1/api/users/login", HTTPMethod.POST)) in endpoints_dict
    assert (("/v1/api/users", HTTPMethod.POST)) in endpoints_dict
    assert (("/v1/api/user/me", HTTPMethod.GET)) in endpoints_dict
    assert (("/v1/api/user", HTTPMethod.PUT)) in endpoints_dict


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_article_endpoints():
    """Test that article-related endpoints are extracted."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    paths = {ep.path for ep in result.endpoints}

    # Check for article endpoints
    assert "/articles/" in paths  # list articles
    assert "/articles/{slug}" in paths  # get/delete article by slug
    assert "/articles/{slug}/comments" in paths  # list/create comments
    assert "/articles/{slug}/comments/{id}" in paths  # delete comment

    # Verify HTTP methods for article endpoints
    endpoints_dict = {(ep.path, ep.method): ep for ep in result.endpoints}
    assert (("/articles/", HTTPMethod.GET)) in endpoints_dict
    assert (("/articles/", HTTPMethod.POST)) in endpoints_dict
    assert (("/articles/{slug}", HTTPMethod.GET)) in endpoints_dict
    assert (("/articles/{slug}", HTTPMethod.DELETE)) in endpoints_dict


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_comment_endpoints():
    """Test that comment-related endpoints are extracted."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Check for comment endpoints
    endpoints_dict = {(ep.path, ep.method): ep for ep in result.endpoints}
    assert (("/articles/{slug}/comments", HTTPMethod.GET)) in endpoints_dict
    assert (("/articles/{slug}/comments", HTTPMethod.POST)) in endpoints_dict
    assert (("/articles/{slug}/comments/{id}", HTTPMethod.DELETE)) in endpoints_dict


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_http_methods():
    """Test that various HTTP methods are detected."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    methods = {ep.method for ep in result.endpoints}

    # gin-rest-api-example uses GET, POST, PUT, DELETE
    assert HTTPMethod.GET in methods
    assert HTTPMethod.POST in methods
    assert HTTPMethod.PUT in methods
    assert HTTPMethod.DELETE in methods


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_path_parameters():
    """Test that path parameters are properly extracted and normalized."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    paths = {ep.path for ep in result.endpoints}

    # Check for routes with path parameters (normalized from :param to {param})
    assert any("{slug}" in path for path in paths)
    assert any("{id}" in path for path in paths)

    # Verify specific parameterized paths
    assert "/articles/{slug}" in paths
    assert "/articles/{slug}/comments/{id}" in paths


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_source_tracking():
    """Test that source files and line numbers are tracked."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Check that all endpoints have source tracking
    for ep in result.endpoints:
        assert ep.source_file is not None
        assert ep.source_file.endswith(".go")
        assert ep.source_line is not None
        assert ep.source_line > 0


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_route_groups():
    """Test that route groups and prefixes are properly applied."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    paths = {ep.path for ep in result.endpoints}

    # Check that v1/api prefix is applied to user endpoints
    user_paths = [p for p in paths if "user" in p]
    for path in user_paths:
        assert path.startswith("/v1/api/")

    # Check that article paths have proper prefixes
    article_paths = [p for p in paths if "article" in p]
    for path in article_paths:
        # Article paths should start with /articles/ (no v1/api prefix)
        assert path.startswith("/articles/")

    # All paths should start with /
    for path in paths:
        assert path.startswith("/")
        # No double slashes
        assert "//" not in path


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_unique_endpoints():
    """Test that path+method combinations are unique."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Check for duplicates
    path_method_combos = [(ep.path, ep.method) for ep in result.endpoints]
    unique_combos = set(path_method_combos)

    # All combinations should be unique
    assert len(unique_combos) == len(path_method_combos)


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..",
            "fixtures",
            "real-world",
            "go",
            "gin",
            "gin-rest-api-example",
        )
    ),
    reason="gin-rest-api-example not cloned",
)
def test_gin_rest_api_example_file_structure():
    """Test that routes are found in expected files."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "gin-rest-api-example",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Check that we found routes in handler files
    source_files = {ep.source_file for ep in result.endpoints}
    assert len(source_files) > 0

    # All source files should be .go files
    for file in source_files:
        assert file.endswith(".go")

    # Routes should be in handler.go files (account and article handlers)
    handler_files = [f for f in source_files if "handler.go" in f]
    assert len(handler_files) == 2  # account/handler.go and article/handler.go

    # Verify expected files contain routes
    file_basenames = {os.path.basename(f) for f in source_files}
    assert "handler.go" in file_basenames
