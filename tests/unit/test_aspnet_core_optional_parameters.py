"""Unit tests for ASP.NET Core optional parameter handling."""

from __future__ import annotations

import tempfile
from pathlib import Path

from api_extractor.extractors.csharp.aspnet_core import ASPNETCoreExtractor


def test_optional_parameter_in_path() -> None:
    """Test that optional parameters (marked with ?) are correctly extracted.

    Note: In OpenAPI specification, path parameters MUST always be required=True.
    The ? in ASP.NET Core routes indicates optional routing, but we document
    the path as if the parameter is present, and it's marked as required in OpenAPI.
    """
    code = '''
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class ProductsController : ControllerBase
{
    [HttpGet("type/{typeId}/brand/{brandId?}")]
    public IActionResult GetProducts(int typeId, int? brandId)
    {
        return Ok();
    }
}
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "controller.cs"
        file_path.write_text(code)

        extractor = ASPNETCoreExtractor()
        routes = extractor.extract_routes_from_file(str(file_path))

        assert len(routes) == 1
        route = routes[0]

        # Check that path is normalized (? removed)
        assert route.path == "/api/products/type/{typeId}/brand/{brandId}"

        # Convert to endpoint to check parameters
        endpoints = extractor._route_to_endpoints(route)
        assert len(endpoints) == 1
        endpoint = endpoints[0]

        # Check parameters
        assert len(endpoint.parameters) == 2

        # Both parameters should be required (OpenAPI spec requirement for path params)
        type_id_param = next(p for p in endpoint.parameters if p.name == "typeId")
        assert type_id_param.required is True

        brand_id_param = next(p for p in endpoint.parameters if p.name == "brandId")
        assert brand_id_param.required is True  # OpenAPI requires path params to be required


def test_optional_parameter_with_constraint() -> None:
    """Test optional parameters with simple type constraints.

    Note: In OpenAPI specification, path parameters MUST always be required=True.
    The ? in ASP.NET Core routes indicates optional routing, but we document
    the path as if the parameter is present, and it's marked as required in OpenAPI.
    """
    code = '''
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class ItemsController : ControllerBase
{
    [HttpGet("{id:int}/{slug:alpha?}")]
    public IActionResult GetItem(int id, string? slug)
    {
        return Ok();
    }
}
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "controller.cs"
        file_path.write_text(code)

        extractor = ASPNETCoreExtractor()
        routes = extractor.extract_routes_from_file(str(file_path))

        assert len(routes) == 1
        route = routes[0]

        # Check that path is normalized (constraint and ? removed)
        assert route.path == "/api/items/{id}/{slug}"

        # Convert to endpoint to check parameters
        endpoints = extractor._route_to_endpoints(route)
        assert len(endpoints) == 1
        endpoint = endpoints[0]

        # Check parameters
        assert len(endpoint.parameters) == 2

        # id should be required
        id_param = next(p for p in endpoint.parameters if p.name == "id")
        assert id_param.required is True

        # slug should be required (OpenAPI spec requirement for path params)
        slug_param = next(p for p in endpoint.parameters if p.name == "slug")
        assert slug_param.required is True  # OpenAPI requires path params to be required


def test_multiple_optional_parameters() -> None:
    """Test route with multiple optional parameters.

    Note: In OpenAPI specification, path parameters MUST always be required=True.
    The ? in ASP.NET Core routes indicates optional routing, but we document
    the path as if the parameter is present, and it's marked as required in OpenAPI.
    """
    code = '''
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class SearchController : ControllerBase
{
    [HttpGet("{query}/{page?}/{size?}")]
    public IActionResult Search(string query, int? page, int? size)
    {
        return Ok();
    }
}
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "controller.cs"
        file_path.write_text(code)

        extractor = ASPNETCoreExtractor()
        routes = extractor.extract_routes_from_file(str(file_path))

        assert len(routes) == 1
        route = routes[0]

        # Check that path is normalized
        assert route.path == "/api/search/{query}/{page}/{size}"

        # Convert to endpoint to check parameters
        endpoints = extractor._route_to_endpoints(route)
        assert len(endpoints) == 1
        endpoint = endpoints[0]

        # Check parameters
        assert len(endpoint.parameters) == 3

        # query should be required
        query_param = next(p for p in endpoint.parameters if p.name == "query")
        assert query_param.required is True

        # page should be required (OpenAPI spec requirement for path params)
        page_param = next(p for p in endpoint.parameters if p.name == "page")
        assert page_param.required is True  # OpenAPI requires path params to be required

        # size should be required (OpenAPI spec requirement for path params)
        size_param = next(p for p in endpoint.parameters if p.name == "size")
        assert size_param.required is True  # OpenAPI requires path params to be required
