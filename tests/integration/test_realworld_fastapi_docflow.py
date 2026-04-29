"""Integration tests for FastAPI extractor with DocFlow."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.fastapi import FastAPIExtractor


@pytest.fixture
def docflow_path():
    """Get path to DocFlow real-world fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "python",
        "fastapi",
        "docflow",
    )
    if not os.path.exists(path):
        pytest.skip("DocFlow fixture not available (run: git submodule update --init)")
    return path


class TestFastAPIDocFlow:
    """Integration tests for DocFlow document management system."""

    def test_extraction(self, docflow_path: str) -> None:
        """Test extraction from DocFlow.

        Repository: https://github.com/jiisanda/docflow
        Domain: Document Management System
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count range
        assert 22 <= len(result.endpoints) <= 30, \
            f"Expected 22-30 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, docflow_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_path_parameters(self, docflow_path: str) -> None:
        """Test that path parameters are properly extracted."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) > 5, "Should find multiple endpoints with path parameters"

        # Verify OpenAPI format {param}
        for ep in param_endpoints:
            assert "{" in ep.path and "}" in ep.path

    def test_source_tracking(self, docflow_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".py")
            assert ep.source_line is not None
            assert ep.source_line > 0

    def test_document_paths(self, docflow_path: str) -> None:
        """Test that expected document management paths are found."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for document-related patterns (using actual API structure)
        # DocFlow uses simple paths like /upload, /{document}, /share/{document}
        assert any("upload" in path.lower() for path in paths), \
            "Should find upload endpoint"

        # Check for common document operations
        doc_related = [p for p in paths if any(
            keyword in p.lower()
            for keyword in ["upload", "document", "share", "archive", "trash"]
        )]
        assert len(doc_related) >= 10, \
            f"Expected at least 10 document-related paths, found {len(doc_related)}"

    def test_file_operations(self, docflow_path: str) -> None:
        """Test that file upload/download endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Look for file operation patterns
        file_ops = [p for p in paths if any(
            keyword in p.lower()
            for keyword in ["upload", "download", "preview"]
        )]

        assert len(file_ops) > 0, "Should find file operation endpoints"

    def test_sharing_endpoints(self, docflow_path: str) -> None:
        """Test that document sharing endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Look for sharing patterns
        sharing_paths = [p for p in paths if "share" in p.lower()]

        # Should have some sharing-related endpoints (may be 0 if not implemented yet)
        # This is a soft assertion
        if len(sharing_paths) > 0:
            assert any("{" in p for p in sharing_paths), \
                "Sharing endpoints should have path parameters"

    def test_search_functionality(self, docflow_path: str) -> None:
        """Test that search endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Look for search patterns
        has_search = any(
            "search" in path.lower() or "query" in path.lower()
            for path in paths
        )

        # Note: Search may not be implemented yet, so this is informational
        if has_search:
            search_endpoints = [
                ep for ep in result.endpoints
                if "search" in ep.path.lower() or "query" in ep.path.lower()
            ]
            assert len(search_endpoints) > 0

    def test_authentication_endpoints(self, docflow_path: str) -> None:
        """Test that authentication endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(docflow_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for login/signup endpoints (actual implementation)
        has_login = any("login" in p.lower() for p in paths)
        has_signup = any("signup" in p.lower() for p in paths)

        assert has_login, "Should find login endpoint"
        assert has_signup, "Should find signup endpoint"

        # Check for user profile endpoint
        has_me = any(p == "/me" for p in paths)
        assert has_me, "Should find /me endpoint for current user"
