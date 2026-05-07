"""Integration tests for FastAPI extractor with Polar."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.python.fastapi import FastAPIExtractor


@pytest.fixture
def polar_path():
    """Get path to Polar real-world fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "python",
        "fastapi",
        "polar",
        "server",  # Polar API is in the server subdirectory
    )
    if not os.path.exists(path):
        pytest.skip("Polar fixture not available (run: git submodule update --init)")
    return path


class TestFastAPIPolar:
    """Integration tests for Polar payment/monetization platform."""

    def test_extraction(self, polar_path: str) -> None:
        """Test extraction from Polar.

        Repository: https://github.com/polarsource/polar
        Domain: Payment & Monetization Platform

        NOTE: Polar has 332 endpoints, but router prefixes are not currently
        detected by the FastAPI extractor. Paths are relative to their router
        definitions (e.g., /{id} instead of /customers/{id}).
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) > 0, "Should find endpoints"

        # Verify endpoint count range (Polar is large with 330+ endpoints)
        assert 280 <= len(result.endpoints) <= 350, \
            f"Expected 280-350 endpoints, found {len(result.endpoints)}"

    def test_http_methods(self, polar_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"
        assert HTTPMethod.PUT in methods, "Should find PUT endpoints"
        assert HTTPMethod.PATCH in methods, "Should find PATCH endpoints"
        assert HTTPMethod.DELETE in methods, "Should find DELETE endpoints"

    def test_path_parameters(self, polar_path: str) -> None:
        """Test that path parameters are properly extracted."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success

        # Find endpoints with path parameters
        param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
        assert len(param_endpoints) == 164, \
            f"Should find at least 100 endpoints with path parameters, found {len(param_endpoints)}"

        # Verify {id} pattern is common
        id_endpoints = [ep for ep in result.endpoints if "{id}" in ep.path]
        assert len(id_endpoints) == 130, \
            f"Should find many {{id}} pattern endpoints, found {len(id_endpoints)}"

    def test_external_id_pattern(self, polar_path: str) -> None:
        """Test that external ID access pattern is detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success

        # Check for external ID pattern
        external_id_endpoints = [ep for ep in result.endpoints if "external" in ep.path]
        assert len(external_id_endpoints) >= 7, \
            f"Should find external ID endpoints, found {len(external_id_endpoints)}"

        # Verify the pattern includes {external_id}
        external_param_endpoints = [ep for ep in external_id_endpoints if "{external_id}" in ep.path]
        assert len(external_param_endpoints) >= 7, \
            "Should find endpoints with {{external_id}} parameter"

    def test_source_tracking(self, polar_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None
            assert ep.source_file.endswith(".py")
            assert ep.source_line is not None
            assert ep.source_line > 0

    def test_multiple_domain_endpoints(self, polar_path: str) -> None:
        """Test that endpoints from multiple domains are extracted.

        NOTE: Due to router prefix limitation, paths won't have full prefixes.
        We check for partial matches in relative paths.
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for various domain indicators
        # These will appear in relative paths or as path parameters
        domain_indicators = {
            'organization': ['organizations', '{organization_id}'],
            'webhook': ['webhook', 'endpoints', 'deliveries'],
            'user': ['me', 'user'],
            'auth': ['auth', 'authenticate', 'authorize'],
            'external_integration': ['bot', 'installation', 'guild']
        }

        found_domains = set()
        for domain, indicators in domain_indicators.items():
            for indicator in indicators:
                if any(indicator in path for path in paths):
                    found_domains.add(domain)
                    break

        # Should find at least 3 different domain categories
        assert len(found_domains) == 5, \
            f"Should find endpoints from multiple domains, found: {found_domains}"

    def test_export_endpoints(self, polar_path: str) -> None:
        """Test that export endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for export functionality
        export_paths = [p for p in paths if "export" in p.lower()]
        assert len(export_paths) == 5, \
            f"Should find export endpoints, found {len(export_paths)}"

    def test_state_aggregation_endpoints(self, polar_path: str) -> None:
        """Test that state aggregation endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Check for state endpoints
        state_paths = [p for p in paths if "/state" in p]
        assert len(state_paths) == 2, \
            f"Should find state endpoints, found {len(state_paths)}"

    def test_health_and_utility_endpoints(self, polar_path: str) -> None:
        """Test that health check and utility endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Common utility endpoints
        utility_keywords = ["health", "check", "status"]
        utility_paths = [p for p in paths if any(kw in p.lower() for kw in utility_keywords)]

        assert len(utility_paths) >= 8, \
            f"Should find utility endpoints, found {len(utility_paths)}"

    def test_oauth_endpoints(self, polar_path: str) -> None:
        """Test that OAuth-related endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # OAuth patterns
        oauth_keywords = ["authorize", "callback", "consent", "token"]
        oauth_paths = [p for p in paths if any(kw in p.lower() for kw in oauth_keywords)]

        assert len(oauth_paths) == 21, \
            f"Should find exactly 21 OAuth endpoints, found {len(oauth_paths)}"

    def test_streaming_endpoints(self, polar_path: str) -> None:
        """Test that streaming endpoints are detected."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success
        paths = {ep.path for ep in result.endpoints}

        # Streaming patterns
        streaming_keywords = ["stream", "listen"]
        streaming_paths = [p for p in paths if any(kw in p.lower() for kw in streaming_keywords)]

        assert len(streaming_paths) == 6, \
            f"Should find exactly 6 streaming endpoints, found {len(streaming_paths)}"

    def test_large_scale_extraction(self, polar_path: str) -> None:
        """Test that extractor handles large codebases efficiently."""
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success

        # Verify we found a substantial number of unique paths
        paths = set(ep.path for ep in result.endpoints)
        assert len(paths) >= 217, \
            f"Should find at least 217 unique paths, found {len(paths)}"

        # Verify multiple HTTP methods per path
        # This indicates proper method extraction
        path_methods = {}
        for ep in result.endpoints:
            if ep.path not in path_methods:
                path_methods[ep.path] = set()
            path_methods[ep.path].add(ep.method)

        multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
        assert len(multi_method_paths) >= 45, \
            f"Expected at least 45 paths with multiple HTTP methods, found {len(multi_method_paths)}"


    def test_response_schemas_exact_counts(self, polar_path: str) -> None:
        """Test exact counts of response schema extraction.

        Polar uses response_model and return type annotations extensively.
        Verifies proper schema extraction from both decorator params and type hints.
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        assert result.success

        # Exact count of endpoints with response schemas
        endpoints_with_schemas = [
            ep for ep in result.endpoints
            if ep.responses and ep.responses[0].response_schema is not None
        ]

        assert len(endpoints_with_schemas) == 332, \
            f"Expected exactly 332 endpoints with response schemas, found {len(endpoints_with_schemas)}"

        # Exact counts by response type
        array_responses = [
            ep for ep in endpoints_with_schemas
            if ep.responses[0].response_schema.type == "array"
        ]
        object_responses = [
            ep for ep in endpoints_with_schemas
            if ep.responses[0].response_schema.type == "object"
        ]

        assert len(array_responses) == 2, \
            f"Expected exactly 2 array responses, found {len(array_responses)}"
        assert len(object_responses) == 330, \
            f"Expected exactly 330 object responses, found {len(object_responses)}"

    def test_specific_endpoint_1_metrics_dashboards(self, polar_path: str) -> None:
        """Test GET /v1/metrics/dashboards returns list[MetricDashboardSchema].

        Reference: https://github.com/polarsource/polar/blob/main/server/polar/metrics/endpoints.py#L295
        Uses response_model=list[MetricDashboardSchema] in decorator.
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        # Find metrics dashboards endpoint
        endpoint = None
        for ep in result.endpoints:
            if ep.path == "/v1/metrics/dashboards" and ep.method == HTTPMethod.GET:
                endpoint = ep
                break

        assert endpoint is not None, "Metrics dashboards endpoint not found"
        assert endpoint.source_line == 295, f"Expected line 295, got {endpoint.source_line}"

        # Verify response schema
        assert len(endpoint.responses) > 0
        response = endpoint.responses[0]
        assert response.response_schema is not None

        # Should be array type from list[MetricDashboardSchema]
        assert response.response_schema.type == "array"
        assert response.response_schema.items is not None
        assert response.response_schema.items.type == "object"

        # Verify MetricDashboardSchema fields
        properties = response.response_schema.items.properties
        assert len(properties) == 3, f"Expected 3 properties, got {len(properties)}"
        assert "name" in properties
        assert "metrics" in properties
        assert "organization_id" in properties

    def test_specific_endpoint_2_organization_get(self, polar_path: str) -> None:
        """Test GET /v1/organizations/{id} returns single Organization object.

        Uses return type annotation for response schema.
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        # Find organization get endpoint
        endpoint = None
        for ep in result.endpoints:
            if ep.path == "/v1/organizations/{id}" and ep.method == HTTPMethod.GET:
                endpoint = ep
                break

        assert endpoint is not None, "Organization GET endpoint not found"
        assert endpoint.source_line == 116

        # Verify response schema
        response = endpoint.responses[0]
        assert response.response_schema is not None
        assert response.response_schema.type == "object"

        # Check Organization schema has many fields
        properties = response.response_schema.properties
        assert len(properties) == 29, f"Expected 29 properties, got {len(properties)}"

        # Verify key fields
        expected_fields = ["email", "website", "status", "details_submitted_at"]
        for field in expected_fields:
            assert field in properties, f"Field '{field}' missing"

    def test_specific_endpoint_3_organization_patch_payout(self, polar_path: str) -> None:
        """Test PATCH /v1/organizations/{id}/payout-account.

        Tests nested path with object response.
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        endpoint = None
        for ep in result.endpoints:
            if ep.path == "/v1/organizations/{id}/payout-account" and ep.method == HTTPMethod.PATCH:
                endpoint = ep
                break

        assert endpoint is not None
        assert endpoint.source_line == 167

        # Verify request body
        assert endpoint.request_body is not None
        assert endpoint.request_body.type == "object"
        req_props = endpoint.request_body.properties
        assert len(req_props) == 1
        assert "payout_account_id" in req_props
        assert req_props["payout_account_id"]["type"] == "string"

        # Verify response
        response = endpoint.responses[0]
        assert response.response_schema is not None
        assert response.response_schema.type == "object"

        properties = response.response_schema.properties
        assert len(properties) == 29
        assert "email" in properties
        assert "default_presentment_currency" in properties

    def test_specific_endpoint_4_organization_kyc(self, polar_path: str) -> None:
        """Test GET /v1/organizations/{id}/kyc.

        Tests KYC endpoint with detailed schema.
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        endpoint = None
        for ep in result.endpoints:
            if ep.path == "/v1/organizations/{id}/kyc" and ep.method == HTTPMethod.GET:
                endpoint = ep
                break

        assert endpoint is not None
        assert endpoint.source_line == 203

        response = endpoint.responses[0]
        assert response.response_schema is not None
        assert response.response_schema.type == "object"

        properties = response.response_schema.properties
        assert len(properties) == 30
        assert "details" in properties
        assert "status" in properties

    def test_specific_endpoint_5_organization_post(self, polar_path: str) -> None:
        """Test POST /v1/organizations/ creates new organization.

        Tests POST endpoint with object response.
        """
        extractor = FastAPIExtractor()
        result = extractor.extract(polar_path)

        endpoint = None
        for ep in result.endpoints:
            if ep.path == "/v1/organizations/" and ep.method == HTTPMethod.POST:
                endpoint = ep
                break

        assert endpoint is not None
        assert endpoint.source_line == 225

        # Verify request body (OrganizationCreate schema)
        assert endpoint.request_body is not None
        assert endpoint.request_body.type == "object"
        req_props = endpoint.request_body.properties
        assert len(req_props) == 16, f"Expected 16 request properties, got {len(req_props)}"

        # Check required fields
        assert "name" in endpoint.request_body.required
        assert "slug" in endpoint.request_body.required

        # Check key request fields
        assert "name" in req_props
        assert "slug" in req_props
        assert "email" in req_props
        assert req_props["name"]["type"] == "string"
        assert req_props["slug"]["type"] == "string"

        # Verify response (Organization schema)
        response = endpoint.responses[0]
        assert response.response_schema is not None
        assert response.response_schema.type == "object"

        properties = response.response_schema.properties
        assert len(properties) == 29
        assert "email" in properties
        assert "website" in properties
        assert "feature_settings" in properties
