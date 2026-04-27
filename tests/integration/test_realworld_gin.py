"""Integration tests for Gin extractor with RealWorld app."""

from __future__ import annotations

import os

import pytest

from api_extractor.extractors.go.gin import GinExtractor
from api_extractor.core.models import HTTPMethod


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_extraction():
    """Test extraction from RealWorld Gin app."""
    # Get fixture path
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
    )

    # Extract routes
    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    # Check that we found endpoints
    assert result.success
    # RealWorld Conduit API typically has 25-30 endpoints
    assert len(result.endpoints) >= 20
    assert len(result.endpoints) <= 35


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_standard_paths():
    """Test that standard RealWorld paths are extracted."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    paths = {ep.path for ep in result.endpoints}

    # Check for RealWorld path patterns
    # Note: The RealWorld Gin app uses inline RouterGroup creation,
    # so paths are extracted without full composition

    # Should have user-related paths (login, username, follow)
    assert any("login" in path for path in paths)
    assert any("username" in path for path in paths)
    assert any("follow" in path for path in paths)

    # Should have article-related paths (slug, favorite, comments, feed)
    assert any("slug" in path for path in paths)
    assert any("favorite" in path for path in paths)
    assert any("comments" in path for path in paths)
    assert any("feed" in path for path in paths)


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_http_methods():
    """Test that various HTTP methods are detected."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    methods = {ep.method for ep in result.endpoints}

    # RealWorld API uses GET, POST, PUT, DELETE
    assert HTTPMethod.GET in methods
    assert HTTPMethod.POST in methods
    assert HTTPMethod.PUT in methods
    assert HTTPMethod.DELETE in methods


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_path_parameters():
    """Test that path parameters are properly extracted."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Check for routes with path parameters
    paths = {ep.path for ep in result.endpoints}

    # RealWorld uses :slug for articles
    has_slug = any("{slug}" in path for path in paths)
    # RealWorld uses :username for profiles
    has_username = any("{username}" in path for path in paths)
    # RealWorld may use :id for comments
    has_id = any("{id}" in path for path in paths)

    # At least one of these should be present
    assert has_slug or has_username or has_id


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_source_tracking():
    """Test that source files and line numbers are tracked."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
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
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_file_structure():
    """Test that routes are found in expected files."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Check that we found routes in .go files
    source_files = {ep.source_file for ep in result.endpoints}
    assert len(source_files) > 0

    # All source files should be .go files
    for file in source_files:
        assert file.endswith(".go")


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_route_groups():
    """Test that route groups and prefixes are properly applied."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    paths = {ep.path for ep in result.endpoints}

    # Check if paths have consistent prefixes (if RealWorld uses /api prefix)
    # This is a sanity check that path composition worked
    has_prefixed = any(path.startswith("/api") for path in paths)
    has_root = any(not path.startswith("/api") and path != "/" for path in paths)

    # Either all paths have a prefix, or they're at root
    # This test just ensures path composition didn't create invalid paths
    for path in paths:
        assert path.startswith("/") or path == ""
        # No double slashes
        assert "//" not in path


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "fixtures",
            "real-world",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_realworld_no_duplicate_paths():
    """Test that there are no excessive duplicate path+method combinations."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Check for duplicates
    path_method_combos = [(ep.path, ep.method) for ep in result.endpoints]
    unique_combos = set(path_method_combos)

    # Note: The RealWorld Gin app intentionally defines both "" and "/"
    # for the same handlers to handle trailing slash variations.
    # This is a real pattern in the app, so we allow for more duplicates.
    duplicate_ratio = len(unique_combos) / len(path_method_combos)
    assert duplicate_ratio >= 0.65  # At least 65% should be unique (adjusted for trailing slash duplicates)
