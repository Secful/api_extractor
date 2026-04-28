"""Integration tests for Gin extractor against Alist file manager."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.go.gin import GinExtractor


@pytest.fixture
def alist_path() -> str:
    """Get path to Alist real-world fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "go",
        "gin",
        "alist",
        "server",
    )
    if not os.path.exists(path):
        pytest.skip("Alist fixture not available (run: git submodule update --init)")
    return path


def test_alist_extraction(alist_path: str) -> None:
    """Test extraction from Alist file manager.

    Repository: https://github.com/AlistGo/alist
    Domain: File Management & Storage Platform
    Alist is a file list program that supports multiple storage providers.
    """
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success, "Extraction should succeed on Alist"
    assert len(result.endpoints) > 0, "Should find endpoints"

    # Alist has 152 endpoints across auth, file operations, admin, and storage
    assert len(result.endpoints) == 152, \
        f"Expected exactly 152 endpoints, found {len(result.endpoints)}"


def test_alist_http_methods(alist_path: str) -> None:
    """Test that various HTTP methods are detected."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success
    methods = {ep.method for ep in result.endpoints}

    # Alist uses various HTTP methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    assert HTTPMethod.POST in methods, "Should find POST endpoints"
    assert HTTPMethod.PUT in methods or HTTPMethod.HEAD in methods, \
        "Should find PUT or HEAD endpoints"


def test_alist_auth_endpoints(alist_path: str) -> None:
    """Test that authentication endpoints are extracted."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Auth endpoints
    auth_endpoints = [ep for ep in result.endpoints if "auth" in ep.path.lower()]
    assert len(auth_endpoints) == 18, \
        f"Expected exactly 18 auth endpoints, found {len(auth_endpoints)}"

    # Verify specific auth patterns
    paths = {ep.path for ep in result.endpoints}
    assert any("/api/auth/login" in path for path in paths), \
        "Should have login endpoint"
    assert any("/api/auth/register" in path for path in paths or "/api/auth/2fa" in path for path in paths), \
        "Should have register or 2FA endpoint"


def test_alist_file_operations(alist_path: str) -> None:
    """Test that file operation endpoints are extracted."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # File system endpoints - list, get, mkdir, rename, remove, etc.
    fs_endpoints = [ep for ep in result.endpoints if "fs" in ep.path.lower() or "file" in ep.path.lower()]
    assert len(fs_endpoints) == 6, \
        f"Expected exactly 6 file system endpoints, found {len(fs_endpoints)}"

    # Check for common file operations
    paths = {ep.path.lower() for ep in result.endpoints}
    has_list = any("list" in path or "dir" in path for path in paths)
    has_get = any("get" in path or "download" in path for path in paths)
    has_mkdir = any("mkdir" in path or "create" in path for path in paths)

    assert has_list or has_get or has_mkdir, \
        "Should have basic file operation endpoints (list/get/mkdir)"


def test_alist_admin_endpoints(alist_path: str) -> None:
    """Test that admin/management endpoints are extracted."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Admin endpoints - settings, storage, users, etc.
    admin_endpoints = [ep for ep in result.endpoints if any(
        keyword in ep.path.lower()
        for keyword in ["admin", "setting", "storage", "user", "role"]
    )]
    assert len(admin_endpoints) == 37, \
        f"Expected exactly 37 admin endpoints, found {len(admin_endpoints)}"


def test_alist_api_prefix(alist_path: str) -> None:
    """Test that API endpoints have proper /api prefix."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Count endpoints with /api prefix
    api_endpoints = [ep for ep in result.endpoints if ep.path.startswith("/api")]

    # Should have some API endpoints
    assert len(api_endpoints) == 10, \
        f"Expected exactly 10 /api endpoints, found {len(api_endpoints)}"


def test_alist_path_parameters(alist_path: str) -> None:
    """Test that path parameters are properly extracted and normalized."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Find endpoints with path parameters
    param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
    assert len(param_endpoints) > 0, "Should find endpoints with path parameters"

    # Check that Gin path parameters are normalized from :param to {param}
    for ep in param_endpoints:
        assert ":" not in ep.path, \
            f"Path parameters should be normalized, got: {ep.path}"
        assert "{" in ep.path and "}" in ep.path, \
            f"Path parameters should use {{}} format, got: {ep.path}"


def test_alist_source_tracking(alist_path: str) -> None:
    """Test that all endpoints have proper source file information."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Verify all endpoints have source tracking
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".go"), \
            f"Source file should be Go: {endpoint.source_file}"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_alist_wildcard_routes(alist_path: str) -> None:
    """Test that wildcard/catch-all routes are extracted."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Check for wildcard patterns like /*path or /d/*path
    wildcard_endpoints = [ep for ep in result.endpoints if "*path" in ep.path]
    assert len(wildcard_endpoints) == 16, \
        f"Expected exactly 16 wildcard routes, found {len(wildcard_endpoints)}"


def test_alist_offline_download(alist_path: str) -> None:
    """Test that offline download endpoints are extracted."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Offline download is a feature
    offline_endpoints = [ep for ep in result.endpoints if "offline" in ep.path.lower() or "download" in ep.path.lower()]
    assert len(offline_endpoints) == 1, \
        f"Expected exactly 1 offline download endpoint, found {len(offline_endpoints)}"


def test_alist_storage_endpoints(alist_path: str) -> None:
    """Test that storage provider endpoints are extracted."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Storage management endpoints
    storage_endpoints = [ep for ep in result.endpoints if "storage" in ep.path.lower()]
    assert len(storage_endpoints) == 8, \
        f"Expected exactly 8 storage endpoints, found {len(storage_endpoints)}"


def test_alist_no_duplicate_paths(alist_path: str) -> None:
    """Test that there are no excessive duplicate path+method combinations."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Check for duplicates
    path_method_combos = [(ep.path, ep.method) for ep in result.endpoints]
    unique_combos = set(path_method_combos)

    # Should have mostly unique combinations
    duplicate_ratio = len(unique_combos) / len(path_method_combos)
    assert duplicate_ratio >= 0.85, \
        f"At least 85% should be unique, got {duplicate_ratio:.2%}"


def test_alist_large_scale_extraction(alist_path: str) -> None:
    """Test extraction handles large-scale application correctly."""
    extractor = GinExtractor()
    result = extractor.extract(alist_path)

    assert result.success

    # Verify we found a substantial number of unique paths
    paths = set(ep.path for ep in result.endpoints)
    assert len(paths) == 142, \
        f"Expected exactly 142 unique paths, found {len(paths)}"

    # Verify multiple HTTP methods per path (REST pattern)
    path_methods = {}
    for ep in result.endpoints:
        if ep.path not in path_methods:
            path_methods[ep.path] = set()
        path_methods[ep.path].add(ep.method)

    multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
    assert len(multi_method_paths) == 9, \
        f"Expected exactly 9 paths with multiple HTTP methods, found {len(multi_method_paths)}"
