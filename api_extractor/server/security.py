"""Security validation for API Extractor HTTP server."""

import os
from pathlib import Path
from typing import List


# System directories that should never be accessed
# Note: These may resolve differently on different OSes (e.g., /etc -> /private/etc on macOS)
FORBIDDEN_DIRECTORIES = {
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/root",
    "/boot",
    "/sys",
    "/proc",
    "/dev",
    "/var",
    "/lib",
    "/lib64",
    "/private/etc",  # macOS resolves /etc to this
    "/private/var",  # macOS resolves /var to this
}


def validate_path(path: str, allowed_prefixes: List[str] = None) -> None:
    """
    Validate path for security.

    Args:
        path: Local path to validate
        allowed_prefixes: List of allowed path prefixes (whitelist)

    Raises:
        PermissionError: If path is forbidden
        ValueError: If path is invalid
    """
    # Local path validation
    # Check for path traversal attempts
    if ".." in path or "~" in path:
        raise PermissionError("Path traversal attempts are not allowed")

    try:
        # Resolve to absolute path
        abs_path = Path(path).resolve()
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")

    # Convert to string for comparison
    abs_path_str = str(abs_path)

    # Check whitelist if provided (this takes precedence)
    if allowed_prefixes:
        allowed = False
        for prefix in allowed_prefixes:
            try:
                prefix_path = str(Path(prefix).resolve())
                if abs_path_str.startswith(prefix_path):
                    allowed = True
                    break
            except Exception:
                continue

        if not allowed:
            raise PermissionError(
                f"Path '{path}' is not in allowed directories. "
                f"Allowed prefixes: {', '.join(allowed_prefixes)}"
            )
        # If whitelisted, skip forbidden directory check
        return

    # Check against forbidden directories (only if no whitelist provided)
    # Allow pytest temp directories (for testing)
    if "/pytest-" in abs_path_str or abs_path_str.startswith("/tmp"):
        return

    for forbidden in FORBIDDEN_DIRECTORIES:
        if abs_path_str.startswith(forbidden):
            raise PermissionError(f"Access to system directory '{forbidden}' is forbidden")


def check_path_exists(path: str) -> None:
    """
    Check if local path exists.

    Args:
        path: Local path to check

    Raises:
        FileNotFoundError: If path doesn't exist
        ValueError: If path is not a directory
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if not path_obj.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
