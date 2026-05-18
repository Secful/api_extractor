"""Test GET endpoint response schema extraction for Spring Boot."""

from __future__ import annotations

import os

import pytest

from api_extractor.extractors.java.spring_boot import SpringBootExtractor
from api_extractor.core.models import HTTPMethod


@pytest.mark.skipif(
    not os.path.exists(
        os.path.join(
            str(os.path.dirname(__file__)),
            "..", "..", "..", "fixtures",
            "real-world",
            "java",
            "spring-boot",
            "spring-boot-realworld-example-app",
        )
    ),
    reason="Spring Boot RealWorld app not cloned",
)
def test_get_endpoints_have_response_schemas():
    """Verify GET endpoints extract response schemas from return types."""
    fixture_path = os.path.join(
        str(os.path.dirname(__file__)),
        "..", "..", "..", "fixtures",
        "real-world",
        "java",
        "spring-boot",
        "spring-boot-realworld-example-app",
    )

    extractor = SpringBootExtractor()
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

    # List endpoints without schemas
    endpoints_without = [ep for ep in get_endpoints if not (ep.responses and ep.responses[0].response_schema)]
    if endpoints_without:
        print("GET endpoints missing response schemas:")
        for ep in endpoints_without[:10]:
            print(f"  - {ep.method.value} {ep.path}")
            print(f"    Source: {ep.source_file}:{ep.source_line}")
        if len(endpoints_without) > 10:
            print(f"  ... and {len(endpoints_without) - 10} more")
        print()

    # List some endpoints WITH schemas
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

    # Assert: At least 85% coverage
    assert with_schemas / total_gets >= 0.85, \
        f"Expected at least 85% GET endpoints with response schemas, got {with_schemas}/{total_gets}"
