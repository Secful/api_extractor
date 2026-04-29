"""Integration tests for Django REST extractor with NetBox."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.django_rest import DjangoRESTExtractor


@pytest.fixture
def netbox_path():
    """Get path to NetBox real-world fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "python",
        "django",
        "netbox",
    )
    if not os.path.exists(path):
        pytest.skip("NetBox fixture not available (run: git submodule update --init)")
    return path


class TestDjangoNetBox:
    """Integration tests for NetBox network infrastructure management system."""

    def test_extraction(self, netbox_path: str) -> None:
        """Test extraction from NetBox.

        Repository: https://github.com/netbox-community/netbox
        Domain: Network Infrastructure Management
        """
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count range (NetBox is a very large app with 700+ endpoints)
        assert 600 <= len(result.endpoints) <= 900, \
            f"Expected 600-900 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, netbox_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"

        # NetBox ViewSets should have PUT, PATCH, DELETE
        if len(result.endpoints) > 20:
            assert HTTPMethod.PUT in methods or HTTPMethod.PATCH in methods, \
                "Should find PUT or PATCH endpoints"

    def test_path_parameters(self, netbox_path: str) -> None:
        """Test that path parameters are properly extracted."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success

        # Find endpoints with path parameters (detail views)
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) >= 10, \
            f"Should find at least 10 endpoints with path parameters, found {len(param_endpoints)}"

    def test_source_tracking(self, netbox_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".py")
            assert ep.source_line is not None
            assert ep.source_line > 0

    def test_api_prefix(self, netbox_path: str) -> None:
        """Test that API paths have /api prefix."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Most NetBox API paths should start with /api
        api_paths = [p for p in paths if p.startswith("/api")]

        if len(paths) > 10:
            # At least 80% should be API paths
            assert len(api_paths) >= len(paths) * 0.8, \
                f"Most paths should start with /api, found {len(api_paths)}/{len(paths)}"

    def test_dcim_endpoints(self, netbox_path: str) -> None:
        """Test that DCIM (Data Center Infrastructure) endpoints are found."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for DCIM app endpoints
        dcim_paths = [p for p in paths if "/dcim/" in p.lower()]

        if len(dcim_paths) > 0:
            assert len(dcim_paths) >= 5, \
                f"Should find multiple DCIM endpoints, found {len(dcim_paths)}"

    def test_ipam_endpoints(self, netbox_path: str) -> None:
        """Test that IPAM (IP Address Management) endpoints are found."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for IPAM app endpoints
        ipam_paths = [p for p in paths if "/ipam/" in p.lower()]

        if len(ipam_paths) > 0:
            assert len(ipam_paths) >= 5, \
                f"Should find multiple IPAM endpoints, found {len(ipam_paths)}"

    def test_viewset_patterns(self, netbox_path: str) -> None:
        """Test that DRF ViewSet patterns are detected (list + detail)."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

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

        if len(result.endpoints) > 20:
            assert len(list_endpoints) >= 5, \
                f"Should find multiple list endpoints, found {len(list_endpoints)}"
            assert len(detail_endpoints) >= 10, \
                f"Should find multiple detail endpoints, found {len(detail_endpoints)}"

    def test_multiple_django_apps(self, netbox_path: str) -> None:
        """Test that endpoints from multiple Django apps are extracted."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # NetBox has multiple apps: dcim, ipam, circuits, virtualization, etc.
        app_keywords = ["dcim", "ipam", "circuits", "virtualization", "tenancy"]
        apps_found = set()

        for path in paths:
            path_lower = path.lower()
            for keyword in app_keywords:
                if keyword in path_lower:
                    apps_found.add(keyword)

        # Should find at least 2 different Django apps
        if len(paths) > 20:
            assert len(apps_found) >= 2, \
                f"Should find endpoints from multiple apps, found: {apps_found}"

    def test_devices_endpoints(self, netbox_path: str) -> None:
        """Test that device management endpoints are found."""
        extractor = DjangoRESTExtractor()
        result = extractor.extract(netbox_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for device-related endpoints
        device_paths = [p for p in paths if "device" in p.lower()]

        if len(device_paths) > 0:
            # Should have both list and detail
            list_paths = [p for p in device_paths if "{" not in p]
            detail_paths = [p for p in device_paths if "{" in p]

            assert len(list_paths) > 0, "Should find device list endpoint"
            assert len(detail_paths) > 0, "Should find device detail endpoint"
