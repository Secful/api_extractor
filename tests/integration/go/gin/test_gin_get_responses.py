"""Test GET endpoint response schema extraction for Gin."""

from __future__ import annotations

import os

import pytest

from api_extractor.extractors.go.gin import GinExtractor
from api_extractor.core.models import HTTPMethod


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..", "..", "..", "fixtures",
            "real-world",
            "go",
            "gin",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_get_endpoints_have_response_schemas():
    """Verify GET endpoints extract response schemas from c.JSON calls."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "go",
        "gin",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Find GET endpoints
    get_endpoints = [ep for ep in result.endpoints if ep.method == HTTPMethod.GET]
    assert len(get_endpoints) > 0, "Should have GET endpoints"

    # Check response schemas
    endpoints_with_schemas = [
        ep for ep in get_endpoints
        if ep.responses and ep.responses[0].response_schema
    ]

    # Report findings
    total_gets = len(get_endpoints)
    with_schemas = len(endpoints_with_schemas)

    print(f"\n{'='*60}")
    print(f"GET Response Schema Coverage:")
    print(f"  Total GET endpoints: {total_gets}")
    print(f"  With response schemas: {with_schemas}")
    print(f"  Coverage: {with_schemas/total_gets*100:.1f}%")
    print(f"{'='*60}\n")

    # List endpoints without schemas for debugging
    endpoints_without = [ep for ep in get_endpoints if not (ep.responses and ep.responses[0].response_schema)]
    if endpoints_without:
        print("GET endpoints missing response schemas:")
        for ep in endpoints_without:
            print(f"  - {ep.method.value} {ep.path}")
            print(f"    Source: {ep.source_file}:{ep.source_line}")
        print()

    # List some endpoints WITH schemas to verify extraction works
    if endpoints_with_schemas:
        print("Sample GET endpoints WITH response schemas:")
        for ep in endpoints_with_schemas[:5]:
            schema = ep.responses[0].response_schema
            print(f"  - {ep.method.value} {ep.path}")
            if schema:
                if hasattr(schema, 'properties') and schema.properties:
                    props = list(schema.properties.keys())[:3]
                    print(f"    Schema properties: {props}")
                elif hasattr(schema, 'type'):
                    print(f"    Schema type: {schema.type}")
        print()

    # Assert: At least 85% of GET endpoints should have response schemas
    # (realworld app uses gin.H, struct responses, and serializer patterns)
    assert with_schemas / total_gets >= 0.85, \
        f"Expected at least 85% GET endpoints with response schemas, got {with_schemas}/{total_gets}"


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..", "..", "..", "fixtures",
            "real-world",
            "go",
            "gin",
            "golang-gin-realworld-example-app",
        )
    ),
    reason="RealWorld Gin app not cloned",
)
def test_ping_endpoint_has_gin_h_response():
    """Verify ping endpoint with inline gin.H response extracts schema."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "go",
        "gin",
        "golang-gin-realworld-example-app",
    )

    extractor = GinExtractor()
    result = extractor.extract(fixture_path)

    assert result.success

    # Find ping endpoint
    ping = [ep for ep in result.endpoints if "/ping" in ep.path and ep.method == HTTPMethod.GET]
    assert len(ping) > 0, "Should find ping endpoint"

    ping_ep = ping[0]

    # Verify has response
    assert ping_ep.responses, "Ping should have responses"
    assert len(ping_ep.responses) > 0, "Ping should have at least one response"

    # Verify has response schema
    response_schema = ping_ep.responses[0].response_schema
    assert response_schema is not None, "Ping response should have schema"

    # Verify schema has "message" property (from gin.H{"message": "pong"})
    assert hasattr(response_schema, 'properties'), "Schema should have properties"
    assert "message" in response_schema.properties, \
        f"Schema should have 'message' property, got: {list(response_schema.properties.keys())}"

    # Verify message is string type
    message_prop = response_schema.properties["message"]
    assert message_prop.get("type") == "string", \
        f"Message should be string type, got: {message_prop.get('type')}"

    print(f"\n{'='*60}")
    print(f"✓ Ping endpoint response schema extracted successfully")
    print(f"  Path: {ping_ep.path}")
    print(f"  Schema properties: {list(response_schema.properties.keys())}")
    print(f"{'='*60}\n")
