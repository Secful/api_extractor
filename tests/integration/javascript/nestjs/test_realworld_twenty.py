"""Integration tests for NestJS extractor against Twenty CRM real-world codebase."""

import pytest
from pathlib import Path
from api_extractor.extractors.javascript.nestjs import NestJSExtractor


@pytest.fixture
def twenty_repo_path():
    """Path to the Twenty repository."""
    path = Path(__file__).parent.parent.parent.parent / "fixtures" / "real-world" / "javascript" / "nestjs" / "twenty"
    return str(path)


def test_twenty_extraction_completeness(twenty_repo_path):
    """Test extraction coverage against Twenty CRM codebase.

    Twenty is a production NestJS application with:
    - Multiple REST controllers with standard decorators
    - TypeScript DTOs with class-validator decorators
    - Complex type relationships (arrays, unions, promises)
    - Inline object return types
    - Project-relative imports (src/...)
    """
    extractor = NestJSExtractor()
    result = extractor.extract(twenty_repo_path)

    # Count extracted elements
    endpoint_count = len(result.endpoints)
    request_body_count = len([ep for ep in result.endpoints if ep.request_body])
    response_schema_count = len([
        ep for ep in result.endpoints
        if ep.responses and any(r.response_schema for r in ep.responses)
    ])

    # Expected counts based on Twenty server-side REST controllers
    # Controllers analyzed:
    # - DashboardController (1 POST endpoint)
    # - ViewFieldController (GET, GET:id, PATCH, POST, DELETE)
    # - PageLayoutController (GET, GET:id, POST, PATCH, DELETE)
    # - ViewController (GET, GET:id, PATCH, POST, DELETE, POST duplicate)
    # - ViewFilterController (GET, GET:id, PATCH, POST, DELETE)
    # - ViewSortController (GET, GET:id, PATCH, POST, DELETE)
    # - FieldMetadataController (GET, GET:id, PATCH, POST, DELETE)
    # - ObjectMetadataController (GET, GET:id, PATCH, POST, DELETE)
    # - RelationMetadataController (POST, DELETE, GET:id, PATCH)
    # - GraphQLQueryController (GET, POST)
    # - MetadataHealthController (GET)
    # - MetadataModulesController (GET)
    # - RecordController (GET, GET:id, POST, PATCH, DELETE, POST/batch, DELETE/batch)
    # - ServerController (health, about, clientConfig, healthCheck)
    # - EmailController (POST send-password-reset, POST send-invite-link, POST send-verify)
    # - FileController (POST, GET:id/content, POST/upload, POST/uploadImage, GET, DELETE)
    # - WorkspaceMemberController (GET, GET:id, DELETE)
    # - HubSpotController (GET token)
    # - CalendarController (GET channels)
    # - DomainManagerController (GET domains, POST domain, POST validate)
    # - OneDriveController (GET token)
    # - PostgresCredentialsController (GET credentials)
    # - MessagingController (GET channels)
    # - GoogleAPIsController (GET token)
    # - ConnectedAccountController (GET:id/email-aliases, PATCH:id/email-alias, POST:id/email-alias, DELETE:id/email-alias)
    # - TimelineCalendarController (GET)
    # - TimelineMessagingController (GET)
    # - UserVarsController (GET, PATCH)
    # - OAuthController (multiple OAuth GET redirects - ~30 endpoints without return types)
    # - FeatureFlagController (GET, PATCH)
    # - AnalyticsController (POST analytics, POST webhooks)
    # - BillingController (GET subscriptions, PATCH, POST webhooks, POST session, GET product-prices, POST checkout)
    # - WorkspaceController (GET, PATCH, POST activate, POST delete)
    # - RemoteTableController (POST:id/get-columns, POST:id/get-tables)
    # Total: 116+ endpoints

    # Expected response schemas:
    # - Controllers with DTOs: ~65 typed responses
    # - Inline objects: { success: boolean }, { error: string }
    # - OAuth redirects: ~30 endpoints without return types (redirect responses)
    # - Primitives: string, boolean
    # Realistic target: 59-65 schemas (90%+)

    print(f"\n=== Twenty Extraction Results ===")
    print(f"Endpoints: {endpoint_count}")
    print(f"Request bodies: {request_body_count}")
    print(f"Response schemas: {response_schema_count}")

    # Assertions - verify exact coverage
    assert endpoint_count == 116, f"Should extract 116 endpoints, got {endpoint_count}"
    assert request_body_count == 30, f"Should extract 30 request bodies, got {request_body_count}"
    assert response_schema_count == 59, f"Should extract 59 response schemas, got {response_schema_count}"


def test_twenty_dto_resolution(twenty_repo_path):
    """Test that TypeScript DTOs are correctly resolved and mapped to schemas."""
    extractor = NestJSExtractor()
    result = extractor.extract(twenty_repo_path)

    # Find ViewFieldController POST /rest/metadata/viewFields
    view_field_post = next(
        (ep for ep in result.endpoints if ep.path == "/rest/metadata/viewFields" and ep.method.value == "POST"),
        None
    )
    assert view_field_post is not None, "ViewField POST endpoint should be extracted"

    # Should have request body from CreateViewFieldInput
    assert view_field_post.request_body is not None, "Should have request body"
    assert view_field_post.request_body.properties, "Request body should have properties"

    # Should have response from ViewFieldDTO
    assert view_field_post.responses, "Should have responses"
    assert any(r.response_schema for r in view_field_post.responses), "Should have response schema"


def test_twenty_array_return_types(twenty_repo_path):
    """Test that array return types (Promise<DTO[]>) are correctly extracted."""
    extractor = NestJSExtractor()
    result = extractor.extract(twenty_repo_path)

    # Find ViewFieldController GET /rest/metadata/viewFields (returns array)
    view_fields_get = next(
        (ep for ep in result.endpoints if ep.path == "/rest/metadata/viewFields" and ep.method.value == "GET"),
        None
    )
    assert view_fields_get is not None, "ViewFields GET endpoint should be extracted"
    assert view_fields_get.responses, "Should have responses"

    # Find response with schema
    response_with_schema = next((r for r in view_fields_get.responses if r.response_schema), None)
    assert response_with_schema is not None, "Should have response schema"
    assert response_with_schema.response_schema.type == "array", "Should be array type"


def test_twenty_inline_object_return_types(twenty_repo_path):
    """Test that inline object return types are correctly extracted."""
    extractor = NestJSExtractor()
    result = extractor.extract(twenty_repo_path)

    # Find ViewFieldController DELETE (returns { success: boolean })
    view_field_delete = next(
        (ep for ep in result.endpoints if "/rest/metadata/viewFields/" in ep.path and ep.method.value == "DELETE"),
        None
    )
    assert view_field_delete is not None, "ViewField DELETE endpoint should be extracted"
    assert view_field_delete.responses, "Should have responses"

    # Find response with schema
    response_with_schema = next((r for r in view_field_delete.responses if r.response_schema), None)
    assert response_with_schema is not None, "Should have response schema"
    assert response_with_schema.response_schema.properties, "Should have properties"
    assert "success" in response_with_schema.response_schema.properties, "Should have success property"


def test_twenty_project_relative_imports(twenty_repo_path):
    """Test that project-relative imports (src/...) are correctly resolved."""
    extractor = NestJSExtractor()
    result = extractor.extract(twenty_repo_path)

    # Twenty uses project-relative imports - verify DTOs are resolved
    # Count endpoints with request bodies (should be 30 if imports work)
    with_request_body = [ep for ep in result.endpoints if ep.request_body]
    assert len(with_request_body) == 30, f"Should resolve 30 request bodies from imports, got {len(with_request_body)}"
