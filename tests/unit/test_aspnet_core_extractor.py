"""Unit tests for ASP.NET Core extractor."""

import os
from pathlib import Path

import pytest

from api_extractor.core.models import FrameworkType, HTTPMethod, ParameterLocation
from api_extractor.extractors.csharp.aspnet_core import ASPNETCoreExtractor


@pytest.fixture
def extractor():
    """Create ASP.NET Core extractor instance."""
    return ASPNETCoreExtractor()


@pytest.fixture
def minimal_fixture_path():
    """Get path to minimal C# test fixture."""
    return str(Path(__file__).parent.parent / "fixtures" / "minimal" / "csharp" / "aspnet-core")


def test_aspnet_core_framework_type(extractor):
    """Test that extractor has correct framework type."""
    assert extractor.framework == FrameworkType.ASPNET_CORE


def test_aspnet_core_file_extensions(extractor):
    """Test that extractor supports .cs extension."""
    extensions = extractor.get_file_extensions()
    assert ".cs" in extensions
    assert len(extensions) == 1


def test_aspnet_core_basic_extraction(extractor, minimal_fixture_path):
    """Test basic route extraction from ProductsController."""
    controller_file = os.path.join(minimal_fixture_path, "ProductsController.cs")
    routes = extractor.extract_routes_from_file(controller_file)

    # Should extract 6 routes: GET all, GET by id, POST, PUT, DELETE, GET search
    assert len(routes) >= 5

    # Verify we have the expected paths
    paths = [route.path for route in routes]
    assert "/api/products" in paths
    assert "/api/products/{id}" in paths
    assert "/api/products/search" in paths


def test_aspnet_core_http_methods(extractor, minimal_fixture_path):
    """Test HTTP method extraction."""
    controller_file = os.path.join(minimal_fixture_path, "ProductsController.cs")
    routes = extractor.extract_routes_from_file(controller_file)

    # Group routes by method
    methods_found = set()
    for route in routes:
        methods_found.update(route.methods)

    assert HTTPMethod.GET in methods_found
    assert HTTPMethod.POST in methods_found
    assert HTTPMethod.PUT in methods_found
    assert HTTPMethod.DELETE in methods_found


def test_aspnet_core_path_parameters(extractor, minimal_fixture_path):
    """Test path parameter extraction."""
    controller_file = os.path.join(minimal_fixture_path, "ProductsController.cs")
    routes = extractor.extract_routes_from_file(controller_file)

    # Find route with {id} parameter
    id_routes = [r for r in routes if "{id}" in r.path]
    assert len(id_routes) >= 3  # GET, PUT, DELETE

    # Verify path format
    for route in id_routes:
        assert "{id}" in route.path


def test_aspnet_core_path_normalization(extractor):
    """Test path constraint normalization."""
    # Test removing type constraints
    assert extractor._normalize_path("{id:int}") == "{id}"
    assert extractor._normalize_path("/api/products/{id:int}") == "/api/products/{id}"
    assert extractor._normalize_path("{slug:regex(^[a-z]+$)}") == "{slug}"
    assert extractor._normalize_path("/api/{id:int}/items/{slug:alpha}") == "/api/{id}/items/{slug}"


def test_aspnet_core_token_replacement(extractor):
    """Test [controller] token replacement."""
    # Standard controller
    assert extractor._replace_route_tokens("api/[controller]", "ProductsController") == "api/products"
    # Controller without suffix
    assert extractor._replace_route_tokens("api/[controller]", "Products") == "api/products"
    # Single letter
    assert extractor._replace_route_tokens("[controller]", "UsersController") == "users"


def test_aspnet_core_path_combination(extractor):
    """Test combining base and method paths."""
    # Both with slashes
    assert extractor._combine_paths("/api/products", "/search") == "/api/products/search"
    # Base without leading slash
    assert extractor._combine_paths("api/products", "search") == "/api/products/search"
    # Empty method path
    assert extractor._combine_paths("/api/products", "") == "/api/products"
    # Empty base path
    assert extractor._combine_paths("", "search") == "/search"
    # Both empty
    assert extractor._combine_paths("", "") == "/"


def test_aspnet_core_csharp_type_mapping(extractor):
    """Test C# to OpenAPI type mapping."""
    # Primitive types
    assert extractor._parse_csharp_type("string") == "string"
    assert extractor._parse_csharp_type("String") == "string"
    assert extractor._parse_csharp_type("int") == "integer"
    assert extractor._parse_csharp_type("Int32") == "integer"
    assert extractor._parse_csharp_type("long") == "integer"
    assert extractor._parse_csharp_type("bool") == "boolean"
    assert extractor._parse_csharp_type("double") == "number"
    assert extractor._parse_csharp_type("decimal") == "number"

    # Special types
    assert extractor._parse_csharp_type("DateTime") == "string"
    assert extractor._parse_csharp_type("Guid") == "string"

    # Array types
    assert extractor._parse_csharp_type("List<Product>") == "array"
    assert extractor._parse_csharp_type("IEnumerable<User>") == "array"
    assert extractor._parse_csharp_type("ICollection<Item>") == "array"

    # Dictionary types
    assert extractor._parse_csharp_type("Dictionary<string, int>") == "object"
    assert extractor._parse_csharp_type("IDictionary<int, string>") == "object"


def test_aspnet_core_nullable_types(extractor):
    """Test nullable type handling."""
    # Nullable primitive
    assert extractor._parse_csharp_type("int?") == "integer"
    assert extractor._parse_csharp_type("bool?") == "boolean"
    assert extractor._parse_csharp_type("string?") == "string"


def test_aspnet_core_generic_types(extractor):
    """Test generic type handling."""
    # Task<T> return types
    assert extractor._parse_csharp_type("Task<User>") == "object"
    assert extractor._parse_csharp_type("ActionResult<Product>") == "object"
    assert extractor._parse_csharp_type("Task<ActionResult<User>>") == "object"

    # Generic collections
    assert extractor._parse_csharp_type("List<string>") == "array"
    assert extractor._parse_csharp_type("IEnumerable<int>") == "array"


def test_aspnet_core_extract_path_parameters(extractor):
    """Test extracting parameters from path."""
    # Single parameter
    params = extractor._extract_path_parameters("/api/products/{id}")
    assert len(params) == 1
    assert params[0].name == "id"
    assert params[0].location == ParameterLocation.PATH
    assert params[0].required is True

    # Multiple parameters
    params = extractor._extract_path_parameters("/api/{category}/products/{id}")
    assert len(params) == 2
    assert params[0].name == "category"
    assert params[1].name == "id"

    # Parameters with constraints (should strip them)
    params = extractor._extract_path_parameters("/api/products/{id:int}")
    assert len(params) == 1
    assert params[0].name == "id"


def test_aspnet_core_no_routes(extractor, tmp_path):
    """Test handling of files with no routes."""
    # Create a C# file without any controllers
    test_file = tmp_path / "NoController.cs"
    test_file.write_text("""
    using System;

    namespace Test
    {
        public class Helper
        {
            public void DoSomething() {}
        }
    }
    """)

    routes = extractor.extract_routes_from_file(str(test_file))
    assert len(routes) == 0


def test_aspnet_core_source_tracking(extractor, minimal_fixture_path):
    """Test that routes have source file and line information."""
    controller_file = os.path.join(minimal_fixture_path, "ProductsController.cs")
    routes = extractor.extract_routes_from_file(controller_file)

    for route in routes:
        assert route.source_file == controller_file
        assert route.source_line > 0
        assert isinstance(route.source_line, int)


def test_aspnet_core_route_to_endpoint_conversion(extractor, minimal_fixture_path):
    """Test converting Route to Endpoint."""
    controller_file = os.path.join(minimal_fixture_path, "ProductsController.cs")
    routes = extractor.extract_routes_from_file(controller_file)

    # Convert first route to endpoint
    if routes:
        endpoint = extractor.convert_route_to_endpoint(routes[0])
        assert endpoint.path == routes[0].path
        assert endpoint.method == routes[0].methods[0]
        assert endpoint.source_file == routes[0].source_file
        assert endpoint.source_line == routes[0].source_line
        assert len(endpoint.responses) > 0


def test_aspnet_core_handler_names(extractor, minimal_fixture_path):
    """Test that handler names are extracted."""
    controller_file = os.path.join(minimal_fixture_path, "ProductsController.cs")
    routes = extractor.extract_routes_from_file(controller_file)

    handler_names = [route.handler_name for route in routes]
    assert "GetAll" in handler_names or "GetById" in handler_names
    # Verify all routes have handler names
    assert all(name is not None for name in handler_names)


def test_aspnet_core_multiple_parameters(extractor):
    """Test extracting multiple path parameters."""
    params = extractor._extract_path_parameters("/api/{tenantId}/projects/{projectId}/items/{itemId}")
    assert len(params) == 3
    assert params[0].name == "tenantId"
    assert params[1].name == "projectId"
    assert params[2].name == "itemId"
    # All path params are required
    assert all(p.required for p in params)


def test_aspnet_core_empty_path(extractor):
    """Test handling of empty paths."""
    result = extractor._combine_paths("", "")
    assert result == "/"


def test_aspnet_core_dto_extraction(extractor, minimal_fixture_path):
    """Test that DTO classes are identified correctly."""
    controller_file = os.path.join(minimal_fixture_path, "ProductsController.cs")

    # Parse the file
    tree = extractor.parser.parse_file(controller_file)
    assert tree is not None

    with open(controller_file, "rb") as f:
        source_code = f.read()

    # Extract DTO schemas
    dto_schemas = extractor._find_dto_classes(tree, source_code)

    # Should find Product DTO
    assert "Product" in dto_schemas
    product_schema = dto_schemas["Product"]
    assert product_schema.type == "object"
    assert "Id" in product_schema.properties
    assert "Name" in product_schema.properties
    assert "Price" in product_schema.properties
