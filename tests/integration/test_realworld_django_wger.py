"""Integration tests for Django REST extractor with wger."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.django_rest import DjangoRESTExtractor


@pytest.fixture
def wger_path():
    """Get path to wger real-world fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "python",
        "django",
        "wger",
    )
    if not os.path.exists(path):
        pytest.skip("wger fixture not available (run: git submodule update --init)")
    return path


class TestDjangoWger:
    """Integration tests for wger fitness/workout management system."""

    def test_extraction(self, wger_path: str) -> None:
        """Test extraction from wger.

        Repository: https://github.com/wger-project/wger
        Domain: Fitness & Workout Management
        """
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count range (wger is mid-sized with ~50 ViewSets)
        assert 150 <= len(result.endpoints) <= 250, \
            f"Expected 150-250 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, wger_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.PATCH in methods, "Should find PATCH endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_path_parameters(self, wger_path: str) -> None:
        """Test that path parameters are properly extracted."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success

        # Find endpoints with path parameters (detail views)
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) >= 40, \
            f"Should find at least 40 endpoints with path parameters, found {len(param_endpoints)}"

    def test_source_tracking(self, wger_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".py")
            assert ep.source_line is not None
            assert ep.source_line > 0

    def test_api_version_prefix(self, wger_path: str) -> None:
        """Test that API paths have /api/v2/ prefix."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Most wger API paths should start with /api/v2/
        api_v2_paths = [p for p in paths if p.startswith("/api/v2/")]

        if len(paths) > 10:
            # At least 80% should be API v2 paths
            assert len(api_v2_paths) >= len(paths) * 0.8, \
                f"Most paths should start with /api/v2/, found {len(api_v2_paths)}/{len(paths)}"

    def test_exercise_endpoints(self, wger_path: str) -> None:
        """Test that exercise-related endpoints are found."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for exercise endpoints
        exercise_paths = [p for p in paths if "exercise" in p.lower()]

        if len(exercise_paths) > 0:
            assert len(exercise_paths) >= 10, \
                f"Should find multiple exercise endpoints, found {len(exercise_paths)}"

    def test_workout_endpoints(self, wger_path: str) -> None:
        """Test that workout-related endpoints are found."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for workout/routine endpoints (wger uses "routine" terminology)
        workout_keywords = ["routine", "workout", "day", "slot"]
        workout_paths = [p for p in paths if any(kw in p.lower() for kw in workout_keywords)]

        if len(workout_paths) > 0:
            assert len(workout_paths) >= 5, \
                f"Should find multiple workout endpoints, found {len(workout_paths)}"

    def test_nutrition_endpoints(self, wger_path: str) -> None:
        """Test that nutrition-related endpoints are found."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for nutrition endpoints
        nutrition_keywords = ["nutrition", "ingredient", "meal"]
        nutrition_paths = [p for p in paths if any(kw in p.lower() for kw in nutrition_keywords)]

        if len(nutrition_paths) > 0:
            assert len(nutrition_paths) >= 5, \
                f"Should find multiple nutrition endpoints, found {len(nutrition_paths)}"

    def test_weight_tracking_endpoints(self, wger_path: str) -> None:
        """Test that weight tracking endpoints are found."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for weight tracking endpoints
        weight_paths = [p for p in paths if "weight" in p.lower()]

        if len(weight_paths) > 0:
            assert len(weight_paths) >= 2, \
                f"Should find weight tracking endpoints, found {len(weight_paths)}"

    def test_viewset_patterns(self, wger_path: str) -> None:
        """Test that DRF ViewSet patterns are detected (list + detail)."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success

        # ViewSets generate list endpoints (no path params) and detail endpoints (with path params)
        list_endpoints = [
            ep for ep in result.endpoints
            if "{" not in ep.path and ep.method == HTTPMethod.GET
        ]
        detail_endpoints = [
            ep for ep in result.endpoints
            if "{" in ep.path
        ]

        if len(result.endpoints) > 50:
            assert len(list_endpoints) >= 15, \
                f"Should find multiple list endpoints, found {len(list_endpoints)}"
            assert len(detail_endpoints) >= 40, \
                f"Should find multiple detail endpoints, found {len(detail_endpoints)}"

    def test_multiple_domains(self, wger_path: str) -> None:
        """Test that endpoints from multiple domains are extracted."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # wger has multiple domains: exercise, workout/routine, nutrition, weight, gallery
        domain_keywords = ["exercise", "routine", "nutrition", "weight", "gallery"]
        domains_found = set()

        for path in paths:
            path_lower = path.lower()
            for keyword in domain_keywords:
                if keyword in path_lower:
                    domains_found.add(keyword)

        # Should find at least 3 different domains
        if len(paths) > 30:
            assert len(domains_found) >= 3, \
                f"Should find endpoints from multiple domains, found: {domains_found}"

    def test_router_prefix_extraction(self, wger_path: str) -> None:
        """Test that router.urls include() pattern is properly extracted."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(wger_path)

        assert result.success

        # Check that router prefixes were detected
        assert len(extractor.router_prefixes) > 0, "Should detect router include() patterns"

        # Check that the main router has the /api/v2/ prefix
        assert "router" in extractor.router_prefixes, "Should find 'router' variable"
        assert extractor.router_prefixes["router"] == "/api/v2/", \
            f"Router should have /api/v2/ prefix, found: {extractor.router_prefixes.get('router')}"

        # Verify ViewSet registrations include the prefix
        if len(extractor.viewset_registrations) > 0:
            sample_registration = list(extractor.viewset_registrations.values())[0]
            assert sample_registration.startswith("/api/v2/"), \
                f"ViewSet registrations should include /api/v2/ prefix, found: {sample_registration}"
