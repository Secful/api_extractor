"""Tests for security validation."""

import pytest
from pathlib import Path

from api_extractor.server.security import (
    validate_path,
    check_path_exists,
    FORBIDDEN_DIRECTORIES,
)


def test_validate_path_traversal_blocked():
    """Test that path traversal attempts are blocked."""
    with pytest.raises(PermissionError, match="Path traversal"):
        validate_path("/tmp/../etc/passwd")

    with pytest.raises(PermissionError, match="Path traversal"):
        validate_path("../../etc/passwd")

    with pytest.raises(PermissionError, match="Path traversal"):
        validate_path("~/secret")


def test_validate_path_system_directories_blocked():
    """Test that system directories are blocked."""
    # Test with directories that commonly exist
    for forbidden in ["/etc", "/usr"]:
        with pytest.raises(PermissionError, match="system directory"):
            validate_path(forbidden)

    # Test subdir of system directory
    with pytest.raises(PermissionError, match="system directory"):
        validate_path("/etc/passwd")


def test_validate_path_whitelist_enforcement(tmp_path):
    """Test whitelist enforcement."""
    allowed_dir = str(tmp_path / "allowed")
    Path(allowed_dir).mkdir(exist_ok=True)

    disallowed_dir = "/tmp/disallowed"

    # Should succeed for whitelisted path
    validate_path(allowed_dir, allowed_prefixes=[str(tmp_path)])

    # Should fail for non-whitelisted path
    with pytest.raises(PermissionError, match="not in allowed directories"):
        validate_path(disallowed_dir, allowed_prefixes=[str(tmp_path)])


def test_validate_path_whitelist_with_subpaths(tmp_path):
    """Test whitelist with subpaths."""
    base_dir = tmp_path / "base"
    sub_dir = base_dir / "sub" / "path"
    sub_dir.mkdir(parents=True, exist_ok=True)

    # Subpath should be allowed if parent is whitelisted
    validate_path(str(sub_dir), allowed_prefixes=[str(base_dir)])


def test_validate_path_no_whitelist(tmp_path):
    """Test validation without whitelist (all non-system paths allowed)."""
    test_dir = tmp_path / "test"
    test_dir.mkdir(exist_ok=True)

    # Should succeed without whitelist (except system dirs)
    validate_path(str(test_dir), allowed_prefixes=None)
    validate_path(str(test_dir), allowed_prefixes=[])


def test_check_path_exists_valid(tmp_path):
    """Test path existence check for valid path."""
    test_dir = tmp_path / "exists"
    test_dir.mkdir()

    check_path_exists(str(test_dir))


def test_check_path_exists_missing():
    """Test path existence check for missing path."""
    with pytest.raises(FileNotFoundError, match="Path not found"):
        check_path_exists("/nonexistent/path")


def test_check_path_exists_file_not_directory(tmp_path):
    """Test path existence check for file (not directory)."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("content")

    with pytest.raises(ValueError, match="not a directory"):
        check_path_exists(str(test_file))


def test_forbidden_directories_constant():
    """Test that forbidden directories constant is properly defined."""
    assert isinstance(FORBIDDEN_DIRECTORIES, set)
    assert "/etc" in FORBIDDEN_DIRECTORIES
    assert "/root" in FORBIDDEN_DIRECTORIES
    assert "/bin" in FORBIDDEN_DIRECTORIES


def test_validate_path_absolute_resolution(tmp_path):
    """Test that paths are resolved to absolute paths."""
    # Create a test directory
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    # Use relative path
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Relative path should be resolved
        validate_path("test")
    finally:
        os.chdir(original_cwd)
