"""Integration tests for Qinglong - Joi/Celebrate validation extraction."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import HTTPMethod
from api_extractor.extractors.javascript.express import ExpressExtractor


@pytest.fixture
def qinglong_path():
    """Get path to Qinglong fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..",
        "fixtures",
        "real-world",
        "javascript",
        "express",
        "qinglong-joi",
        "back",
    )
    if not os.path.exists(path):
        pytest.skip("Qinglong fixture not available (run: git submodule update --init)")
    return path


class TestQinglongJoi:
    """Integration tests for Qinglong - Joi/Celebrate validation."""

    def test_extraction_succeeds(self, qinglong_path: str) -> None:
        """Test that extraction from Qinglong succeeds.

        Repository: https://github.com/whyour/qinglong
        Stars: 19,532
        Description: Task scheduling and automation platform
        Validation: Celebrate (Joi middleware for Express)
        """
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success, "Extraction should succeed"
        assert len(result.endpoints) == 123, "Should find 123 endpoints"

    def test_joi_validation_detected(self, qinglong_path: str) -> None:
        """Test that Joi/Celebrate validation is detected and extracted."""
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success

        # Find endpoints with validation
        endpoints_with_validation = [
            ep for ep in result.endpoints
            if ep.request_body is not None or len(ep.parameters) > 0
        ]

        assert len(endpoints_with_validation) == 58, \
            "Should find 58 endpoints with Joi validation"

    def test_query_parameter_validation(self, qinglong_path: str) -> None:
        """Test that query parameter validation is extracted correctly."""
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success

        # Find endpoints with query parameters
        endpoints_with_query = [
            ep for ep in result.endpoints
            if any(p.location.value == "query" for p in ep.parameters)
        ]

        assert len(endpoints_with_query) == 1, \
            "Should find 1 endpoint with query parameter validation"

        # Verify query parameters are in parameters array, not request_body
        for ep in endpoints_with_query:
            query_params = [p for p in ep.parameters if p.location.value == "query"]
            assert len(query_params) >= 1, \
                f"Endpoint {ep.path} should have at least 1 query parameter"

    def test_body_parameter_validation(self, qinglong_path: str) -> None:
        """Test that request body validation is extracted correctly."""
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success

        # Find POST/PUT endpoints with body validation
        endpoints_with_body = [
            ep for ep in result.endpoints
            if ep.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]
            and ep.request_body is not None
        ]

        assert len(endpoints_with_body) == 42, \
            "Should find 42 POST/PUT/PATCH endpoints with body validation"

        # Verify body validation has properties
        for ep in endpoints_with_body:
            assert ep.request_body.properties is not None or ep.request_body.type is not None, \
                f"Endpoint {ep.method.value} {ep.path} should have body schema"

    def test_celebrate_config_pattern(self, qinglong_path: str) -> None:
        """Test that celebrate config pattern (multiple locations) is handled.

        Celebrate uses: celebrate({ query: Joi.object(), body: Joi.object() })
        This test verifies we can handle both query and body validation if they exist.
        """
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success

        # Count endpoints with different validation types
        endpoints_with_body = [
            ep for ep in result.endpoints if ep.request_body is not None
        ]
        endpoints_with_query = [
            ep for ep in result.endpoints if len(ep.parameters) > 0
        ]

        # Qinglong should have endpoints with at least one type of validation
        assert len(endpoints_with_body) == 45, "Should have 45 endpoints with body validation"
        assert len(endpoints_with_query) == 14, "Should have 14 endpoints with query parameters"

        # Verify endpoints with body and query validation can handle both
        endpoints_with_body_and_query = [
            ep for ep in result.endpoints
            if ep.request_body is not None
            and any(p.location.value == "query" for p in ep.parameters)
        ]

        if len(endpoints_with_body_and_query) > 0:
            ep = endpoints_with_body_and_query[0]
            assert ep.request_body is not None, \
                "Should have body validation"
            assert len([p for p in ep.parameters if p.location.value == "query"]) >= 1, \
                "Should have at least 1 query parameter"

    def test_http_methods_coverage(self, qinglong_path: str) -> None:
        """Test that various HTTP methods are detected."""
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success
        methods = {ep.method for ep in result.endpoints}

        assert HTTPMethod.GET in methods, "Should find GET endpoints"
        assert HTTPMethod.POST in methods, "Should find POST endpoints"

    def test_source_tracking(self, qinglong_path: str) -> None:
        """Test that source files and line numbers are tracked."""
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith(".ts"), \
                f"Expected .ts file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert ep.source_line > 0, f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_validation_schema_structure(self, qinglong_path: str) -> None:
        """Test that extracted validation schemas have proper structure."""
        extractor = ExpressExtractor()
        result = extractor.extract(qinglong_path)

        assert result.success

        # Find an endpoint with body validation
        endpoints_with_body = [
            ep for ep in result.endpoints
            if ep.request_body is not None and ep.request_body.properties
        ]

        if len(endpoints_with_body) > 0:
            ep = endpoints_with_body[0]
            schema = ep.request_body

            # Verify schema structure
            assert schema.type == "object", \
                "Body schema should be object type"
            assert isinstance(schema.properties, dict), \
                "Schema should have properties dict"

            # Verify property structure
            for prop_name, prop_schema in schema.properties.items():
                assert isinstance(prop_schema, dict), \
                    f"Property {prop_name} should be a dict"
                assert "type" in prop_schema, \
                    f"Property {prop_name} should have type"
