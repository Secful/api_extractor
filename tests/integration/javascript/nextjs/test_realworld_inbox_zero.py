"""Integration tests for inbox-zero - Next.js + Zod real-world project."""

from __future__ import annotations

import os

import pytest

from api_extractor.core.models import FrameworkType, HTTPMethod
from api_extractor.extractors.javascript.nextjs import NextJSExtractor


@pytest.fixture(scope="class")
def inbox_zero_path():
    """Get path to inbox-zero fixture."""
    path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "javascript",
        "nextjs",
        "inbox-zero",
        "apps",
        "web",
        "app",
        "api",
    )
    if not os.path.exists(path):
        pytest.skip("inbox-zero fixture not available (run: git submodule update --init --depth 1)")
    return path


@pytest.fixture(scope="class")
def inbox_zero_extraction_result(inbox_zero_path):
    """Extract endpoints from inbox-zero once and reuse across tests."""
    extractor = NextJSExtractor()
    return extractor.extract(inbox_zero_path)


class TestInboxZero:
    """Integration tests for inbox-zero - Next.js App Router + Zod validation."""

    def test_extraction_succeeds(self, inbox_zero_extraction_result) -> None:
        """Test that extraction from inbox-zero completes successfully.

        Repository: https://github.com/elie222/inbox-zero
        Stars: 10,632
        Description: AI personal assistant for email. Open source app to reach inbox zero fast.
        Tech: Next.js App Router + Zod 4.2.1 + TypeScript + Prisma
        """
        result = inbox_zero_extraction_result

        assert result.success is True
        assert len(result.endpoints) == 173

    def test_framework_detected(self, inbox_zero_extraction_result) -> None:
        """Test that Next.js framework is detected."""
        result = inbox_zero_extraction_result

        assert result.frameworks_detected == [FrameworkType.NEXTJS]

    def test_http_methods_detected(self, inbox_zero_extraction_result) -> None:
        """Test that various HTTP methods are detected."""
        result = inbox_zero_extraction_result

        methods = {ep.method for ep in result.endpoints}
        assert len(methods) == 6

        # inbox-zero has GET, POST, PUT, DELETE, PATCH, OPTIONS endpoints
        assert HTTPMethod.GET in methods
        assert HTTPMethod.POST in methods

    def test_source_tracking(self, inbox_zero_extraction_result) -> None:
        """Test that source files and line numbers are tracked."""
        result = inbox_zero_extraction_result

        for ep in result.endpoints:
            assert ep.source_file is not None, f"Endpoint {ep.path} missing source_file"
            assert ep.source_file.endswith((".ts", ".js")), \
                f"Expected .ts/.js file, got: {ep.source_file}"
            assert ep.source_line is not None, f"Endpoint {ep.path} missing source_line"
            assert isinstance(ep.source_line, int) and ep.source_line >= 1, \
                f"Invalid line number for {ep.path}: {ep.source_line}"

    def test_zod_schemas_extracted(self, inbox_zero_extraction_result) -> None:
        """Test that Zod validation schemas are extracted and linked to endpoints."""
        result = inbox_zero_extraction_result

        # Find endpoints with request bodies (POST, PUT, PATCH methods)
        endpoints_with_body = [
            ep for ep in result.endpoints
            if ep.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]
            and ep.request_body is not None
        ]

        # inbox-zero uses Zod for validation (with @/ path alias support)
        assert len(endpoints_with_body) == 23

        # Verify at least one schema has proper structure
        schemas_with_properties = [
            ep for ep in endpoints_with_body
            if ep.request_body.type == "object" and ep.request_body.properties
        ]
        assert len(schemas_with_properties) >= 1

    def test_request_and_response_schemas(self, inbox_zero_extraction_result) -> None:
        """Test extraction counts for request and response schemas."""
        result = inbox_zero_extraction_result

        # Request bodies (from Zod schemas)
        with_request_body = [ep for ep in result.endpoints if ep.request_body is not None]
        assert len(with_request_body) == 23

        # Response schemas (from TypeScript types + inline objects)
        with_response_schema = [
            ep for ep in result.endpoints
            if ep.responses and any(r.response_schema for r in ep.responses)
        ]
        # 1 endpoint uses NextResponse.json<Type>() pattern
        # 41 endpoints use inline objects with literal values: NextResponse.json({ status: "ok" })
        # Improved inline object detection now extracts more response schemas
        # Filtered out: error-only responses ({error: string}) from wrapped handlers
        # Not extracted: responses with dynamic values (variables, function calls)
        assert len(with_response_schema) == 42

        # Verify typed generic response (NextResponse.json<T>)
        typed_endpoint = next(
            ep for ep in with_response_schema
            if ep.path == "/api/mcp/{integration}/auth-url"
        )
        typed_response = typed_endpoint.responses[0]
        assert typed_response.response_schema is not None
        assert typed_response.response_schema.type == "object"
        assert "url" in typed_response.response_schema.properties

        # Verify inline object response (NextResponse.json({ ... }))
        inline_endpoints = [
            ep for ep in with_response_schema
            if ep.path != "/api/mcp/{integration}/auth-url"
        ]
        assert len(inline_endpoints) == 41

        # Sample check - inline object with literal values
        sample = next(
            ep for ep in inline_endpoints
            if ep.path == "/api/clean" and ep.method.value == "POST"
        )
        sample_response = sample.responses[0]
        assert sample_response.response_schema is not None
        assert sample_response.response_schema.type == "object"
        assert "success" in sample_response.response_schema.properties
        assert sample_response.response_schema.properties["success"]["type"] == "boolean"

    def test_path_parameters_extracted(self, inbox_zero_extraction_result) -> None:
        """Test that dynamic route parameters are extracted."""
        result = inbox_zero_extraction_result

        # Find endpoints with path parameters (dynamic routes like [id])
        endpoints_with_params = [
            ep for ep in result.endpoints
            if "{" in ep.path  # OpenAPI format for path params
        ]

        assert len(endpoints_with_params) == 23

        # Verify parameter structure - check first endpoint
        ep = endpoints_with_params[0]
        path_params = [p for p in ep.parameters if p.location.value == "path"]
        assert len(path_params) >= 1

    def test_endpoint_count_realistic(self, inbox_zero_extraction_result) -> None:
        """Test that endpoint count is realistic for project size."""
        result = inbox_zero_extraction_result

        # inbox-zero has 30+ API route directories with multiple HTTP methods per route
        assert len(result.endpoints) == 173

    def test_unique_operation_ids(self, inbox_zero_extraction_result) -> None:
        """Test that all endpoints have unique operation IDs."""
        result = inbox_zero_extraction_result

        operation_ids = [ep.operation_id for ep in result.endpoints if ep.operation_id]
        assert len(operation_ids) == len(set(operation_ids)), "Operation IDs should be unique"
