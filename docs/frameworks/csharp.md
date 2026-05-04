# C# Framework Support

API Extractor supports ASP.NET Core with comprehensive route extraction capabilities for REST APIs.

## Supported Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **ASP.NET Core** | .NET 6+ | `.csproj`, `using` statements | ✅ ASP.NET Core RealWorld |

## Key Features

- `[ApiController]` and `Controller` base class detection
- HTTP method attributes (`[HttpGet]`, `[HttpPost]`, etc.)
- `[Route]` attribute with token replacement (`[controller]`, `[action]`)
- Parameter binding attributes (`[FromRoute]`, `[FromQuery]`, `[FromBody]`)
- Path constraint normalization (`{id:int}` → `{id}`)
- DTO and model extraction

## ASP.NET Core

Modern, cross-platform framework for building web applications and APIs.

### Example

```csharp
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
    public Product Update(
        [FromRoute] int id,
        [FromBody] Product product
    )
    {
        return productService.Update(id, product);
    }

    [HttpDelete("{id}")]
    public void Delete([FromRoute] int id)
    {
        productService.Delete(id);
    }

    [HttpGet("search")]
    public IEnumerable<Product> Search(
        [FromQuery] string query,
        [FromQuery] int? limit
    )
    {
        return productService.Search(query, limit);
    }
}
```

**Detection:** `.csproj` with `Sdk="Microsoft.NET.Sdk.Web"`, `using Microsoft.AspNetCore.Mvc`
**Validated on:** ASP.NET Core RealWorld (23 endpoints across 8 controllers)

## Supported Features

- ✅ `[ApiController]` attribute
- ✅ `Controller` and `ControllerBase` base classes
- ✅ `[Route]` attribute with path patterns
- ✅ Token replacement in routes (`[controller]`, `[action]`)
- ✅ HTTP method attributes: `[HttpGet]`, `[HttpPost]`, `[HttpPut]`, `[HttpDelete]`, `[HttpPatch]`
- ✅ Parameter binding attributes:
  - `[FromRoute]` - Path parameters
  - `[FromQuery]` - Query string parameters
  - `[FromBody]` - Request body
- ✅ Path constraints (`{id:int}`, `{slug:minlength(3)}`) - automatically normalized
- ✅ Multiple route attributes per controller/action
- ✅ C# type mapping to OpenAPI types (int, string, bool, etc.)

## Pattern Support

### Route Attributes

ASP.NET Core supports multiple routing patterns:

```csharp
// Controller-level route with token replacement
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    // Action-level route
    [HttpGet("{id}")]  // Results in: /api/Users/{id}
    public User Get(int id) { }
}

// Controller-level with fixed path
[Route("api/products")]
public class ProductController : ControllerBase
{
    [HttpGet]  // Results in: /api/products
    public List<Product> GetAll() { }
}

// Multiple routes per action
[HttpGet("")]
[HttpGet("all")]
public List<Product> GetAll() { }  // Both /api/products and /api/products/all
```

### Path Parameters

Path parameters use curly brace syntax with optional constraints:

- `{id}` - Simple parameter
- `{id:int}` - Integer constraint (normalized to `{id}`)
- `{slug:minlength(3)}` - String with minimum length (normalized to `{slug}`)
- `{name:alpha}` - Alphabetic constraint (normalized to `{name}`)

### Parameter Binding

```csharp
[HttpGet("{id}")]
public Product Get(
    [FromRoute] int id,                    // Path parameter
    [FromQuery] string include,            // Query parameter
    [FromQuery] bool? detailed = false     // Optional query parameter
)
{
    return productService.Get(id, include, detailed);
}

[HttpPost]
public Product Create([FromBody] CreateProductDto dto)  // Request body
{
    return productService.Create(dto);
}
```

## Usage

### Basic Extraction

```bash
# Detect and extract from ASP.NET Core project
api-extractor extract /path/to/aspnetcore/project
```

### Extract from Solution

```bash
# Extract from .NET solution directory
api-extractor extract /path/to/solution --output aspnet-api.json --verbose
```

### Multiple Projects

```bash
# Extract from specific project folder
api-extractor extract /path/to/solution/MyApi.Web --output api.yaml --format yaml
```

## Generated OpenAPI Spec

For the example controller above, the extractor generates:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Extracted API",
    "version": "1.0.0"
  },
  "paths": {
    "/api/Products": {
      "get": {
        "tags": ["aspnet_core"],
        "operationId": "GetAll",
        "responses": {
          "200": { "description": "Success" }
        }
      },
      "post": {
        "tags": ["aspnet_core"],
        "operationId": "Create",
        "responses": {
          "200": { "description": "Success" }
        }
      }
    },
    "/api/Products/{id}": {
      "get": {
        "tags": ["aspnet_core"],
        "operationId": "GetById",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": { "type": "integer" }
          }
        ],
        "responses": {
          "200": { "description": "Success" }
        }
      },
      "put": { "..." },
      "delete": { "..." }
    },
    "/api/Products/search": {
      "get": {
        "tags": ["aspnet_core"],
        "operationId": "Search",
        "responses": {
          "200": { "description": "Success" }
        }
      }
    }
  }
}
```

## Validation Library Support

API Extractor can extract validation schemas from common C# libraries:

| Framework | Validation Libraries |
|-----------|---------------------|
| ASP.NET Core | Data Annotations, FluentValidation |

### Data Annotations Example

```csharp
public class CreateProductDto
{
    [Required]
    [MaxLength(100)]
    public string Name { get; set; }

    [Range(0, 10000)]
    public decimal Price { get; set; }

    [EmailAddress]
    public string ContactEmail { get; set; }
}
```

## Real-World Validation

Tested against **ASP.NET Core RealWorld** (https://github.com/gothinkster/aspnetcore-realworld-example-app):

- ✅ 23 endpoints successfully extracted
- ✅ `[ApiController]` and `Controller` detection
- ✅ `[Route]` attribute with token replacement
- ✅ HTTP method attributes
- ✅ Parameter binding attributes
- ✅ Path constraint normalization
- ✅ Full RealWorld API specification

### Extracted Endpoints

| HTTP Method | Path | Description |
|-------------|------|-------------|
| POST | `/api/users` | Register user |
| POST | `/api/users/login` | Login user |
| GET | `/api/user` | Get current user |
| PUT | `/api/user` | Update user |
| GET | `/api/profiles/{username}` | Get profile |
| POST | `/api/profiles/{username}/follow` | Follow user |
| DELETE | `/api/profiles/{username}/follow` | Unfollow user |
| GET | `/api/articles` | List articles |
| GET | `/api/articles/feed` | Get feed |
| GET | `/api/articles/{slug}` | Get article |
| POST | `/api/articles` | Create article |
| PUT | `/api/articles/{slug}` | Update article |
| DELETE | `/api/articles/{slug}` | Delete article |
| POST | `/api/articles/{slug}/comments` | Add comment |
| GET | `/api/articles/{slug}/comments` | Get comments |
| DELETE | `/api/articles/{slug}/comments/{id}` | Delete comment |
| POST | `/api/articles/{slug}/favorite` | Favorite article |
| DELETE | `/api/articles/{slug}/favorite` | Unfavorite article |
| GET | `/api/tags` | Get tags |

## Known Limitations

1. **Dynamic routes**: Routes configured in `Startup.cs` or `Program.cs` using `MapControllerRoute()` may not be fully resolved
2. **Minimal APIs**: .NET 6+ minimal API style (`app.MapGet()`) is not currently supported - only MVC/attribute-based controllers
3. **Area routing**: `[Area]` attribute for organizing controllers into areas may not be fully supported

## Troubleshooting

### No endpoints found

- Ensure you're running the extractor on the source directory (`.cs` files), not compiled assemblies (`bin/` or `obj/`)
- Check that the framework is correctly detected with `--verbose` flag
- Verify that controllers use `[ApiController]` attribute or inherit from `ControllerBase`

### Routes missing from output

- Check that controller classes have `[Route]` attribute
- Verify that action methods use HTTP method attributes (`[HttpGet]`, `[HttpPost]`, etc.)
- Ensure `.csproj` is detected as a web project

### Path parameters not extracted

- Check that parameters use `[FromRoute]` or appear in the `[HttpGet("{id}")]` route template
- Verify path syntax uses curly braces: `{id}` not `:id`

## Docker Image Extraction

When extracting from Docker images:

| Status | Notes |
|--------|-------|
| ❌ **Decompilation required** | .dll files → .cs source |

ASP.NET Core applications are compiled to `.dll` files (IL/MSIL bytecode) in Docker images. To extract API definitions:

1. **Extract DLLs** from Docker image
2. **Decompile** using tools like:
   - **ILSpy** - Open-source .NET decompiler (GUI and CLI)
   - **dotPeek** - JetBrains decompiler
   - **dnSpy** - Debugger and decompiler

### Example Decompilation Process

```bash
# Extract DLLs from Docker image
docker cp container-id:/app/MyApi.dll ./

# Decompile with ILSpy CLI
ilspycmd MyApi.dll -o decompiled/

# Run API Extractor on decompiled source
api-extractor extract decompiled/ --output api.json
```

**Note**: Decompiled code preserves attributes and method signatures needed for API extraction.
