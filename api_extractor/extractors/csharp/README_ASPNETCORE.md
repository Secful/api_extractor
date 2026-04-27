# ASP.NET Core REST API Extractor

Extracts REST API routes from ASP.NET Core applications using controller-based routing.

## Supported Features

### Controller Detection

- `[ApiController]` attribute
- `[Controller]` attribute
- Inheritance from `Controller` or `ControllerBase` base classes

### Routing

- `[Route("path")]` attributes on controllers
- Token replacement:
  - `[controller]` → controller name (without "Controller" suffix, camelCase)
  - `[action]` → method name (camelCase)
- Path parameters: `{id}`, `{slug}`, `{username}`
- Path constraints (automatically stripped): `{id:int}` → `{id}`

### HTTP Methods

HTTP method attributes with optional route templates:

- `[HttpGet]` / `[HttpGet("path")]`
- `[HttpPost]` / `[HttpPost("path")]`
- `[HttpPut("{id}")]`
- `[HttpDelete("{id}")]`
- `[HttpPatch]` / `[HttpPatch("path")]`

### Parameter Binding

Automatically detects parameter locations from binding attributes:

- `[FromRoute]` → Path parameter (required)
- `[FromQuery]` → Query parameter
- `[FromBody]` → Request body
- `[FromHeader]` → Header parameter

**Default behavior** (when no attribute specified):
- Complex types (DTOs) → `[FromBody]`
- Simple types → `[FromQuery]`

### Type Mapping

C# types are mapped to OpenAPI types:

| C# Type | OpenAPI Type | Notes |
|---------|--------------|-------|
| `string`, `String` | `string` | |
| `int`, `Int32`, `long`, `Int64` | `integer` | |
| `bool`, `Boolean` | `boolean` | |
| `double`, `float`, `decimal` | `number` | |
| `DateTime`, `DateTimeOffset` | `string` | ISO 8601 format |
| `Guid` | `string` | UUID format |
| `List<T>`, `IEnumerable<T>` | `array` | Generic collections |
| `Dictionary<K,V>` | `object` | Key-value maps |
| `int?`, `bool?` | Same as base | Nullable types |
| `Task<T>`, `ActionResult<T>` | Unwraps to `T` | Async wrappers |

### Schema Extraction

Automatically extracts DTO/model classes:

- Properties with `{ get; set; }` accessors
- Required vs. optional based on nullable reference types (`string?`)
- Nested object types

## Example Usage

### Basic Controller

```csharp
using Microsoft.AspNetCore.Mvc;
using System.Collections.Generic;

namespace MyApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class ProductsController : ControllerBase
    {
        [HttpGet]
        public IEnumerable<Product> GetAll()
        {
            return productService.GetAll();
        }

        [HttpGet("{id}")]
        public Product GetById([FromRoute] int id)
        {
            return productService.GetById(id);
        }

        [HttpPost]
        public Product Create([FromBody] Product product)
        {
            return productService.Create(product);
        }

        [HttpPut("{id}")]
        public Product Update([FromRoute] int id, [FromBody] Product product)
        {
            return productService.Update(id, product);
        }

        [HttpDelete("{id}")]
        public void Delete([FromRoute] int id)
        {
            productService.Delete(id);
        }

        [HttpGet("search")]
        public IEnumerable<Product> Search([FromQuery] string query, [FromQuery] int? limit)
        {
            return productService.Search(query, limit);
        }
    }

    public class Product
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public decimal Price { get; set; }
    }
}
```

**Extracted Routes:**
- `GET /api/products`
- `GET /api/products/{id}`
- `POST /api/products`
- `PUT /api/products/{id}`
- `DELETE /api/products/{id}`
- `GET /api/products/search?query=...&limit=...`

### Token Replacement

```csharp
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    [HttpGet("[action]")]
    public User GetCurrent() { }
}
```

**Result:**
- `[controller]` → `users` (UsersController → users)
- `[action]` → `getCurrent` (GetCurrent → getCurrent)
- Final path: `GET /api/users/getCurrent`

### Path Constraints

```csharp
[HttpGet("{id:int}")]
public Product GetById([FromRoute] int id) { }

[HttpGet("{slug:regex(^[a-z]+$)}")]
public Article GetBySlug([FromRoute] string slug) { }
```

**Normalization:**
- `{id:int}` → `{id}`
- `{slug:regex(...)}` → `{slug}`

Path constraints are stripped for OpenAPI compatibility.

## Detection Methods

The extractor identifies ASP.NET Core projects through:

1. **Project Files (.csproj)**
   - `Sdk="Microsoft.NET.Sdk.Web"`
   - `<PackageReference Include="Microsoft.AspNetCore.Mvc" />`

2. **Using Statements**
   - `using Microsoft.AspNetCore.Mvc;`
   - `using Microsoft.AspNetCore.Builder;`

3. **Controller Patterns**
   - Classes with `[ApiController]` or `[Controller]` attributes
   - Classes inheriting from `Controller` or `ControllerBase`

## Limitations (v1)

### Not Supported

- **Minimal APIs** (`.MapGet()`, `.MapPost()` lambda routing) - Planned for v2
- **Area routing** (`[Area("Admin")]`) - Controllers in areas not supported
- **API versioning** (`[ApiVersion("1.0")]`) - Version attributes ignored
- **Base controller routes** - Inheritance-based routing not fully supported
- **Convention-based routing** (configured in `Program.cs`) - Only attribute routing
- **Action filters** (`[Authorize]`, `[ValidateModel]`) - Not extracted to OpenAPI

### Partial Support

- **Generic return types**: `Task<ActionResult<T>>` unwraps to `T`, but deeply nested generics may fall back to `object`
- **Complex parameter binding**: Custom model binders not detected

## Testing

### Run Unit Tests

```bash
pytest tests/unit/test_aspnet_core_extractor.py -v
```

**Coverage:** 19 tests, 78% code coverage

### Run Integration Tests

```bash
pytest tests/integration/test_realworld_aspnet_core.py -v
```

**Validated on:** ASP.NET Core RealWorld app (15 endpoints, 6 controllers)

### Test Against Your Project

```bash
api-extractor extract /path/to/aspnetcore/project -o openapi.json
cat openapi.json | jq '.paths | keys'
```

## Architecture Notes

### AST Structure

Uses tree-sitter-c-sharp for parsing:

- `class_declaration` → Controller classes
- `attribute_list` → Attributes (`[HttpGet]`, `[Route]`, etc.)
- `method_declaration` → Action methods
- `parameter` → Method parameters with binding attributes
- `base_list` → Base classes (Controller, ControllerBase)

### Comparison to Spring Boot

ASP.NET Core extraction is similar to Spring Boot (Java):
- Both use attribute/annotation-based routing
- Both have parameter location markers
- Both use `{param}` syntax (no normalization needed)
- Type mapping differs (C# vs. Java types)

Key differences:
- C# uses `[HttpGet]` vs. Java's `@GetMapping`
- Token replacement: `[controller]` vs. Spring's convention
- C# has nullable types (`int?`) vs. Java's `@Nullable`

## Troubleshooting

### No routes extracted

**Check:**
1. Controllers have `[ApiController]`, `[Controller]`, or inherit from `Controller`/`ControllerBase`
2. Methods have HTTP method attributes (`[HttpGet]`, `[HttpPost]`, etc.)
3. `.csproj` file includes `Microsoft.AspNetCore.Mvc` or uses `Sdk="Microsoft.NET.Sdk.Web"`

### Wrong paths extracted

**Common issues:**
- Token replacement: `[controller]` should be replaced with lowercase controller name
- Base path missing: Check `[Route]` attribute on controller class
- Path combination: Verify controller route + method route merge correctly

### Parameters not detected

**Check:**
- Use `[FromRoute]`, `[FromQuery]`, `[FromBody]` attributes explicitly
- Default behavior: complex types → body, simple types → query
- Path parameters must be in route template: `[HttpGet("{id}")]`

## Contributing

When adding features to this extractor:

1. Add unit tests in `tests/unit/test_aspnet_core_extractor.py`
2. Update integration tests in `tests/integration/test_realworld_aspnet_core.py`
3. Verify coverage: `pytest --cov=api_extractor.extractors.csharp.aspnet_core`
4. Update this README with new features
5. Add examples to main README.md

## References

- [ASP.NET Core Routing](https://learn.microsoft.com/en-us/aspnet/core/mvc/controllers/routing)
- [ASP.NET Core Model Binding](https://learn.microsoft.com/en-us/aspnet/core/mvc/models/model-binding)
- [tree-sitter-c-sharp](https://github.com/tree-sitter/tree-sitter-c-sharp)
- [RealWorld API Spec](https://github.com/gothinkster/realworld)
