# Go Framework Support

API Extractor supports Gin with comprehensive route extraction capabilities for REST APIs.

## Supported Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **Gin** | 1.x | `go.mod`, imports | ✅ Gin RealWorld |

## Key Features

- Router method detection (`router.GET()`, `router.POST()`, etc.)
- RouterGroup path composition
- Path parameter normalization (`:param` → `{param}`)
- Handler function tracking
- Go module detection

## Gin

Fast HTTP web framework written in Go.

### Example

```go
package main

import "github.com/gin-gonic/gin"

func ArticlesRegister(router *gin.RouterGroup) {
    router.GET("/feed", ArticleFeed)
    router.GET("/:slug", ArticleRetrieve)
    router.POST("", ArticleCreate)
    router.PUT("/:slug", ArticleUpdate)
    router.DELETE("/:slug", ArticleDelete)
}

func ArticleFeed(c *gin.Context) {
    // Handler implementation
}

func ArticleRetrieve(c *gin.Context) {
    slug := c.Param("slug")
    // Handler implementation
}

func ArticleCreate(c *gin.Context) {
    var req CreateArticleRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    // Handler implementation
}
```

**Detection:** `go.mod` dependencies, imports (`github.com/gin-gonic/gin`)
**Validated on:** Gin RealWorld (25-30 endpoints)

## Supported Features

- ✅ Router method calls (`router.GET()`, `router.POST()`, `router.PUT()`, `router.DELETE()`, `router.PATCH()`)
- ✅ RouterGroup for path composition
- ✅ Path parameters (`:param` notation)
- ✅ Path parameter normalization (`:slug` → `{slug}`)
- ✅ Handler function names
- ✅ Middleware detection
- ✅ Group prefixes

## Pattern Support

### Route Definition

Gin supports multiple routing patterns:

```go
func main() {
    router := gin.Default()

    // Simple routes
    router.GET("/ping", func(c *gin.Context) {
        c.JSON(200, gin.H{"message": "pong"})
    })

    // Path parameters
    router.GET("/users/:id", func(c *gin.Context) {
        id := c.Param("id")
        c.JSON(200, gin.H{"id": id})
    })

    // RouterGroup for path composition
    api := router.Group("/api")
    {
        users := api.Group("/users")
        {
            users.GET("", GetUsers)        // /api/users
            users.POST("", CreateUser)     // /api/users
            users.GET("/:id", GetUser)     // /api/users/:id
            users.PUT("/:id", UpdateUser)  // /api/users/:id
        }
    }

    router.Run(":8080")
}
```

### Path Parameters

Gin uses colon notation for path parameters:

- `/users/:id` → `/users/{id}`
- `/articles/:slug/comments/:commentId` → `/articles/{slug}/comments/{commentId}`
- `/files/*filepath` → `/files/{filepath}` (wildcard parameter)

### RouterGroup

RouterGroups allow path composition and middleware sharing:

```go
api := router.Group("/api/v1")
api.Use(AuthMiddleware())  // Middleware for all routes in group
{
    users := api.Group("/users")  // Prefix: /api/v1/users
    {
        users.GET("", ListUsers)       // /api/v1/users
        users.POST("", CreateUser)     // /api/v1/users
        users.GET("/:id", GetUser)     // /api/v1/users/:id
    }

    articles := api.Group("/articles")  // Prefix: /api/v1/articles
    {
        articles.GET("", ListArticles)  // /api/v1/articles
        articles.POST("", CreateArticle)  // /api/v1/articles
    }
}
```

## Usage

### Basic Extraction

```bash
# Detect and extract from Go project
api-extractor extract /path/to/gin/project
```

### Go Module Project

```bash
# Extract from Go module (looks for go.mod)
api-extractor extract /path/to/gin-app --output gin-api.json --verbose
```

### Multiple Packages

```bash
# Extract from specific package
api-extractor extract /path/to/project/cmd/api --output api.yaml --format yaml
```

## Generated OpenAPI Spec

For the example above, the extractor generates:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Extracted API",
    "version": "1.0.0"
  },
  "paths": {
    "/articles/feed": {
      "get": {
        "tags": ["gin"],
        "operationId": "ArticleFeed",
        "responses": {
          "200": { "description": "Success" }
        }
      }
    },
    "/articles/{slug}": {
      "get": {
        "tags": ["gin"],
        "operationId": "ArticleRetrieve",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": { "description": "Success" }
        }
      },
      "put": {
        "tags": ["gin"],
        "operationId": "ArticleUpdate",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": { "description": "Success" }
        }
      },
      "delete": {
        "tags": ["gin"],
        "operationId": "ArticleDelete",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": { "description": "Success" }
        }
      }
    },
    "/articles": {
      "post": {
        "tags": ["gin"],
        "operationId": "ArticleCreate",
        "responses": {
          "200": { "description": "Success" }
        }
      }
    }
  }
}
```

## Validation Library Support

API Extractor can extract validation schemas from common Go libraries:

| Framework | Validation Libraries |
|-----------|---------------------|
| Gin | go-playground/validator, Go Struct Tags |

### Struct Tags Example

```go
type CreateArticleRequest struct {
    Title       string   `json:"title" binding:"required,min=3,max=100"`
    Description string   `json:"description" binding:"required"`
    Body        string   `json:"body" binding:"required"`
    TagList     []string `json:"tagList"`
}

func CreateArticle(c *gin.Context) {
    var req CreateArticleRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    // Handler implementation
}
```

## Real-World Validation

Tested against **Gin RealWorld** (https://github.com/gothinkster/golang-gin-realworld-example-app):

- ✅ 25-30 endpoints successfully extracted
- ✅ Router method detection
- ✅ RouterGroup path composition
- ✅ Path parameter normalization
- ✅ Handler function names
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

1. **Dynamic routes**: Routes defined in loops or loaded from configuration cannot be extracted
2. **Cross-package resolution**: Routes defined across multiple packages may not be fully resolved
3. **Custom router wrappers**: Custom abstraction layers over Gin may not be detected

## Troubleshooting

### No endpoints found

- Ensure you're running the extractor on the source directory (`.go` files), not compiled binaries
- Check that the framework is correctly detected with `--verbose` flag
- Verify that `go.mod` contains `github.com/gin-gonic/gin` dependency

### Routes missing from output

- Check that routes are defined using `router.GET()`, `router.POST()`, etc.
- Verify that RouterGroup setup is in the same file or package
- Ensure handler functions are properly referenced

### Path parameters not extracted

- Check that parameter syntax uses colons: `:id` not `{id}`
- Verify parameter names are valid Go identifiers

## Docker Image Extraction

When extracting from Docker images:

| Status | Notes |
|--------|-------|
| ❌ **Very Difficult** | Compiled to native binary |

Go applications are compiled to native machine code binaries in Docker images. This makes extraction extremely difficult:

- **No source code**: Source files are not included in the image
- **No bytecode**: Unlike Java/C#, Go compiles to native binary (no intermediate representation)
- **Limited decompilers**: Very few Go decompilers exist, with limited functionality
- **Binary analysis**: Requires specialized reverse engineering tools

### Recommendations for Go Projects

If you need to extract API definitions from Go Docker images:

1. **Include source in image** (development only):
   ```dockerfile
   COPY . /app/source
   ```

2. **Generate OpenAPI at build time**:
   ```dockerfile
   RUN api-extractor extract /app/source --output /app/openapi.json
   ```

3. **Use runtime documentation**: Consider libraries like `swag` or `go-swagger` that generate docs at compile time

4. **Keep separate documentation images**: Build a separate image with source code for documentation purposes

**Best practice**: Extract API definitions during CI/CD before building the Docker image, not from the image itself.
