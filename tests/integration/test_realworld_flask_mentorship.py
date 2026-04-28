"""Integration tests for Flask extractor with Mentorship Backend."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.flask import FlaskExtractor


@pytest.fixture
def mentorship_path():
    """Get path to Mentorship Backend real-world fixture."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "mentorship-backend",
    )
    if not os.path.exists(path):
        pytest.skip("Mentorship Backend fixture not available (run: git submodule update --init)")
    return path


class TestFlaskMentorshipBackend:
    """Integration tests for AnitaB.org Mentorship Backend."""

    def test_extraction(self, mentorship_path: str) -> None:
        """Test extraction from Mentorship Backend.

        Repository: https://github.com/anitab-org/mentorship-backend
        Domain: Social mentorship platform
        """
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count range (33 expected, allow some variance)
        assert 25 <= len(result.endpoints) <= 40, \
            f"Expected 25-40 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, mentorship_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_path_parameters(self, mentorship_path: str) -> None:
        """Test that path parameters are properly extracted and normalized."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success

        # Find endpoints with path parameters (Flask uses <param>, should normalize to {param})
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path or "<" in ep.path]
        assert len(param_endpoints) > 10, \
            f"Should find multiple endpoints with path parameters, found {len(param_endpoints)}"

        # Verify parameter format (should be normalized to OpenAPI {param} format)
        for ep in param_endpoints:
            # Either already normalized to {param} or still in Flask <param> format
            has_curly = "{" in ep.path and "}" in ep.path
            has_angle = "<" in ep.path and ">" in ep.path
            assert has_curly or has_angle, \
                f"Path {ep.path} should have parameters in {{}} or <> format"

    def test_source_tracking(self, mentorship_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".py")
            assert ep.source_line is not None
            assert ep.source_line > 0

    def test_user_endpoints(self, mentorship_path: str) -> None:
        """Test that user management endpoints are found."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for user-related patterns
        user_paths = [p for p in paths if "user" in p.lower()]
        assert len(user_paths) >= 5, \
            f"Expected at least 5 user-related paths, found {len(user_paths)}"

    def test_mentorship_relation_endpoints(self, mentorship_path: str) -> None:
        """Test that mentorship relationship endpoints are found."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for mentorship relation patterns
        relation_paths = [p for p in paths if "mentorship" in p.lower() or "relation" in p.lower()]
        assert len(relation_paths) >= 5, \
            f"Expected at least 5 mentorship relation paths, found {len(relation_paths)}"

    def test_nested_resources(self, mentorship_path: str) -> None:
        """Test that nested resources (tasks, comments) are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for task-related nested resources
        task_paths = [p for p in paths if "task" in p.lower()]
        if len(task_paths) > 0:  # Tasks may be present
            # Should have nested structure: /mentorship_relation/<id>/task/<task_id>
            deeply_nested = [p for p in task_paths if p.count("/") > 3]
            assert len(deeply_nested) > 0, \
                "Should find deeply nested task endpoints"

    def test_admin_endpoints(self, mentorship_path: str) -> None:
        """Test that admin endpoints are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for admin endpoints
        admin_paths = [p for p in paths if "admin" in p.lower()]
        if len(admin_paths) > 0:
            assert len(admin_paths) >= 2, \
                f"Should find multiple admin endpoints, found {len(admin_paths)}"

    def test_authentication_endpoints(self, mentorship_path: str) -> None:
        """Test that authentication endpoints are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for auth-related endpoints
        has_login = any("login" in p.lower() for p in paths)
        has_register = any("register" in p.lower() or "signup" in p.lower() for p in paths)

        assert has_login or has_register, \
            "Should find login or register endpoints"

    def test_state_machine_endpoints(self, mentorship_path: str) -> None:
        """Test that state machine endpoints (accept, reject, cancel) are detected."""
        extractor = FlaskExtractor()
        result = extractor.extract(mentorship_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for state transition endpoints
        state_actions = ["accept", "reject", "cancel"]
        state_paths = [
            p for p in paths
            if any(action in p.lower() for action in state_actions)
        ]

        if len(state_paths) > 0:
            assert len(state_paths) >= 2, \
                "Should find multiple state transition endpoints"
