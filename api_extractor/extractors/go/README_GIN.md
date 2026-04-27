# Gin Framework Extractor

## Overview

The Gin extractor supports the **Gin Web Framework** for Go, one of the most popular Go web frameworks with 55,000+ GitHub stars. It extracts REST API routes from Gin applications using tree-sitter-based AST parsing.

## Supported Features

### ✅ Router Method Detection
- `router.GET()` - GET requests
- `router.POST()` - POST requests
- `router.PUT()` - PUT requests
- `router.DELETE()` - DELETE requests
- `router.PATCH()` - PATCH requests
- `router.HEAD()` - HEAD requests
- `router.OPTIONS()` - OPTIONS requests

### ✅ Path Parameters
Gin uses `:param` syntax for path parameters, which are automatically normalized to OpenAPI `{param}` format:

```go
router.GET("/users/:id", GetUser)        // → /users/{id}
router.GET("/articles/:slug", GetArticle) // → /articles/{slug}
```

### ✅ RouterGroup Path Composition
Supports nested route groups with automatic path composition:

```go
api := router.Group("/api")
api.GET("/users", GetUsers)  // → /api/users
api.GET("/users/:id", GetUser) // → /api/users/{id}
```

### ✅ Handler Function Tracking
Extracts handler function names for operation IDs and documentation:

```go
router.GET("/users", GetUsers)  // Handler: GetUsers
router.POST("/users", CreateUser) // Handler: CreateUser
```

### ✅ Source Location Tracking
Each extracted endpoint includes:
- Source file path (`.go` file)
- Line number where the route is defined

## Detection Methods

The Gin extractor is automatically detected when:

1. **go.mod file** contains `github.com/gin-gonic/gin` dependency
2. **Import statements** in `.go` files reference `github.com/gin-gonic/gin`

## Example Code

### Basic Routes

```go
package main

import "github.com/gin-gonic/gin"

func RegisterRoutes(router *gin.RouterGroup) {
    // Simple routes
    router.GET("/users", GetUsers)
    router.POST("/users", CreateUser)

    // Routes with path parameters
    router.GET("/users/:id", GetUser)
    router.PUT("/users/:id", UpdateUser)
    router.DELETE("/users/:id", DeleteUser)

    // Multiple path parameters
    router.GET("/articles/:slug/comments/:id", GetComment)
}

func GetUsers(c *gin.Context) {
    // Handler implementation
}

func GetUser(c *gin.Context) {
    id := c.Param("id")
    // Handler implementation
}
```

### RouterGroup Composition

```go
package main

import "github.com/gin-gonic/gin"

func SetupAPI(r *gin.Engine) {
    // Create API group with /api prefix
    api := r.Group("/api")

    // Register user routes
    users := api.Group("/users")
    users.GET("", ListUsers)           // → /api/users
    users.GET("/:id", GetUser)        // → /api/users/{id}
    users.POST("", CreateUser)        // → /api/users

    // Register article routes
    articles := api.Group("/articles")
    articles.GET("", ListArticles)    // → /api/articles
    articles.GET("/:slug", GetArticle) // → /api/articles/{slug}
}
```

### RealWorld Example Structure

The Gin RealWorld Conduit app uses domain-driven routing:

```
project/
├── go.mod
├── users/
│   └── routers.go      # User and authentication routes
├── articles/
│   └── routers.go      # Article and comment routes
└── hello.go            # Main application with route mounting
```

## Path Parameter Syntax

Gin's path parameter syntax is **identical to Express.js**:

| Gin Syntax | OpenAPI Format | Description |
|------------|----------------|-------------|
| `/users/:id` | `/users/{id}` | Single parameter |
| `/posts/:slug` | `/posts/{slug}` | Named parameter |
| `/articles/:slug/comments/:id` | `/articles/{slug}/comments/{id}` | Multiple parameters |
| `/users/:userId/posts/:postId` | `/users/{userId}/posts/{postId}` | Multiple parameters |

**Note:** Gin also supports `*param` for wildcard routes, but this is not commonly used in REST APIs and is not supported in v1.

## Limitations (v1)

### ❌ Not Supported

1. **Wildcard Routes** - `router.GET("/static/*filepath", ServeStatic)`
   - Wildcard parameters using `*param` syntax are not extracted
   - Uncommon in REST APIs

2. **Middleware Extraction** - Middleware functions are ignored
   - Only the final handler function is tracked
   - Example: `router.GET("/users", AuthMiddleware, GetUsers)` extracts `GetUsers` only

3. **Function Literal Handlers** - Anonymous functions are marked as `<anonymous>`
   ```go
   router.GET("/users", func(c *gin.Context) {
       // Anonymous handler
   })
   ```

4. **Request/Response Schema Extraction** - Type information is not yet extracted
   - Future enhancement to parse struct types from handler signatures

5. **Query Parameters** - Not extracted from code
   - Only path parameters are detected
   - OpenAPI spec can be manually enhanced

## Testing Instructions

### Unit Tests

Run unit tests for the Gin extractor:

```bash
pytest tests/unit/test_gin_extractor.py -v
```

The test suite includes:
- Basic route extraction
- Path parameter normalization
- RouterGroup path composition
- Multiple HTTP methods
- Edge cases (empty paths, trailing slashes)
- Source tracking verification

### Integration Tests

Run integration tests against the RealWorld Gin app:

```bash
# Clone the RealWorld app (if not already present)
cd tests/fixtures/real-world
git clone https://github.com/gothinkster/golang-gin-realworld-example-app

# Run integration tests
pytest tests/integration/test_realworld_gin.py -v
```

Expected results:
- 25-30 endpoints extracted
- Users, articles, profiles, and tags paths
- GET, POST, PUT, DELETE methods
- Path parameters (`:slug`, `:username`, `:id`)

### Manual Testing

Test the extractor on your own Gin project:

```bash
# Extract routes from a Gin project
api-extractor extract /path/to/gin/project -o openapi.json

# View extracted paths
cat openapi.json | jq '.paths | keys'

# View endpoint details
cat openapi.json | jq '.paths | to_entries[] | {path: .key, methods: .value | keys}'
```

## Implementation Details

### Tree-sitter Queries

The extractor uses tree-sitter-go to parse Go AST and match these patterns:

**Router Method Calls:**
```scheme
(call_expression
  function: (selector_expression
    operand: (identifier) @router_var
    field: (field_identifier) @method_name)
  arguments: (argument_list) @args)
```

**RouterGroup Creation:**
```scheme
(short_var_declaration
  left: (expression_list (identifier) @var_name)
  right: (expression_list
    (call_expression
      function: (selector_expression
        field: (field_identifier) @method_name)
      arguments: (argument_list) @args)))
```

### Code Reusability

The Gin extractor reuses ~70% of the Express.js extractor logic:

| Component | Reusability | Notes |
|-----------|-------------|-------|
| `_extract_path_parameters()` | 100% | Same `:param` regex |
| `_normalize_path()` | 100% | Same regex transformation |
| `_compose_paths()` | 100% | Identical logic |
| `HTTP_METHODS` | 95% | Same methods, different case |
| Router tracking | 80% | Adapted for RouterGroup |
| Route detection | 50% | New Go AST queries |

### Performance Characteristics

- **File parsing:** ~10-50ms per .go file (depends on file size)
- **Query matching:** ~1-5ms per file
- **Memory usage:** Minimal, similar to other extractors
- **Scalability:** Tested on projects with 100+ Go files

## Troubleshooting

### Issue: No routes detected

**Possible causes:**
1. No `go.mod` file or missing Gin dependency
2. Routes defined in files outside scanned directory
3. Non-standard routing patterns (custom router wrappers)

**Solution:**
- Verify `go.mod` contains `github.com/gin-gonic/gin`
- Check that `.go` files are in the scanned directory
- Ensure routes use standard `router.GET/POST/etc.` syntax

### Issue: Routes missing from output

**Possible causes:**
1. Routes defined in excluded directories (`vendor/`, `.git/`)
2. Non-standard method names (custom wrappers)
3. Routes defined dynamically at runtime

**Solution:**
- Check that route files are not in excluded directories
- Use standard Gin method names (`GET`, `POST`, etc.)
- Static analysis can only detect statically defined routes

### Issue: Path parameters not detected

**Possible causes:**
1. Non-standard parameter syntax (e.g., regex patterns)
2. Dynamic path construction

**Solution:**
- Use standard `:param` syntax for path parameters
- Avoid dynamic path generation

## Contributing

To improve the Gin extractor:

1. **Add wildcard route support** - Parse `*filepath` syntax
2. **Extract query parameters** - Parse `c.Query()` calls in handlers
3. **Request/response types** - Extract struct types from handler signatures
4. **Middleware support** - Track middleware chains
5. **Anonymous handlers** - Better detection of inline function handlers

See `api_extractor/extractors/go/gin.py` for the implementation.

## References

- **Gin Framework:** https://gin-gonic.com/
- **Gin GitHub:** https://github.com/gin-gonic/gin
- **Gin RealWorld:** https://github.com/gothinkster/golang-gin-realworld-example-app
- **Tree-sitter Go:** https://github.com/tree-sitter/tree-sitter-go
- **RealWorld Spec:** https://github.com/gothinkster/realworld

## Version History

- **v0.3.0** (Current) - Initial Gin support
  - Router method detection
  - Path parameter normalization
  - RouterGroup composition
  - Handler function tracking
  - Source location tracking
