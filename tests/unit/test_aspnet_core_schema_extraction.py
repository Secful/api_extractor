"""Tests for ASP.NET Core schema extraction."""

from api_extractor.extractors.csharp.aspnet_core import ASPNETCoreExtractor
from api_extractor.core.models import HTTPMethod
import pytest


@pytest.fixture
def extractor():
    """Create ASP.NET Core extractor instance."""
    return ASPNETCoreExtractor()


def test_extract_return_type_simple(extractor, tmp_path):
    """Test extraction of simple return types."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;

    public class User
    {
        public string Name { get; set; }
    }

    [ApiController]
    [Route("api/test")]
    public class TestController : ControllerBase
    {
        [HttpGet]
        public User GetUser()
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "TestController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.method == HTTPMethod.GET
    assert endpoint.path == "/api/test"
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "Name" in endpoint.responses[0].response_schema.properties


def test_extract_return_type_ienumerable(extractor, tmp_path):
    """Test extraction of IEnumerable<T> return types."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;
    using System.Collections.Generic;

    public class Product
    {
        public int Id { get; set; }
        public string Name { get; set; }
    }

    [ApiController]
    [Route("api/products")]
    public class ProductsController : ControllerBase
    {
        [HttpGet]
        public IEnumerable<Product> GetAll()
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "ProductsController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "array"
    assert endpoint.responses[0].response_schema.items is not None
    assert endpoint.responses[0].response_schema.items.type == "object"
    assert "Id" in endpoint.responses[0].response_schema.items.properties
    assert "Name" in endpoint.responses[0].response_schema.items.properties


def test_request_body_extraction(extractor, tmp_path):
    """Test extraction of [FromBody] schemas."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;

    public class CreateUserRequest
    {
        public string Username { get; set; }
        public string Email { get; set; }
    }

    public class User
    {
        public int Id { get; set; }
        public string Username { get; set; }
    }

    [ApiController]
    [Route("api/users")]
    public class UsersController : ControllerBase
    {
        [HttpPost]
        public User CreateUser([FromBody] CreateUserRequest request)
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "UsersController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.method == HTTPMethod.POST
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "Username" in endpoint.request_body.properties
    assert "Email" in endpoint.request_body.properties

    # Verify response schema too
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "Id" in endpoint.responses[0].response_schema.properties
    assert "Username" in endpoint.responses[0].response_schema.properties


def test_action_result_wrapper(extractor, tmp_path):
    """Test that ActionResult<T> is unwrapped to T."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;

    public class Product
    {
        public string Name { get; set; }
    }

    [ApiController]
    [Route("api/products")]
    public class ProductsController : ControllerBase
    {
        [HttpGet]
        public ActionResult<Product> GetProduct()
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "ProductsController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "Name" in endpoint.responses[0].response_schema.properties


def test_task_wrapper(extractor, tmp_path):
    """Test that Task<T> is unwrapped to T."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;
    using System.Threading.Tasks;

    public class Item
    {
        public string Title { get; set; }
    }

    [ApiController]
    [Route("api/items")]
    public class ItemsController : ControllerBase
    {
        [HttpGet]
        public Task<Item> GetItem()
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "ItemsController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "Title" in endpoint.responses[0].response_schema.properties


def test_nested_async_wrappers(extractor, tmp_path):
    """Test Task<ActionResult<T>> double wrapper unwrapping."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;
    using System.Threading.Tasks;

    public class Order
    {
        public int OrderId { get; set; }
    }

    [ApiController]
    [Route("api/orders")]
    public class OrdersController : ControllerBase
    {
        [HttpGet]
        public Task<ActionResult<Order>> GetOrder()
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "OrdersController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "OrderId" in endpoint.responses[0].response_schema.properties


def test_void_return_type(extractor, tmp_path):
    """Test that void return types don't create response schemas."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;

    [ApiController]
    [Route("api/users")]
    public class UsersController : ControllerBase
    {
        [HttpDelete("{id}")]
        public void DeleteUser([FromRoute] int id)
        {
        }
    }
    """

    file_path = tmp_path / "UsersController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.method == HTTPMethod.DELETE
    # Void methods should not have a response schema
    assert endpoint.responses[0].response_schema is None


def test_request_body_with_list(extractor, tmp_path):
    """Test extraction of List<T> in request body."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;
    using System.Collections.Generic;

    public class User
    {
        public string Name { get; set; }
    }

    [ApiController]
    [Route("api/users")]
    public class UsersController : ControllerBase
    {
        [HttpPost("batch")]
        public void CreateUsers([FromBody] List<User> users)
        {
        }
    }
    """

    file_path = tmp_path / "UsersController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "array"
    assert endpoint.request_body.items is not None
    assert endpoint.request_body.items.type == "object"
    assert "Name" in endpoint.request_body.items.properties


def test_nested_generic_types(extractor, tmp_path):
    """Test extraction of nested generic types like Task<ActionResult<List<Item>>>."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;
    using System.Collections.Generic;
    using System.Threading.Tasks;

    public class Item
    {
        public string Title { get; set; }
    }

    [ApiController]
    [Route("api/items")]
    public class ItemsController : ControllerBase
    {
        [HttpGet]
        public Task<ActionResult<List<Item>>> GetItems()
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "ItemsController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    # Should unwrap Task and ActionResult and handle List<Item>
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "array"
    assert endpoint.responses[0].response_schema.items is not None
    assert endpoint.responses[0].response_schema.items.type == "object"
    assert "Title" in endpoint.responses[0].response_schema.items.properties


def test_multiple_dtos_in_file(extractor, tmp_path):
    """Test extraction when multiple DTOs exist in the same file."""
    csharp_code = """
    using Microsoft.AspNetCore.Mvc;

    public class CreateRequest
    {
        public string Name { get; set; }
    }

    public class UpdateRequest
    {
        public string Description { get; set; }
    }

    public class Response
    {
        public int Id { get; set; }
    }

    [ApiController]
    [Route("api/items")]
    public class ItemsController : ControllerBase
    {
        [HttpPost]
        public Response Create([FromBody] CreateRequest request)
        {
            return null;
        }

        [HttpPut("{id}")]
        public Response Update([FromRoute] int id, [FromBody] UpdateRequest request)
        {
            return null;
        }
    }
    """

    file_path = tmp_path / "ItemsController.cs"
    file_path.write_text(csharp_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 2

    # Check POST endpoint
    post_endpoint = next(ep for ep in result.endpoints if ep.method == HTTPMethod.POST)
    assert post_endpoint.request_body is not None
    assert "Name" in post_endpoint.request_body.properties
    assert post_endpoint.responses[0].response_schema is not None
    assert "Id" in post_endpoint.responses[0].response_schema.properties

    # Check PUT endpoint
    put_endpoint = next(ep for ep in result.endpoints if ep.method == HTTPMethod.PUT)
    assert put_endpoint.request_body is not None
    assert "Description" in put_endpoint.request_body.properties
    assert put_endpoint.responses[0].response_schema is not None
    assert "Id" in put_endpoint.responses[0].response_schema.properties


def test_schema_extraction_coverage(extractor):
    """Test schema extraction coverage on real fixture."""
    result = extractor.extract("tests/fixtures/minimal/csharp/aspnet-core")

    assert result.success
    assert len(result.endpoints) >= 6

    # Count endpoints with schemas
    endpoints_with_request_body = sum(1 for ep in result.endpoints if ep.request_body is not None)
    endpoints_with_response_schema = sum(
        1 for ep in result.endpoints
        if ep.responses and ep.responses[0].response_schema is not None
    )

    # POST and PUT endpoints should have request bodies
    post_put_endpoints = sum(
        1 for ep in result.endpoints
        if ep.method in (HTTPMethod.POST, HTTPMethod.PUT)
    )

    # Verify good coverage
    assert endpoints_with_request_body >= 2  # At least POST and PUT
    assert endpoints_with_response_schema >= 4  # Most GET/POST/PUT should have responses

    # All POST/PUT should have request bodies
    assert endpoints_with_request_body == post_put_endpoints
