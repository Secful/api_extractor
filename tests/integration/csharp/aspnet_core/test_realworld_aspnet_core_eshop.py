"""Integration tests for ASP.NET Core extractor against eShop.

Note: eShop uses both Minimal APIs (Catalog, Ordering, Webhooks services) and
traditional Controller-based APIs (Identity.API service). This tests both patterns.
"""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.csharp.aspnet_core import ASPNETCoreExtractor


@pytest.fixture
def eshop_path() -> str:
    """Get path to eShop real-world fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "csharp",
        "aspnet-core",
        "eShop",
    )
    if not os.path.exists(path):
        pytest.skip("eShop fixture not available (run: git clone --depth=1)")
    return path


def test_eshop_extraction(eshop_path: str) -> None:
    """Test extraction from eShop microservices application.

    Repository: https://github.com/dotnet/eShop
    Domain: E-commerce & Microservices Reference Application
    eShop is Microsoft's reference .NET application using microservices architecture.
    """
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success, "Extraction should succeed on eShop"
    assert len(result.endpoints) > 0, "Should find endpoints"

    # eShop has multiple services with REST APIs
    # Catalog.API: 16 endpoints (Minimal API)
    # Ordering.API: 7 endpoints (Minimal API)
    # Webhooks.API: 4 endpoints (Minimal API)
    # Identity.API: 17 endpoints (Controller-based)
    # Total: 44 endpoints
    assert len(result.endpoints) == 44, \
        f"Expected exactly 44 endpoints, found {len(result.endpoints)}"


def test_eshop_http_methods(eshop_path: str) -> None:
    """Test that various HTTP methods are detected."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success
    methods = {ep.method for ep in result.endpoints}

    # eShop uses standard REST methods
    assert HTTPMethod.GET in methods, "Should find GET endpoints"
    assert HTTPMethod.POST in methods, "Should find POST endpoints"
    assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
    assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"


def test_eshop_catalog_service(eshop_path: str) -> None:
    """Test that Catalog service Minimal API endpoints are extracted."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Catalog endpoints - items, types, brands, semantic search
    catalog_endpoints = [ep for ep in result.endpoints if "/api/catalog" in ep.path]
    assert len(catalog_endpoints) == 16, \
        f"Expected exactly 16 Catalog endpoints, found {len(catalog_endpoints)}"

    # Verify specific catalog patterns
    paths = {ep.path for ep in result.endpoints}
    assert "/api/catalog/items" in paths, "Should have items endpoint"
    assert "/api/catalog/catalogtypes" in paths, "Should have types endpoint"
    assert "/api/catalog/catalogbrands" in paths, "Should have brands endpoint"


def test_eshop_ordering_service(eshop_path: str) -> None:
    """Test that Ordering service Minimal API endpoints are extracted."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Ordering endpoints - orders, card types, cancel, ship
    ordering_endpoints = [ep for ep in result.endpoints if "/api/orders" in ep.path]
    assert len(ordering_endpoints) == 7, \
        f"Expected exactly 7 Ordering endpoints, found {len(ordering_endpoints)}"

    # Verify specific ordering patterns
    paths = {ep.path.lower() for ep in result.endpoints}
    assert any("/api/orders/cancel" in path for path in paths), \
        "Should have cancel order endpoint"
    assert any("/api/orders/ship" in path for path in paths), \
        "Should have ship order endpoint"


def test_eshop_webhooks_service(eshop_path: str) -> None:
    """Test that Webhooks service Minimal API endpoints are extracted."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Webhooks endpoints - CRUD operations
    webhooks_endpoints = [ep for ep in result.endpoints if "/api/webhooks" in ep.path]
    assert len(webhooks_endpoints) == 4, \
        f"Expected exactly 4 Webhooks endpoints, found {len(webhooks_endpoints)}"

    # Verify CRUD operations
    webhook_methods = {ep.method for ep in webhooks_endpoints}
    assert HTTPMethod.GET in webhook_methods, "Should have GET webhooks"
    assert HTTPMethod.POST in webhook_methods, "Should have POST webhook"
    assert HTTPMethod.DELETE in webhook_methods, "Should have DELETE webhook"


def test_eshop_identity_service(eshop_path: str) -> None:
    """Test that Identity service controller endpoints are extracted."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Identity.API uses traditional controllers (not Minimal API)
    # These are IdentityServer4 OAuth endpoints
    identity_endpoints = [
        ep for ep in result.endpoints
        if not any(prefix in ep.path for prefix in ["/api/catalog", "/api/orders", "/api/webhooks"])
    ]
    assert len(identity_endpoints) == 17, \
        f"Expected exactly 17 Identity controller endpoints, found {len(identity_endpoints)}"


def test_eshop_minimal_api_pattern(eshop_path: str) -> None:
    """Test that Minimal API patterns (MapGet, MapPost, MapGroup) are detected."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Minimal APIs use /api prefix
    api_endpoints = [ep for ep in result.endpoints if ep.path.startswith("/api")]
    assert len(api_endpoints) == 27, \
        f"Expected exactly 27 /api endpoints, found {len(api_endpoints)}"

    # Verify MapGroup prefix composition works
    # All catalog endpoints should have /api/catalog prefix
    catalog_endpoints = [ep for ep in result.endpoints if "/api/catalog" in ep.path]
    for ep in catalog_endpoints:
        assert ep.path.startswith("/api/catalog"), \
            f"Catalog endpoint should start with /api/catalog: {ep.path}"


def test_eshop_path_parameters(eshop_path: str) -> None:
    """Test that path parameters are properly extracted and normalized."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Find endpoints with path parameters
    param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
    assert len(param_endpoints) == 11, \
        f"Expected exactly 11 endpoints with parameters, found {len(param_endpoints)}"

    # Check that ASP.NET Core constraints are normalized from {id:int} to {id}
    for ep in param_endpoints:
        # Should not have type constraints
        assert ":int" not in ep.path, \
            f"Path should not have :int constraint: {ep.path}"
        assert ":minlength" not in ep.path, \
            f"Path should not have :minlength constraint: {ep.path}"
        # Should use {{}} format
        assert "{" in ep.path and "}" in ep.path, \
            f"Path parameters should use {{}} format: {ep.path}"


def test_eshop_source_tracking(eshop_path: str) -> None:
    """Test that all endpoints have proper source file information."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Verify all endpoints have source tracking
    for endpoint in result.endpoints:
        assert endpoint.source_file is not None, "Endpoint should have source file"
        assert endpoint.source_file.endswith(".cs"), \
            f"Source file should be C#: {endpoint.source_file}"
        assert endpoint.source_line is not None, "Endpoint should have source line"
        assert endpoint.source_line > 0, "Source line should be positive"


def test_eshop_microservices_architecture(eshop_path: str) -> None:
    """Test that endpoints are extracted from multiple microservices."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Verify we found endpoints from multiple services
    source_files = {ep.source_file for ep in result.endpoints if ep.source_file}

    # Should have files from multiple .API projects
    has_catalog = any("Catalog.API" in f for f in source_files)
    has_ordering = any("Ordering.API" in f for f in source_files)
    has_webhooks = any("Webhooks.API" in f for f in source_files)
    has_identity = any("Identity.API" in f for f in source_files)

    assert has_catalog, "Should find Catalog.API endpoints"
    assert has_ordering, "Should find Ordering.API endpoints"
    assert has_webhooks, "Should find Webhooks.API endpoints"
    assert has_identity, "Should find Identity.API endpoints"


def test_eshop_rest_only(eshop_path: str) -> None:
    """Verify that only REST endpoints are extracted, not gRPC."""
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # eShop uses gRPC for some services (e.g., Basket.API uses gRPC)
    # These should NOT be included in REST endpoint extraction
    # We should only see HTTP REST endpoints, not gRPC endpoints
    for endpoint in result.endpoints:
        # All endpoints should have proper HTTP methods
        assert endpoint.method in [
            HTTPMethod.GET,
            HTTPMethod.POST,
            HTTPMethod.PUT,
            HTTPMethod.DELETE,
            HTTPMethod.PATCH,
        ], f"Unexpected method: {endpoint.method}"

        # gRPC service methods would not have HTTP paths
        assert endpoint.path, "Endpoint should have a path"


def test_eshop_api_versioning(eshop_path: str) -> None:
    """Test that endpoints with API versioning are correctly extracted.

    Note: eShop uses .HasApiVersion() which is metadata, not part of the path.
    The extractor extracts the base path, not versioning metadata.
    """
    extractor = ASPNETCoreExtractor()
    result = extractor.extract(eshop_path)

    assert result.success

    # Catalog service uses v1 and v2 versioning
    # Both versions map to same paths (versioning is via headers/query params)
    # So we may see duplicate paths with same method
    path_method_combos = [(ep.path, ep.method) for ep in result.endpoints]
    unique_combos = set(path_method_combos)

    # Some duplication is expected due to API versioning (v1/v2 map to same paths)
    # eShop's Catalog service uses both v1 and v2, creating legitimate duplicates
    # 44 total endpoints, 30 unique path+method combinations (68.18% unique)
    assert len(path_method_combos) == 44, \
        f"Expected exactly 44 endpoint instances, found {len(path_method_combos)}"
    assert len(unique_combos) == 30, \
        f"Expected exactly 30 unique path+method combinations, found {len(unique_combos)}"
