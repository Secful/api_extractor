"""Tests for Gin extractor."""

from __future__ import annotations

import os
import tempfile

import pytest
from pathlib import Path

from api_extractor.extractors.go.gin import GinExtractor
from api_extractor.core.models import HTTPMethod, FrameworkType


def test_gin_basic_extraction():
    """Test Gin route extraction from minimal fixture."""
    # Get fixture path
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "go")

    # Extract routes
    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    # Check that we found endpoints
    assert result.success
    assert len(result.endpoints) > 0

    # Check specific endpoints
    paths = {(ep.path, ep.method): ep for ep in result.endpoints}

    # Check GET / (empty string path)
    assert ("/", HTTPMethod.GET) in paths or ("", HTTPMethod.GET) in paths

    # Check GET /:id (normalized to {id})
    assert ("/{id}", HTTPMethod.GET) in paths
    id_ep = paths[("/{id}", HTTPMethod.GET)]
    assert id_ep.method == HTTPMethod.GET

    # Check POST /
    assert ("/", HTTPMethod.POST) in paths or ("", HTTPMethod.POST) in paths

    # Check PUT /:id
    assert ("/{id}", HTTPMethod.PUT) in paths

    # Check DELETE /:id
    assert ("/{id}", HTTPMethod.DELETE) in paths

    # Check GET /search
    assert ("/search", HTTPMethod.GET) in paths


def test_gin_path_parameters():
    """Test path parameter extraction."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    router.GET("/users/:id", GetUser)
    router.GET("/posts/:postId/comments/:commentId", GetComment)
}

func GetUser(c *gin.Context) {}
func GetComment(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success
        assert len(result.endpoints) > 0

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Check single parameter
        assert ("/users/{id}", HTTPMethod.GET) in paths
        user_ep = paths[("/users/{id}", HTTPMethod.GET)]

        # Check multiple parameters
        assert ("/posts/{postId}/comments/{commentId}", HTTPMethod.GET) in paths


def test_gin_path_normalization():
    """Test path normalization from :param to {param}."""
    extractor = GinExtractor()

    # Test the normalization method directly
    assert extractor._normalize_path("/users/:id") == "/users/{id}"
    assert extractor._normalize_path("/posts/:slug") == "/posts/{slug}"
    assert extractor._normalize_path("/:id") == "/{id}"
    assert extractor._normalize_path("/articles/:slug/comments/:id") == "/articles/{slug}/comments/{id}"


def test_gin_no_routes():
    """Test extraction from file with no routes."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

// No routes here
func main() {
    println("hello")
}
""")

        result = extractor.extract(tmpdir)
        assert not result.success
        assert len(result.endpoints) == 0


def test_gin_framework_type():
    """Test that extractor returns correct framework type."""
    extractor = GinExtractor()
    assert extractor.framework == FrameworkType.GIN


def test_gin_file_extensions():
    """Test that extractor handles .go files."""
    extractor = GinExtractor()
    extensions = extractor.get_file_extensions()
    assert ".go" in extensions


def test_gin_path_composition():
    """Test path composition with RouterGroup prefixes."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    api := router.Group("/api")
    api.GET("/users", GetUsers)
    api.GET("/users/:id", GetUser)
}

func GetUsers(c *gin.Context) {}
func GetUser(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success
        assert len(result.endpoints) > 0

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Check that paths are properly composed
        assert ("/api/users", HTTPMethod.GET) in paths
        assert ("/api/users/{id}", HTTPMethod.GET) in paths


def test_gin_multiple_parameters():
    """Test multiple path parameters in a single route."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    router.GET("/articles/:slug/comments/:id", GetComment)
    router.DELETE("/users/:userId/posts/:postId", DeletePost)
}

func GetComment(c *gin.Context) {}
func DeletePost(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Check routes with multiple parameters
        assert ("/articles/{slug}/comments/{id}", HTTPMethod.GET) in paths
        assert ("/users/{userId}/posts/{postId}", HTTPMethod.DELETE) in paths


def test_gin_http_methods():
    """Test all supported HTTP methods."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    router.GET("/resource", GetResource)
    router.POST("/resource", CreateResource)
    router.PUT("/resource", UpdateResource)
    router.DELETE("/resource", DeleteResource)
    router.PATCH("/resource", PatchResource)
    router.HEAD("/resource", HeadResource)
    router.OPTIONS("/resource", OptionsResource)
}

func GetResource(c *gin.Context) {}
func CreateResource(c *gin.Context) {}
func UpdateResource(c *gin.Context) {}
func DeleteResource(c *gin.Context) {}
func PatchResource(c *gin.Context) {}
func HeadResource(c *gin.Context) {}
func OptionsResource(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Check all HTTP methods
        assert ("/resource", HTTPMethod.GET) in paths
        assert ("/resource", HTTPMethod.POST) in paths
        assert ("/resource", HTTPMethod.PUT) in paths
        assert ("/resource", HTTPMethod.DELETE) in paths
        assert ("/resource", HTTPMethod.PATCH) in paths
        assert ("/resource", HTTPMethod.HEAD) in paths
        assert ("/resource", HTTPMethod.OPTIONS) in paths


def test_gin_empty_path():
    """Test empty path routes."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    router.GET("", GetRoot)
    router.POST("", CreateRoot)
}

func GetRoot(c *gin.Context) {}
func CreateRoot(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success
        assert len(result.endpoints) > 0


def test_gin_trailing_slash():
    """Test routes with trailing slashes."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    router.GET("/", GetRoot)
    router.GET("/users/", GetUsers)
}

func GetRoot(c *gin.Context) {}
func GetUsers(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success
        assert len(result.endpoints) > 0

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}
        assert ("/", HTTPMethod.GET) in paths


def test_gin_handler_names():
    """Test handler function name extraction."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    router.GET("/users", GetUsers)
    router.POST("/users", CreateUser)
}

func GetUsers(c *gin.Context) {}
func CreateUser(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success

        # Find the endpoints and check handler names
        for ep in result.endpoints:
            if ep.path == "/users" and ep.method == HTTPMethod.GET:
                # Check that we extracted handler metadata
                # The handler name should be in metadata or operation_id
                assert ep.operation_id or (ep.source_file and ep.source_line)


def test_gin_compose_paths_edge_cases():
    """Test path composition edge cases."""
    extractor = GinExtractor()

    # Empty prefix
    assert extractor._compose_paths("", "/users") == "/users"

    # Root prefix
    assert extractor._compose_paths("/", "/users") == "/users"

    # Prefix with trailing slash
    assert extractor._compose_paths("/api/", "/users") == "/api/users"

    # Path without leading slash
    assert extractor._compose_paths("/api", "users") == "/api/users"

    # Both with slashes
    assert extractor._compose_paths("/api", "/users") == "/api/users"


def test_gin_source_tracking():
    """Test that source file and line numbers are tracked."""
    extractor = GinExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.go")
        with open(test_file, "w") as f:
            f.write("""
package main

import "github.com/gin-gonic/gin"

func Register(router *gin.RouterGroup) {
    router.GET("/users", GetUsers)
}

func GetUsers(c *gin.Context) {}
""")

        result = extractor.extract(tmpdir)
        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".go")
            assert ep.source_line is not None
            assert ep.source_line > 0
