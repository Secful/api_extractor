"""Integration tests for ASP.NET Core RealWorld application."""

import os
from pathlib import Path

import pytest

from api_extractor.core.models import FrameworkType, HTTPMethod
from api_extractor.extractors.csharp.aspnet_core import ASPNETCoreExtractor


@pytest.fixture
def extractor():
    """Create ASP.NET Core extractor instance."""
    return ASPNETCoreExtractor()


@pytest.fixture
def realworld_path():
    """Get path to ASP.NET Core RealWorld fixture."""
    path = Path(__file__).parent.parent / "fixtures" / "real-world" / "csharp" / "aspnet-core" / "aspnetcore-realworld-example-app"
    if not path.exists():
        pytest.skip("ASP.NET Core RealWorld fixture not found")
    return str(path)


def test_realworld_extraction(extractor, realworld_path):
    """Test extracting endpoints from RealWorld app."""
    # Extract from the entire app
    extraction_result = extractor.extract(realworld_path)

    assert extraction_result.success
    # ASP.NET Core RealWorld app has exactly 15 endpoints
    assert len(extraction_result.endpoints) == 15, (
        f"Expected 15 endpoints, got {len(extraction_result.endpoints)}. "
        f"If the RealWorld app changed, update this test."
    )

    # Should have detected ASP.NET Core
    assert FrameworkType.ASPNET_CORE in extraction_result.frameworks_detected


def test_realworld_standard_paths(extractor, realworld_path):
    """Test that standard RealWorld API paths are extracted."""
    extraction_result = extractor.extract(realworld_path)

    paths = {endpoint.path for endpoint in extraction_result.endpoints}

    # RealWorld API specification requires these core endpoints
    required_paths = {
        "/articles",
        "/articles/{slug}",
        "/articles/feed",
        "/profiles/{username}",
        "/tags",
        "/articles/{slug}/comments",
        "/articles/{slug}/favorite",
    }

    missing_paths = required_paths - paths
    assert not missing_paths, f"Missing required RealWorld paths: {missing_paths}"


def test_realworld_http_methods(extractor, realworld_path):
    """Test that various HTTP methods are detected."""
    extraction_result = extractor.extract(realworld_path)

    methods = set()
    for endpoint in extraction_result.endpoints:
        methods.add(endpoint.method)

    # RealWorld API should have CRUD operations
    assert HTTPMethod.GET in methods
    assert HTTPMethod.POST in methods
    # May also have PUT, DELETE depending on implementation


def test_realworld_path_parameters(extractor, realworld_path):
    """Test that path parameters are extracted correctly."""
    extraction_result = extractor.extract(realworld_path)

    # Find endpoints with path parameters
    param_endpoints = [
        endpoint for endpoint in extraction_result.endpoints if "{" in endpoint.path
    ]

    assert len(param_endpoints) > 0, "Should have endpoints with path parameters"

    # Check that parameters are extracted
    for endpoint in param_endpoints:
        path_params = [p for p in endpoint.parameters if p.location.value == "path"]
        # If path has {param}, should have extracted it
        if "{" in endpoint.path:
            assert len(path_params) > 0, f"Path {endpoint.path} should have path parameters"


def test_realworld_source_tracking(extractor, realworld_path):
    """Test that all endpoints have source tracking information."""
    extraction_result = extractor.extract(realworld_path)

    for endpoint in extraction_result.endpoints:
        assert endpoint.source_file is not None
        assert endpoint.source_file.endswith(".cs")
        assert endpoint.source_line is not None
        assert endpoint.source_line > 0
        assert os.path.exists(endpoint.source_file)


def test_realworld_controller_structure(extractor, realworld_path):
    """Test that all expected controllers are detected."""
    extraction_result = extractor.extract(realworld_path)

    # Get unique controller filenames
    from pathlib import Path
    controller_files = {Path(endpoint.source_file).name for endpoint in extraction_result.endpoints}

    # RealWorld app has exactly these 6 controllers
    expected_controllers = {
        "ArticlesController.cs",
        "CommentsController.cs",
        "FavoritesController.cs",
        "FollowersController.cs",
        "ProfilesController.cs",
        "TagsController.cs",
    }

    assert controller_files == expected_controllers, (
        f"Expected controllers: {expected_controllers}\n"
        f"Found controllers: {controller_files}\n"
        f"Missing: {expected_controllers - controller_files}\n"
        f"Extra: {controller_files - expected_controllers}"
    )


def test_realworld_no_duplicate_paths(extractor, realworld_path):
    """Test that we don't have duplicate path/method combinations."""
    extraction_result = extractor.extract(realworld_path)

    # Track path+method combinations
    combinations = set()
    duplicates = []

    for endpoint in extraction_result.endpoints:
        combo = (endpoint.path, endpoint.method)
        if combo in combinations:
            duplicates.append(combo)
        combinations.add(combo)

    # Should not have duplicates (same path+method)
    assert len(duplicates) == 0, f"Found duplicate endpoints: {duplicates}"


def test_realworld_endpoint_paths_normalized(extractor, realworld_path):
    """Test that all paths are normalized (no type constraints)."""
    extraction_result = extractor.extract(realworld_path)

    for endpoint in extraction_result.endpoints:
        # Check that paths don't have type constraints
        assert ":int" not in endpoint.path
        assert ":string" not in endpoint.path
        assert ":regex" not in endpoint.path


def test_realworld_specific_controllers(extractor, realworld_path):
    """Test extraction from specific known controllers."""
    # Find a known controller file
    controller_files = [
        "ArticlesController.cs",
        "UsersController.cs",
        "ProfilesController.cs",
        "TagsController.cs",
    ]

    found_controller = None
    for root, dirs, files in os.walk(realworld_path):
        for filename in files:
            if filename in controller_files:
                found_controller = os.path.join(root, filename)
                break
        if found_controller:
            break

    if not found_controller:
        pytest.skip("Could not find known controller files")

    # Extract from single controller
    routes = extractor.extract_routes_from_file(found_controller)
    assert len(routes) > 0, f"Should extract routes from {found_controller}"

    # Verify routes have required fields
    for route in routes:
        assert route.path is not None
        assert len(route.methods) > 0
        assert route.source_file == found_controller
        assert route.source_line > 0


def test_realworld_framework_detection(realworld_path):
    """Test that framework detection works for RealWorld app."""
    from api_extractor.core.detector import FrameworkDetector

    detector = FrameworkDetector()
    frameworks = detector.detect(realworld_path)

    assert frameworks is not None
    assert FrameworkType.ASPNET_CORE in frameworks
