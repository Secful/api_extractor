# API Extractor

Automatically extract REST API definitions from source code and generate OpenAPI specifications.

## Features

- **Automatic Framework Detection**: Detects web frameworks in your codebase
- **Multi-Language Support**: Supports Python (FastAPI, Flask, Django REST), JavaScript/TypeScript (Express, NestJS, Fastify, Next.js), Java (Spring Boot), C# (ASP.NET Core), and Go (Gin)
- **OpenAPI 3.1 Output**: Generates standard OpenAPI specifications in JSON or YAML
- **Tree-sitter Based**: Uses Tree-sitter Query Language for accurate AST parsing and pattern matching
- **Production Validated**: Tested against real-world projects including Cal.com (Next.js), Dub (Next.js), Spring Boot RealWorld, ASP.NET Core RealWorld, Gin RealWorld, truthy (NestJS), and Postman tutorial patterns
- **Comprehensive Coverage**: Extracts paths, methods, parameters, request bodies, and type information

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

API Extractor can be used in two modes:
1. **CLI Mode** - Command-line tool for batch extraction
2. **HTTP Server Mode** - HTTP API for on-demand analysis

### CLI Mode

#### Basic Usage

Extract API definitions from a local directory:

```bash
api-extractor extract /path/to/project
```

### Specify Output Format

Generate YAML output:

```bash
api-extractor extract /path/to/project --output api-spec.yaml --format yaml
```

### Verbose Output

Show detailed extraction progress:

```bash
api-extractor extract /path/to/project --verbose
```

### Framework-Specific Examples

Extract from a Go Gin project:

```bash
api-extractor extract /path/to/gin/project -o openapi.json
```

Extract from a Next.js project:

```bash
api-extractor extract /path/to/nextjs/project -o openapi.yaml --format yaml
```

## CLI Reference

### Command: `extract`

Extract API routes from source code and generate OpenAPI specification.

```bash
api-extractor extract <PATH> [OPTIONS]
```

### Arguments

- `PATH` - Path to local codebase directory

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | path | `openapi.json` | Output file path |
| `--format` | `-f` | choice | `json` | Output format (`json` or `yaml`) |
| `--verbose` | `-v` | flag | false | Show detailed extraction progress |
| `--title` | - | string | `Extracted API` | API title in OpenAPI spec |
| `--version` | - | string | `1.0.0` | API version in OpenAPI spec |
| `--help` | `-h` | flag | - | Show help message |

## Supported Frameworks

API Extractor supports **10 major web frameworks** across 5 languages, automatically detected via dependency files, imports, and code patterns.

## Docker Image Extraction Requirements

When extracting API definitions from Docker images, different languages require different preprocessing steps:

| Language | Frameworks | Preprocessing Required | Tools/Notes |
|----------|-----------|------------------------|-------------|
| **Python** | FastAPI, Flask, Django REST | ✅ None | Python source files (.py) are deployed as-is in Docker images |
| **JavaScript/TypeScript** | Express, NestJS, Fastify, Next.js | ⚠️ Varies | **Development images**: Source available as-is<br>**Production images**: May be transpiled/minified - source maps needed for TS, Next.js apps may be optimized/bundled |
| **Java** | Spring Boot | ❌ Decompilation | .class files → .java source<br>Extract JAR/WAR first, then decompile with JD-CLI, fernflower, or Procyon |
| **C#** | ASP.NET Core | ❌ Decompilation | .dll files → .cs source<br>Decompile IL/MSIL using ILSpy, dotPeek, or dnSpy |
| **Go** | Gin | ❌ Very Difficult | Compiled to native binary - specialized Go decompilers required (limited availability)<br>Source code typically not in image |

**Legend:**
- ✅ **None** - Extract and analyze source files directly
- ⚠️ **Varies** - Depends on build configuration (development vs production)
- ❌ **Decompilation** - Requires decompiling bytecode/binaries back to source

### Python Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **FastAPI** | All versions | `requirements.txt`, `pyproject.toml`, imports | ✅ FastAPI Full-Stack Template |
| **Flask** | All versions | `requirements.txt`, `pyproject.toml`, imports | ✅ Flask RealWorld (DataDog) |
| **Django REST Framework** | 3.x+ | `requirements.txt`, `pyproject.toml`, imports | ✅ Django REST Tutorial |

**Key Features:**
- Route decorator detection (`@app.route`, `@router.get`, `@api_view`)
- Blueprint and APIRouter support
- ViewSet and generic views (Django REST)
- Path parameters and query parameters
- Request/response type hints (FastAPI, Flask-RESTX)

### JavaScript/TypeScript Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **Express** | 4.x+ | `package.json`, imports | ✅ Express Examples |
| **NestJS** | 8.x+ | `package.json`, `@nestjs/*` imports | ✅ NestJS RealWorld |
| **Fastify** | 3.x+ | `package.json`, imports | ✅ Fastify Demo |
| **Next.js** | 13.x+ | `package.json`, directory structure, imports | ✅ Cal.com, Dub |

**Key Features:**
- Router and controller detection
- Decorator-based routing (NestJS: `@Get()`, `@Post()`)
- File-system routing (Next.js)
- Dynamic routes and path parameters
- Middleware and plugin patterns
- TypeScript type extraction

### Java Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **Spring Boot** | 2.x, 3.x | `pom.xml`, `build.gradle`, imports, annotations | ✅ Spring Boot RealWorld |

**Key Features:**
- `@RestController` and `@Controller` detection
- Mapping annotations (`@GetMapping`, `@PostMapping`, etc.)
- `@RequestMapping` with method arrays
- Path variables and request parameters

### C# Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **ASP.NET Core** | .NET 6+ | `.csproj`, `using` statements | ✅ ASP.NET Core RealWorld |

**Key Features:**
- `[ApiController]` and `Controller` base class detection
- HTTP method attributes (`[HttpGet]`, `[HttpPost]`, etc.)
- `[Route]` attribute with token replacement (`[controller]`, `[action]`)
- Parameter binding attributes (`[FromRoute]`, `[FromQuery]`, `[FromBody]`)
- Path constraint normalization (`{id:int}` → `{id}`)
- DTO and model extraction
- Maven and Gradle project support

### Go Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **Gin** | 1.x | `go.mod`, imports | ✅ Gin RealWorld |

**Key Features:**
- Router method detection (`router.GET()`, `router.POST()`, etc.)
- RouterGroup path composition
- Path parameter normalization (`:param` → `{param}`)
- Handler function tracking
- Go module detection

### Framework-Specific Details

#### Next.js (App Router & Pages Router)

Next.js is a full-stack React framework with API Routes support. The extractor handles both routing patterns:

**App Router** (Next.js 13+):
```typescript
// app/api/users/route.ts
export async function GET() {
  return Response.json({ users: [] })
}

export async function POST(request: Request) {
  const body = await request.json()
  return Response.json({ user: body })
}

// app/api/users/[id]/route.ts → /api/users/:id
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  return Response.json({ user: { id } })
}
```

**Pages Router** (Legacy):
```typescript
// pages/api/users.ts
export default function handler(req, res) {
  if (req.method === 'GET') {
    res.status(200).json({ users: [] })
  }
  if (req.method === 'POST') {
    res.status(201).json({ user: req.body })
  }
}

// pages/api/users/[id].ts → /api/users/:id
export default function handler(req, res) {
  const { id } = req.query
  res.status(200).json({ user: { id } })
}
```

**Detection:** Package dependency, directory structure (`app/api/`, `pages/api/`), or imports
**Validated on:** Cal.com (11 endpoints), Dub (31 endpoints)

#### Spring Boot

Supports both Maven and Gradle projects with annotation-based routing:

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping
    public List<User> getUsers() {
        return userService.findAll();
    }

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }
}
```

**Detection:** `pom.xml`/`build.gradle` dependencies, imports, `@RestController` annotations
**Validated on:** Spring Boot RealWorld (12 paths, 19 endpoints)

#### Gin (Go)

Supports Gin web framework with function-based routing:

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
```

**Detection:** `go.mod` dependencies, imports (`github.com/gin-gonic/gin`)
**Validated on:** Gin RealWorld (25-30 endpoints)

#### ASP.NET Core

Supports .NET 6+ with attribute-based routing:

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
}
```

**Detection:** `.csproj` with `Sdk="Microsoft.NET.Sdk.Web"`, `using Microsoft.AspNetCore.Mvc`
**Validated on:** ASP.NET Core RealWorld (23 endpoints across 8 controllers)

#### NestJS

TypeScript framework with decorator-based routing:

```typescript
@Controller('users')
export class UsersController {
  @Get()
  findAll(): Promise<User[]> {
    return this.usersService.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string): Promise<User> {
    return this.usersService.findOne(id);
  }

  @Post()
  create(@Body() user: CreateUserDto): Promise<User> {
    return this.usersService.create(user);
  }
}
```

**Detection:** `@nestjs/*` packages in `package.json`
**Validated on:** NestJS RealWorld

#### FastAPI

Python framework with type hints and automatic OpenAPI generation:

```python
from fastapi import FastAPI, APIRouter

router = APIRouter(prefix="/api/users")

@router.get("/")
async def get_users() -> List[User]:
    return await user_service.find_all()

@router.get("/{user_id}")
async def get_user(user_id: int) -> User:
    return await user_service.find_one(user_id)

@router.post("/")
async def create_user(user: UserCreate) -> User:
    return await user_service.create(user)
```

**Detection:** `fastapi` in requirements/pyproject.toml
**Validated on:** FastAPI Full-Stack Template

### Exit Codes

- `0` - Success
- `1` - Framework detection failed (no frameworks found)
- `2` - Invalid input (path not found, invalid arguments, etc.)
- `3` - Extraction error (parse failures, no endpoints found, etc.)

### Examples

#### Basic Usage

**Automatic framework detection:**
```bash
api-extractor extract /path/to/project
```

**Custom output with metadata:**
```bash
api-extractor extract . \
  --output my-api.yaml \
  --format yaml \
  --title "My API" \
  --version "2.0.0" \
  --verbose
```

#### Framework-Specific Examples

**Next.js (App Router or Pages Router):**
```bash
api-extractor extract /path/to/nextjs-app --output nextjs-api.json
# Detects: app/api/ or pages/api/ directories
# Output: OpenAPI spec with all API routes
```

**Spring Boot (Maven or Gradle):**
```bash
api-extractor extract /path/to/spring-boot-app --output spring-api.yaml --format yaml
# Detects: pom.xml, build.gradle, @RestController annotations
# Output: OpenAPI spec with all REST endpoints
```

**FastAPI:**
```bash
api-extractor extract /path/to/fastapi-app --output fastapi-spec.json
# Detects: FastAPI decorators and type hints
# Output: OpenAPI spec with request/response schemas
```

**Express/NestJS/Fastify:**
```bash
api-extractor extract /path/to/node-app --output api.json
# Detects: package.json dependencies and routing patterns
# Output: OpenAPI spec with all routes
```

**Flask/Django REST:**
```bash
api-extractor extract /path/to/python-app --output api.json
# Detects: requirements.txt, route decorators, ViewSets
# Output: OpenAPI spec with all endpoints
```

### Environment Variables

None currently supported for CLI mode. All configuration is via CLI arguments.

---

## HTTP Server Mode (Sidecar Deployment)

API Extractor can run as an HTTP server, exposing REST API endpoints for on-demand code analysis. This mode is designed for **sidecar deployment** in containerized environments, where API Extractor runs alongside your application to provide real-time API documentation and analysis capabilities.

### Use Cases

- **Runtime API Discovery**: Automatically discover and document APIs running in your cluster
- **CI/CD Integration**: Extract API specs during build/deploy pipelines
- **API Gateway Integration**: Provide OpenAPI specs to API gateways for routing and validation
- **Documentation Automation**: Generate up-to-date API documentation on every deployment
- **Service Mesh Integration**: Supply API metadata to service mesh control planes
- **Contract Testing**: Generate API contracts for consumer-driven contract testing
- **Web-based UIs**: Power interactive API exploration dashboards

### Starting the Server

```bash
api-extractor serve
```

The server will start on `http://0.0.0.0:8000` by default.

**Custom host and port:**
```bash
api-extractor serve --host 127.0.0.1 --port 9000
```

**Development mode with auto-reload:**
```bash
api-extractor serve --reload --log-level debug
```

### Sidecar Deployment Pattern

The most common deployment pattern for API Extractor is as a **sidecar container** that runs alongside your application in a Kubernetes pod or Docker Compose stack. This allows other services to discover and document your API at runtime without modifying your application code.

**Benefits of Sidecar Deployment:**

1. **Zero Application Changes**: No instrumentation or code changes required in your application
2. **Real-Time Analysis**: Generate OpenAPI specs on-demand when services start or change
3. **Multi-Language Support**: Works with any supported framework across Python, JavaScript/TypeScript, Java, C#, Go
4. **Shared Volume Access**: Sidecar reads application code from a shared volume
5. **Network Isolation**: API Extractor is accessible only within the pod/stack (not exposed externally)
6. **Independent Scaling**: Can be scaled independently of the application

**Architecture:**

```
┌────────────────────────────────────────────────────────────┐
│  Kubernetes Pod / Docker Compose Stack                     │
│                                                             │
│  ┌─────────────────┐       ┌─────────────────────────┐   │
│  │  Application    │       │  API Extractor          │   │
│  │  Container      │       │  (Sidecar)              │   │
│  │                 │       │                         │   │
│  │  :8080 (app)    │       │  :8000 (analysis API)   │   │
│  │                 │       │                         │   │
│  └────────┬────────┘       └──────────┬──────────────┘   │
│           │                           │                   │
│           └──────┬────────────────────┘                   │
│                  │                                         │
│         ┌────────▼────────┐                               │
│         │ Shared Volume   │                               │
│         │ /app/code       │                               │
│         │ (Application    │                               │
│         │  Source Code)   │                               │
│         └─────────────────┘                               │
└────────────────────────────────────────────────────────────┘
                      │
                      │ External Request
                      ▼
            Other services call
            http://pod-ip:8000/api/v1/analyze
            to get OpenAPI spec
```

**Example: Docker Compose Sidecar Setup**

```yaml
version: '3.8'

services:
  # Your application
  app:
    image: my-app:latest
    ports:
      - "8080:8080"
    volumes:
      - ./app-code:/app/code:ro
    networks:
      - app-network

  # API Extractor sidecar
  api-extractor:
    image: api-extractor:latest
    ports:
      - "8000:8000"
    volumes:
      - ./app-code:/app/code:ro
    environment:
      - API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code
      - API_EXTRACTOR_LOG_LEVEL=info
    networks:
      - app-network
    depends_on:
      - app

  # Example: API Gateway that uses the OpenAPI spec
  api-gateway:
    image: kong:latest
    ports:
      - "8001:8001"
    environment:
      - GATEWAY_API_SPEC_URL=http://api-extractor:8000/api/v1/analyze
    networks:
      - app-network
    depends_on:
      - api-extractor

networks:
  app-network:
    driver: bridge
```

**Access the API Extractor from other services:**

```bash
# From another container in the same network
curl -X POST http://api-extractor:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/app/code"}'

# From the host machine
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/app/code"}'
```

### API Endpoints

#### Health Check
**GET** `/api/v1/health`

Check if the service is healthy and responsive.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

#### Service Information
**GET** `/api/v1/info`

Get information about service capabilities and supported frameworks.

**Response:**
```json
{
  "version": "0.1.0",
  "supported_frameworks": ["fastapi", "flask", "django_rest", "express", "nestjs", "fastify", "spring_boot"],
  "features": {
    "auto_detection": true,
    "multiple_frameworks": true
  }
}
```

#### Analyze Codebase - Core Endpoint
**POST** `/api/v1/analyze`

The primary endpoint for extracting REST API definitions from source code and generating OpenAPI specifications. This endpoint performs automatic framework detection, AST parsing, route extraction, and OpenAPI spec generation in a single request.

**Key Features:**
- **Automatic Framework Detection**: Detects Python (FastAPI, Flask, Django REST), JavaScript/TypeScript (Express, NestJS, Fastify, Next.js), Java (Spring Boot), C# (ASP.NET Core), and Go (Gin)
- **Multi-Framework Support**: Handles codebases with multiple frameworks
- **OpenAPI 3.1 Output**: Returns standard-compliant OpenAPI specifications
- **Local Sources**: Analyzes code from local filesystem
- **Rich Metadata**: Provides extraction statistics, detected frameworks, warnings, and errors
- **Path Security**: Validates paths to prevent directory traversal and unauthorized access

**Request Body:**
```json
{
  "path": "/app/code",
  "title": "My API",
  "version": "1.0.0",
  "description": "My REST API Documentation"
}
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | - | Path to local codebase directory |
| `title` | string | No | `"Extracted API"` | API title that appears in the OpenAPI `info.title` field |
| `version` | string | No | `"1.0.0"` | API version that appears in the OpenAPI `info.version` field |
| `description` | string | No | `null` | API description that appears in the OpenAPI `info.description` field |

**Success Response (200 OK):**
```json
{
  "success": true,
  "openapi_spec": {
    "openapi": "3.1.0",
    "info": {
      "title": "My API",
      "version": "1.0.0",
      "description": "My REST API Documentation"
    },
    "paths": {
      "/api/users": {
        "get": {
          "tags": ["fastapi"],
          "operationId": "get_users",
          "responses": {
            "200": {"description": "Success"}
          }
        }
      },
      "/api/users/{user_id}": {
        "get": {
          "tags": ["fastapi"],
          "operationId": "get_user",
          "parameters": [
            {
              "name": "user_id",
              "in": "path",
              "required": true,
              "schema": {"type": "integer"}
            }
          ],
          "responses": {
            "200": {"description": "Success"}
          }
        }
      }
    }
  },
  "endpoints_count": 5,
  "frameworks_detected": ["fastapi"],
  "errors": [],
  "warnings": ["No type hints found for parameter 'query' in function 'search_users'"],
  "metadata": {
    "source_path": "/app/code",
    "frameworks_used": ["fastapi"],
    "total_files_scanned": 12,
    "extraction_time_ms": 234
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether extraction completed successfully (true even if no endpoints found) |
| `openapi_spec` | object \| null | Complete OpenAPI 3.1.0 specification, or `null` if extraction failed |
| `endpoints_count` | integer | Total number of API endpoints discovered |
| `frameworks_detected` | array[string] | List of detected frameworks (e.g., `["fastapi", "flask"]`) |
| `errors` | array[string] | Critical errors that prevented extraction |
| `warnings` | array[string] | Non-critical issues (missing types, ambiguous routes, etc.) |
| `metadata` | object | Additional extraction metadata (source path, frameworks used, statistics) |

**Error Responses:**

| Status Code | Description | Example |
|-------------|-------------|---------|
| **400 Bad Request** | Invalid request parameters | Path is empty or invalid |
| **403 Forbidden** | Path security violation | Path contains `..`, targets system directories, or violates whitelist |
| **404 Not Found** | Path does not exist (local only) | Directory not found at specified path |
| **422 Validation Error** | Request schema validation failed | Missing required field, wrong type |
| **500 Internal Server Error** | Unexpected server error | Parser crash, unexpected exception |

**Example Error Response (403 Forbidden):**
```json
{
  "detail": "Access denied: path '/etc/passwd' is forbidden"
}
```

**Sidecar Deployment Example:**

In a Kubernetes sidecar deployment, the API Extractor container runs alongside your application container and analyzes the application's source code:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      # Main application container
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: app-code
          mountPath: /app/code
          readOnly: true

      # API Extractor sidecar
      - name: api-extractor
        image: api-extractor:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_EXTRACTOR_ALLOWED_PATH_PREFIXES
          value: "/app/code"
        volumeMounts:
        - name: app-code
          mountPath: /app/code
          readOnly: true

      volumes:
      - name: app-code
        emptyDir: {}
```

**Analyze the application from another service:**
```bash
curl -X POST http://my-app:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/app/code",
    "title": "My App API",
    "version": "1.0.0"
  }'
```

### API Documentation

Interactive API documentation is automatically generated and available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Example Usage

**Using curl:**
```bash
# Analyze local codebase
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/code"
  }'

# Health check
curl http://localhost:8000/api/v1/health
```

**Using Python requests:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/analyze",
    json={
        "path": "/path/to/code",
        "title": "My API",
        "version": "1.0.0"
    }
)

result = response.json()
if result["success"]:
    print(f"Found {result['endpoints_count']} endpoints")
    print(result["openapi_spec"])
```

### Real-World Integration Examples

#### Example 1: API Gateway Auto-Configuration

Use API Extractor in a sidecar to automatically configure an API gateway on application startup:

```python
# api-gateway-config.py - Runs in init container or startup script
import requests
import json

# Get OpenAPI spec from API Extractor sidecar
response = requests.post(
    "http://api-extractor:8000/api/v1/analyze",
    json={
        "path": "/app/code",
        "title": "User Service API",
        "version": "1.0.0"
    }
)

spec = response.json()

if spec["success"]:
    # Configure API Gateway with the OpenAPI spec
    # Example: Kong, AWS API Gateway, or any gateway that accepts OpenAPI
    gateway_response = requests.post(
        "http://api-gateway:8001/services",
        json={
            "name": "user-service",
            "openapi_spec": spec["openapi_spec"]
        }
    )

    print(f"✓ Configured gateway with {spec['endpoints_count']} endpoints")
    print(f"✓ Frameworks detected: {spec['frameworks_detected']}")
else:
    print(f"✗ Extraction failed: {spec['errors']}")
    exit(1)
```

#### Example 2: Service Mesh Registration

Register service endpoints with a service mesh control plane:

```python
# service-mesh-register.py
import requests
import yaml

# Extract OpenAPI spec
response = requests.post(
    "http://api-extractor:8000/api/v1/analyze",
    json={"path": "/app/code"}
)

spec = response.json()

if spec["success"]:
    openapi = spec["openapi_spec"]

    # Register each endpoint with the service mesh
    for path, methods in openapi["paths"].items():
        for method, details in methods.items():
            route_config = {
                "service": "user-service",
                "path": path,
                "method": method.upper(),
                "tags": details.get("tags", [])
            }

            requests.post(
                "http://service-mesh-control-plane:9090/routes",
                json=route_config
            )

    print(f"✓ Registered {spec['endpoints_count']} routes with service mesh")
```

#### Example 3: Continuous Documentation Updates

Automatically update API documentation in a docs site on every deployment:

```bash
#!/bin/bash
# update-docs.sh - Runs in CI/CD pipeline or as Kubernetes Job

# Start API Extractor sidecar (already running in K8s sidecar pattern)
API_EXTRACTOR_URL="http://localhost:8000"

# Extract OpenAPI spec
OPENAPI_SPEC=$(curl -s -X POST "$API_EXTRACTOR_URL/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/app/code",
    "title": "'"$SERVICE_NAME"' API",
    "version": "'"$APP_VERSION"'"
  }' | jq -r '.openapi_spec')

# Generate documentation using tools like redoc-cli or swagger-ui
echo "$OPENAPI_SPEC" > /docs/openapi.json

# Upload to documentation site
npx @redocly/cli build-docs /docs/openapi.json -o /docs/index.html
aws s3 cp /docs/index.html s3://docs-bucket/services/$SERVICE_NAME/

echo "✓ Documentation updated at https://docs.example.com/services/$SERVICE_NAME/"
```

#### Example 4: Contract Testing

Use extracted OpenAPI specs for consumer-driven contract testing:

```python
# contract-test.py - Runs in test suite
import requests
import pact

# Extract OpenAPI spec from the service
response = requests.post(
    "http://api-extractor:8000/api/v1/analyze",
    json={"path": "/app/code"}
)

openapi_spec = response.json()["openapi_spec"]

# Use the spec to generate Pact contracts
pact_broker = pact.Broker("http://pact-broker:9292")

# Publish the OpenAPI spec as a contract
pact_broker.publish(
    consumer="frontend-app",
    provider="user-service",
    openapi_spec=openapi_spec,
    version="1.0.0"
)

# Run contract tests
verifier = pact.Verifier(provider="user-service")
verifier.verify_with_broker(
    broker_url="http://pact-broker:9292",
    openapi_spec=openapi_spec
)

print("✓ Contract tests passed")
```

#### Example 5: Kubernetes Init Container Pattern

Extract OpenAPI spec in an init container before the main application starts:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  template:
    spec:
      # Init container extracts OpenAPI spec and stores it
      initContainers:
      - name: extract-api-spec
        image: api-extractor:latest
        command:
        - sh
        - -c
        - |
          # Run API Extractor as a CLI tool
          api-extractor extract /app/code \
            --output /specs/openapi.json \
            --title "User Service API" \
            --version "$APP_VERSION"

          # Validate the spec was created
          if [ ! -f /specs/openapi.json ]; then
            echo "Failed to extract OpenAPI spec"
            exit 1
          fi

          echo "OpenAPI spec extracted successfully"
        volumeMounts:
        - name: app-code
          mountPath: /app/code
          readOnly: true
        - name: api-specs
          mountPath: /specs

      # Main application container
      containers:
      - name: app
        image: user-service:latest
        volumeMounts:
        - name: app-code
          mountPath: /app/code
          readOnly: true
        - name: api-specs
          mountPath: /specs
          readOnly: true
        env:
        - name: OPENAPI_SPEC_PATH
          value: /specs/openapi.json

      volumes:
      - name: app-code
        emptyDir: {}
      - name: api-specs
        emptyDir: {}
```

### Server Configuration

Configuration can be set via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_EXTRACTOR_HOST` | `0.0.0.0` | Server host |
| `API_EXTRACTOR_PORT` | `8000` | Server port |
| `API_EXTRACTOR_LOG_LEVEL` | `info` | Logging level |
| `API_EXTRACTOR_ALLOWED_PATH_PREFIXES` | (empty) | Comma-separated whitelist of allowed path prefixes |

**Example with environment variables:**
```bash
export API_EXTRACTOR_HOST=127.0.0.1
export API_EXTRACTOR_PORT=9000
export API_EXTRACTOR_LOG_LEVEL=debug
export API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code,/tmp
api-extractor serve
```

### Security

The HTTP server includes several security features:

1. **Path Traversal Prevention** - Blocks paths containing `..` or `~`
2. **System Directory Protection** - Forbidden: `/etc`, `/usr`, `/bin`, `/sbin`, `/root`, `/boot`, `/sys`, `/proc`, `/dev`
3. **Path Whitelist** - Optional whitelist of allowed path prefixes via `API_EXTRACTOR_ALLOWED_PATH_PREFIXES`

**Example security configuration:**
```bash
# Only allow analysis of code in /app/code and /tmp
export API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code,/tmp
api-extractor serve
```

### Docker Deployment

#### Using Docker

**Build the image:**
```bash
docker build -t api-extractor .
```

**Run the container:**
```bash
docker run -d \
  -p 8000:8000 \
  -v /path/to/code:/app/code:ro \
  -e API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code \
  --name api-extractor \
  api-extractor
```

**Test the container:**
```bash
curl http://localhost:8000/api/v1/health
```

#### Using Docker Compose

**docker-compose.yml** is included in the repository.

**Start the service:**
```bash
# Place code to analyze in ./code-to-analyze directory
mkdir -p code-to-analyze
cp -r /path/to/your/code code-to-analyze/

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

**Analyze code in container:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/app/code"
  }'
```

#### Docker Configuration

The Docker image includes:
- Python 3.11 slim base image
- Health check configured (checks `/api/v1/health` every 30s)
- Volume mount at `/app/code` for analyzed code
- Security whitelist set to `/app/code` and `/tmp`
- CORS enabled for web UIs

**Environment variables in Docker:**
```yaml
environment:
  - API_EXTRACTOR_HOST=0.0.0.0
  - API_EXTRACTOR_PORT=8000
  - API_EXTRACTOR_LOG_LEVEL=info
  - API_EXTRACTOR_ALLOWED_PATH_PREFIXES=/app/code,/tmp
```

### Kubernetes Deployment

**Example deployment manifest:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-extractor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-extractor
  template:
    metadata:
      labels:
        app: api-extractor
    spec:
      containers:
      - name: api-extractor
        image: api-extractor:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_EXTRACTOR_ALLOWED_PATH_PREFIXES
          value: "/app/code"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: code-volume
          mountPath: /app/code
          readOnly: true
      volumes:
      - name: code-volume
        persistentVolumeClaim:
          claimName: code-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: api-extractor
spec:
  selector:
    app: api-extractor
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## AWS Lambda Deployment

API Extractor can be deployed as an AWS Lambda function with **Function URL** for HTTP access. This serverless deployment pattern is ideal for on-demand API extraction without managing servers.

### Architecture Overview

The Lambda deployment uses three key AWS services:

1. **Lambda Function** - Runs the API extraction code in a serverless environment
2. **Function URL** - Provides an HTTPS endpoint with IAM authentication
3. **S3 Files** - Mounts an S3 bucket as a filesystem at `/mnt/s3` for reading source code

```
┌─────────────────────────────────────────────────────────────────┐
│  AWS Lambda Function (ARM64 Graviton)                           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Lambda Handler (handler.py)                           │    │
│  │  - Receives HTTP request via Function URL              │    │
│  │  - Reads code from S3 Files mount: /mnt/s3/lambda/    │    │
│  │  - Runs api_extractor service                          │    │
│  │  - Returns OpenAPI spec as JSON                        │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │                                            │
│                     ▼                                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  S3 Files Filesystem Mount: /mnt/s3/                   │    │
│  │  └── lambda/                                           │    │
│  │      ├── my-fastapi-app/    (source code)             │    │
│  │      ├── my-flask-app/      (source code)             │    │
│  │      └── my-spring-app/     (source code)             │    │
│  └──────────────────┬─────────────────────────────────────┘    │
│                     │                                            │
└─────────────────────┼────────────────────────────────────────────┘
                      │
                      │ Backed by S3 Bucket
                      ▼
           ┌─────────────────────────┐
           │  S3 Bucket              │
           │  my-code-repositories   │
           │                         │
           │  s3://bucket/lambda/    │
           │    ├── my-fastapi-app/  │
           │    ├── my-flask-app/    │
           │    └── my-spring-app/   │
           └─────────────────────────┘
```

**Request Flow:**

1. Client sends HTTP POST to Function URL with AWS IAM signatures
2. Lambda receives request via Function URL (API Gateway is not used)
3. Handler reads `folder` parameter from request body
4. Handler accesses `/mnt/s3/lambda/{folder}` via S3 Files mount
5. Extraction service analyzes code and generates OpenAPI spec
6. Lambda returns OpenAPI spec in HTTP response

### Key Features

#### Function URL

AWS Lambda Function URLs provide **built-in HTTPS endpoints** without needing API Gateway:

- **Direct HTTP Access**: Each Lambda function gets a unique HTTPS URL
- **IAM Authentication**: Secured with AWS signature v4 (AWS_IAM auth type)
- **Low Latency**: Direct invocation without API Gateway overhead
- **No Additional Cost**: Included with Lambda pricing, no API Gateway charges
- **CORS Support**: Configurable cross-origin access for web clients

**URL Format:**
```
https://{url-id}.lambda-url.{region}.on.aws/
```

**Authentication:**
- All requests must be signed with AWS credentials (AWS Signature Version 4)
- Use AWS SDKs, AWS CLI, or `awscurl` to sign requests automatically
- IAM policies control which users/roles can invoke the function

#### S3 Files (S3 as Filesystem)

**S3 Files** is an AWS service that mounts S3 buckets as POSIX filesystems in Lambda:

- **Standard File APIs**: Access S3 objects using `open()`, `Path()`, and other filesystem operations
- **No Downloads**: No need to download code from S3 before processing - read directly from mount
- **Automatic Caching**: S3 Files caches frequently accessed files for better performance
- **Cost Efficient**: Only pay for data transfer and API calls, no storage duplication
- **Large Files**: Supports files up to 5 TB in S3
- **VPC Required**: S3 Files requires Lambda to run in a VPC with private subnets

**How it works:**

1. S3 bucket `my-code-repositories` contains project folders in `lambda/` prefix
2. S3 Files mounts the bucket at `/mnt/s3` inside the Lambda execution environment
3. Lambda reads code using standard filesystem operations: `/mnt/s3/lambda/my-project/`
4. No explicit S3 API calls needed in the Lambda handler code

**Benefits over direct S3 access:**
- Simpler code - use `Path()` instead of `boto3.client('s3')`
- Better performance - automatic caching and prefetching
- Works with existing file-based tools without modification

#### VPC Configuration

Lambda runs in a **VPC with private subnets** to access S3 Files:

- **Private Subnets**: Lambda runs in subnets without internet access
- **NAT Gateway**: Not required for S3 Files access (uses VPC endpoints)
- **Security Groups**: Control network access to/from Lambda
- **S3 VPC Endpoint**: Direct S3 access without internet gateway

### Deployment Setup

All Lambda-related files are in `api_extractor/lambda/`:

```
api_extractor/lambda/
├── handler.py              # Lambda entry point
├── requirements.txt        # Lambda dependencies
├── config.sh              # AWS configuration
├── build_lambda.sh        # Build ARM64 package
├── deploy_lambda.sh       # Deploy to AWS
├── setup_vpc.sh           # Create VPC
├── setup_s3_files.sh      # Create S3 Files filesystem
├── attach_s3_files.sh     # Attach filesystem to Lambda
├── create_function_url.sh # Create Function URL
├── cleanup.sh             # Delete Lambda function
└── QUICK_START.md         # Quick reference guide
```

### Prerequisites

1. **AWS CLI** configured with credentials:
   ```bash
   aws configure
   ```

2. **Docker** for building ARM64 package:
   ```bash
   docker --version
   ```

3. **IAM Permissions** to create:
   - Lambda functions
   - IAM roles
   - VPC resources
   - S3 buckets
   - S3 Files filesystems

### Quick Start

#### 1. Configure Deployment

Edit `api_extractor/lambda/config.sh`:

```bash
# Lambda Configuration
export FUNCTION_NAME=api-extractor
export AWS_REGION=eu-north-1

# S3 Configuration
export S3_BUCKET_NAME=my-code-repositories

# Lambda Settings
export LAMBDA_TIMEOUT=300    # seconds (5 minutes)
export LAMBDA_MEMORY=1024    # MB
```

#### 2. Create VPC

Set up VPC with private subnets for S3 Files:

```bash
cd api_extractor/lambda
./setup_vpc.sh
```

This creates:
- VPC with CIDR 10.0.0.0/16
- 2 private subnets in different availability zones
- Security group allowing outbound HTTPS
- VPC endpoint for S3 access

The script updates `config.sh` with VPC IDs automatically.

#### 3. Create S3 Bucket and Upload Code

```bash
# Create S3 bucket (if needed)
aws s3 mb s3://my-code-repositories

# Upload project code to S3 under lambda/ prefix
aws s3 cp --recursive ./my-fastapi-app s3://my-code-repositories/lambda/my-fastapi-app/
aws s3 cp --recursive ./my-flask-app s3://my-code-repositories/lambda/my-flask-app/

# Verify upload
aws s3 ls s3://my-code-repositories/lambda/
```

**Important**: All projects must be uploaded under the `lambda/` prefix in S3. The Lambda handler expects paths like `/mnt/s3/lambda/{folder}/`.

#### 4. Setup S3 Files Filesystem

Create S3 Files filesystem and mount configuration:

```bash
./setup_s3_files.sh
```

This creates:
- S3 Files filesystem
- IAM role with S3 and S3 Files permissions
- Access point linked to S3 bucket

The script updates `config.sh` with filesystem IDs automatically.

#### 5. Build and Deploy Lambda

```bash
# Build ARM64 package with Docker
./build_lambda.sh

# Deploy to AWS
./deploy_lambda.sh
```

The build process:
- Uses Docker with `public.ecr.aws/lambda/python:3.11-arm64` image
- Installs dependencies for ARM64 architecture (Graviton processors)
- Packages `api_extractor` module and `handler.py`
- Creates `lambda-function.zip` (typically 15-20 MB)

The deploy process:
- Creates IAM role with Lambda, VPC, S3, and S3 Files permissions
- Creates or updates Lambda function
- Configures VPC networking
- Sets environment variables

#### 6. Attach S3 Files to Lambda

Mount the S3 Files filesystem at `/mnt/s3`:

```bash
./attach_s3_files.sh
```

This:
- Creates EFS File System Configuration linking S3 Files access point
- Mounts filesystem at `/mnt/s3` in Lambda environment
- Updates Lambda function configuration

**Important**: Lambda must be deployed before attaching S3 Files.

#### 7. Create Function URL

Enable HTTP access with IAM authentication:

```bash
./create_function_url.sh
```

This creates a Function URL with:
- Auth Type: `AWS_IAM` (requires signed requests)
- CORS: Enabled for cross-origin access

The script outputs the Function URL:
```
Function URL: https://abc123xyz.lambda-url.eu-north-1.on.aws/
```

**Save this URL** - you'll need it to invoke the Lambda function.

### Usage

#### Request Format

Send a POST request with JSON body:

```json
{
  "folder": "my-fastapi-app",
  "title": "My FastAPI Application",
  "version": "2.0.0",
  "description": "Production API for FastAPI app"
}
```

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `folder` | string | Yes | - | Folder name under `/mnt/s3/lambda/` to analyze |
| `title` | string | No | `"Extracted API"` | OpenAPI spec title |
| `version` | string | No | `"1.0.0"` | API version |
| `description` | string | No | `null` | API description |

**Important**: The `folder` parameter should match the folder name in S3:
- S3 path: `s3://my-code-repositories/lambda/my-fastapi-app/`
- Request: `{"folder": "my-fastapi-app"}`
- Lambda reads: `/mnt/s3/lambda/my-fastapi-app/`

#### Using awscurl (Recommended)

Install `awscurl` for automatic AWS signature signing:

```bash
pip install awscurl
```

Make a request:

```bash
# Get Function URL
FUNCTION_URL=$(aws lambda get-function-url-config \
  --function-name api-extractor \
  --query 'FunctionUrl' \
  --output text)

# Extract API from folder
awscurl --service lambda --region eu-north-1 -X POST \
  -H "Content-Type: application/json" \
  -d '{"folder": "my-fastapi-app"}' \
  "$FUNCTION_URL"
```

Full example with all parameters:

```bash
awscurl --service lambda --region eu-north-1 -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "folder": "my-spring-boot-app",
    "title": "Spring Boot RealWorld API",
    "version": "1.0.0",
    "description": "RealWorld backend implementation"
  }' \
  "$FUNCTION_URL"
```

#### Using AWS CLI

Invoke Lambda directly (response is Base64-encoded):

```bash
aws lambda invoke \
  --function-name api-extractor \
  --payload '{"folder": "my-fastapi-app"}' \
  response.json

# View response
cat response.json
```

#### Using Python boto3

```python
import boto3
import json

client = boto3.client('lambda', region_name='eu-north-1')

response = client.invoke(
    FunctionName='api-extractor',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'folder': 'my-fastapi-app',
        'title': 'My API',
        'version': '1.0.0'
    })
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

#### Using Python requests with AWS Signature

```python
import requests
from aws_requests_auth.aws_auth import AWSRequestsAuth
import json

# Get credentials from environment or ~/.aws/credentials
auth = AWSRequestsAuth(
    aws_access_key='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    aws_host='abc123xyz.lambda-url.eu-north-1.on.aws',
    aws_region='eu-north-1',
    aws_service='lambda'
)

response = requests.post(
    'https://abc123xyz.lambda-url.eu-north-1.on.aws/',
    auth=auth,
    json={'folder': 'my-fastapi-app'}
)

openapi_spec = response.json()
print(json.dumps(openapi_spec, indent=2))
```

### Response Format

#### Success Response (200)

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "X-Endpoints-Count": "15",
    "X-Frameworks": "fastapi"
  },
  "body": "{\"openapi\":\"3.1.0\",\"info\":{\"title\":\"My API\",\"version\":\"1.0.0\"},...}"
}
```

The `body` field contains a JSON-serialized OpenAPI 3.1.0 specification.

#### Error Responses

**404 - Folder Not Found:**
```json
{
  "statusCode": 404,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"error\": \"Folder not found: my-project\"}"
}
```

**400 - Invalid Request:**
```json
{
  "statusCode": 400,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"error\": \"Missing required field: 'folder'\"}"
}
```

**500 - S3 Files Not Mounted:**
```json
{
  "statusCode": 500,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"error\": \"S3 filesystem not mounted at /mnt/s3\"}"
}
```

**422 - Extraction Failed:**
```json
{
  "statusCode": 422,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"error\": \"Extraction failed\", \"errors\": [...], \"warnings\": [...]}"
}
```

### Monitoring and Logs

#### View Logs

**Real-time logs:**
```bash
aws logs tail /aws/lambda/api-extractor --follow
```

**Recent logs:**
```bash
# Last 10 minutes
aws logs tail /aws/lambda/api-extractor --since 10m

# Last hour
aws logs tail /aws/lambda/api-extractor --since 1h
```

**Filter logs:**
```bash
# Show errors only
aws logs tail /aws/lambda/api-extractor --filter-pattern "ERROR"

# Show specific folder extractions
aws logs tail /aws/lambda/api-extractor --filter-pattern "my-fastapi-app"
```

#### CloudWatch Metrics

View Lambda metrics in CloudWatch console:
- Invocations
- Duration
- Errors
- Throttles
- Concurrent executions

### Configuration

#### Environment Variables

Set in Lambda function configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_MOUNT_PATH` | `/mnt/s3` | S3 Files mount point |

Update environment variables:

```bash
aws lambda update-function-configuration \
  --function-name api-extractor \
  --environment Variables="{S3_MOUNT_PATH=/mnt/s3}"
```

#### Lambda Settings

Update timeout (default 300 seconds):

```bash
aws lambda update-function-configuration \
  --function-name api-extractor \
  --timeout 600
```

Update memory (default 1024 MB):

```bash
aws lambda update-function-configuration \
  --function-name api-extractor \
  --memory-size 2048
```

#### IAM Permissions

The Lambda function needs permissions for:

1. **Lambda Execution**:
   - `AWSLambdaBasicExecutionRole` - CloudWatch Logs
   - `AWSLambdaVPCAccessExecutionRole` - VPC networking

2. **S3 Access**:
   - `s3:GetObject` - Read objects from S3 bucket
   - `s3:ListBucket` - List bucket contents

3. **S3 Files Access**:
   - `s3files:DescribeFileSystem` - Access filesystem metadata
   - `s3files:DescribeAccessPoint` - Access mount point

The `deploy_lambda.sh` script creates these permissions automatically.

### Updating the Lambda Function

#### Update Code Only

```bash
# Rebuild and redeploy
cd api_extractor/lambda
./build_lambda.sh
./deploy_lambda.sh
```

#### Update Code in S3

```bash
# Upload updated project code
aws s3 sync ./my-fastapi-app s3://my-code-repositories/lambda/my-fastapi-app/

# S3 Files will automatically reflect changes
# No Lambda restart needed
```

#### Update Configuration

```bash
# Edit config
nano config.sh

# Redeploy
./deploy_lambda.sh
```

### Testing

#### Test Locally

Run Lambda handler locally (requires uploaded code in S3):

```bash
cd api_extractor/lambda
python test_lambda_local.py
```

#### Test Remote Lambda

```bash
# Test with default folder
./test_lambda_remote.sh

# Test specific folder
./test_lambda_remote.sh my-spring-boot-app
```

### Cleanup

#### Delete Lambda Function Only

```bash
cd api_extractor/lambda
./cleanup.sh
```

This removes:
- Lambda function
- Lambda IAM role
- Function URL

Keeps:
- VPC and subnets
- S3 bucket and contents
- S3 Files filesystem

#### Full Cleanup

```bash
# Delete Lambda
./cleanup.sh

# Delete S3 Files
aws s3files delete-file-system --file-system-id $FILE_SYSTEM_ID
aws iam delete-role --role-name api-extractor-s3files-role

# Delete VPC
./cleanup_vpc.sh

# Delete S3 bucket (WARNING: deletes all code)
aws s3 rb s3://my-code-repositories --force
```

### Troubleshooting

#### S3 filesystem not mounted

**Error:**
```json
{"error": "S3 filesystem not mounted at /mnt/s3"}
```

**Solution:**
```bash
cd api_extractor/lambda
./attach_s3_files.sh
```

Verify mount:
```bash
aws lambda get-function-configuration \
  --function-name api-extractor \
  --query 'FileSystemConfigs'
```

#### Folder not found

**Error:**
```json
{"error": "Folder not found: my-project"}
```

**Solution:**

Check S3 bucket structure:
```bash
aws s3 ls s3://my-code-repositories/lambda/
```

Ensure folder exists under `lambda/` prefix:
```bash
aws s3 cp --recursive ./my-project s3://my-code-repositories/lambda/my-project/
```

#### Task timed out after 300 seconds

**Error:**
```
Task timed out after 300.00 seconds
```

**Solution:**

Increase timeout:
```bash
# Edit config.sh
export LAMBDA_TIMEOUT=600

# Redeploy
./deploy_lambda.sh
```

Or update directly:
```bash
aws lambda update-function-configuration \
  --function-name api-extractor \
  --timeout 600
```

#### Permission denied errors

**Error:**
```
Access Denied (Service: S3Files)
```

**Solution:**

Check IAM role permissions:
```bash
aws iam list-attached-role-policies \
  --role-name api-extractor-role
```

Re-run setup to fix permissions:
```bash
./setup_s3_files.sh
./deploy_lambda.sh
```

#### VPC connectivity issues

**Error:**
```
Task timed out (no logs)
```

**Solution:**

Verify VPC configuration:
```bash
aws lambda get-function-configuration \
  --function-name api-extractor \
  --query 'VpcConfig'
```

Check security group allows outbound HTTPS:
```bash
aws ec2 describe-security-groups \
  --group-ids $SECURITY_GROUP_ID
```

### Cost Estimation

AWS Lambda pricing (as of 2024):

| Component | Cost | Notes |
|-----------|------|-------|
| **Lambda Requests** | $0.20 per 1M requests | First 1M free per month |
| **Lambda Compute** | $0.0000133334 per GB-second (ARM64) | First 400,000 GB-seconds free per month |
| **S3 Storage** | $0.023 per GB/month | Standard storage |
| **S3 Files** | $0.08 per GB transferred | Data transfer from S3 to Lambda |
| **VPC** | Free | No NAT Gateway needed |

**Example calculation** (1024 MB, 30-second execution):

- 1000 requests/month: $0.20
- Compute (1024 MB × 30s × 1000): $0.41
- S3 storage (10 GB): $0.23
- S3 Files transfer (100 MB per request × 1000): $8.00

**Total: ~$8.84/month** for 1000 requests

**Free Tier:**
- First 1M requests free
- First 400,000 GB-seconds free (~13,000 requests at 1024 MB × 30s)

### Advantages of Lambda Deployment

1. **Serverless** - No server management, automatic scaling
2. **Cost-Efficient** - Pay only for actual execution time
3. **Low Latency** - Function URL provides direct HTTP access
4. **S3 Integration** - S3 Files mounts buckets as filesystem
5. **Secure** - IAM authentication, VPC isolation
6. **ARM64** - Graviton processors for better price/performance

### Limitations

1. **Cold Starts** - First request after idle period is slower (3-5 seconds)
2. **Timeout** - Maximum 15 minutes execution time
3. **Memory** - Maximum 10 GB memory
4. **VPC Required** - S3 Files requires VPC configuration
5. **Large Projects** - Very large codebases may exceed timeout

For production workloads with consistent traffic, consider the **HTTP Server Mode** with Docker/Kubernetes instead.

---

## Supported Frameworks

### Python
- ✅ **FastAPI**: Route decorators (`@app.get`, `@router.post`), APIRouter, path parameters, type hints
- ✅ **Flask**: Blueprints, `@app.route()`, method-specific decorators (`@app.get`), path converters (`<int:id>`)
- ✅ **Django REST Framework**: ViewSets, APIView, `@api_view` decorator, URL patterns

### JavaScript/TypeScript
- ✅ **Express**: Router mounting (`app.use()`), middleware chains, path parameters (`:param`), route methods
- ✅ **NestJS**: Controllers (`@Controller()`), HTTP decorators (`@Get()`, `@Post()`), multiple decorators, path composition, versioning
- ✅ **Fastify**: Route registration (`fastify.get()`), path parameters (`:param`), schema validation

### Java
- ✅ **Spring Boot**: REST controllers (`@RestController`, `@Controller`), request mappings (`@GetMapping`, `@PostMapping`, `@RequestMapping`), path variables (`{param}`), request parameters, request body

## Pattern Support

### Path Parameters
All frameworks support extracting path parameters and normalizing them to OpenAPI format:
- **Express/NestJS/Fastify**: `/users/:id` → `/users/{id}`
- **Flask**: `/users/<int:id>` → `/users/{id}`
- **FastAPI**: `/users/{user_id}` → `/users/{user_id}`
- **Spring Boot**: `/users/{id}` → `/users/{id}` (already OpenAPI-compliant)

### Router/Blueprint Mounting
- **Express**: `app.use('/api', router)` - Correctly applies prefix to all routes
- **Flask**: `Blueprint('api', __name__, url_prefix='/api')` - Tracks blueprint prefixes
- **FastAPI**: `app.include_router(router, prefix='/api')` - Handles router inclusion
- **NestJS**: `@Controller('users')` - Path composition with controller decorators
- **Spring Boot**: `@RequestMapping('/api')` - Class-level path prefixes combined with method-level mappings

### Middleware & Guards
- **Express**: Detects middleware in route chains (e.g., `app.get('/path', auth, handler)`)
- **NestJS**: Recognizes guards (`@UseGuards()`) and other decorators without treating them as routes

### Parameter Annotations
- **Spring Boot**: Extracts `@PathVariable`, `@RequestParam` (with `required = false` support), and `@RequestBody`

## Known Limitations

1. **Cross-file module resolution**: Extractors work best with single-file or same-directory patterns. Express routers defined in separate files and imported via `require()` may not have their mount paths correctly applied.

2. **Dynamic routes**: Routes defined programmatically (e.g., generated in loops, loaded from config) cannot be extracted.

3. **Type inference**: For untyped JavaScript code, parameter types default to `string`.

4. **Complex path patterns**: Regex-based routes or custom path matchers are not supported.

## Example

Given a FastAPI application:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id}
```

Running the extractor:

```bash
api-extractor extract . --verbose
```

Output:

```
Detecting frameworks...
  ✓ Found: fastapi
Extracting routes...
  fastapi: 1 endpoints found
Generating OpenAPI spec...
✓ Written to openapi.json
```

Generated OpenAPI spec (openapi.json):

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Extracted API",
    "version": "1.0.0"
  },
  "paths": {
    "/users/{user_id}": {
      "get": {
        "tags": ["fastapi"],
        "parameters": [
          {
            "name": "user_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "integer"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  }
}
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Running Tests with Coverage

```bash
pytest tests/ -v --cov=api_extractor --cov-report=term-missing
```

### Test Statistics

- **Total Tests**: 161 (158 passing, 3 known issues)
- **Coverage**: 82% overall
  - Spring Boot extractor: 96%
  - Framework extractors: 85-96%
  - Core parser: 66%
  - Base extractor: 85%

### Test Breakdown by Framework

| Framework | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Spring Boot | 10 | 96% | ✅ Passing |
| Flask | 5 | 94% | ✅ Passing |
| NestJS | 5 | 94% | ✅ Passing |
| Express | 18 | 86% | ✅ Passing |
| Fastify | 4 | 89% | ✅ Passing |
| Django REST | 4 | 89% | ✅ Passing |
| FastAPI | 4 | 86% | ✅ Passing |

## Validation

The extractors have been validated against real-world codebases:

### Express Validation
Tested against patterns from **Postman's "How to Create a REST API with Node.js and Express" tutorial**:
- ✅ Basic CRUD operations
- ✅ Router mounting with `app.use()`
- ✅ Multiple routers with different prefixes
- ✅ Middleware in routes
- ✅ Nested path parameters
- ✅ API versioning patterns
- ✅ REST API best practices
- ✅ Complex path patterns

### NestJS Validation
Tested against **truthy** (https://github.com/gobeam/truthy), a production NestJS application:
- ✅ 39 endpoints successfully extracted
- ✅ Controller path prefixes
- ✅ HTTP method decorators with and without paths
- ✅ Multiple decorators per method (`@Get()` + `@ApiQuery()`)
- ✅ Path parameter extraction and normalization
- ✅ Guard and interceptor decorators (correctly ignored)
- ✅ Class-level decorators

### Spring Boot Validation
Tested against **RealWorld** (https://github.com/gothinkster/spring-boot-realworld-example-app), a production Spring Boot application:
- ✅ 19 endpoints successfully extracted
- ✅ `@RestController` and `@Controller` detection
- ✅ Class-level `@RequestMapping` path prefixes
- ✅ Method-level mappings (`@GetMapping`, `@PostMapping`, etc.)
- ✅ Path variables with `@PathVariable` (single and multiple)
- ✅ Query parameters with `@RequestParam` (required and optional)
- ✅ Request body handling with `@RequestBody`
- ✅ Full RealWorld API specification (users, articles, profiles, comments, favorites, tags)

## Architecture

### Project Structure

```
api_extractor/
├── core/
│   ├── models.py           # Data models
│   ├── detector.py         # Framework detection
│   ├── parser.py           # Tree-sitter wrapper
│   └── base_extractor.py  # Base extractor class
├── extractors/
│   ├── python/
│   │   ├── fastapi.py     # FastAPI extractor
│   │   ├── flask.py       # Flask extractor
│   │   └── django_rest.py # Django REST extractor
│   ├── javascript/
│   │   ├── express.py     # Express extractor
│   │   ├── nestjs.py      # NestJS extractor
│   │   └── fastify.py     # Fastify extractor
│   └── java/
│       └── spring_boot.py # Spring Boot extractor
├── input_handlers/
│   └── local.py           # Local filesystem handler
├── openapi/
│   ├── models.py          # OpenAPI models
│   └── builder.py         # OpenAPI spec builder
├── service/
│   ├── extractor_service.py  # Core extraction service
│   └── models.py          # Service result models
├── server/
│   ├── app.py             # FastAPI application
│   ├── config.py          # Server configuration
│   ├── security.py        # Security validation
│   └── api/
│       ├── routes.py      # HTTP endpoints
│       └── schemas.py     # Request/response schemas
└── cli.py                 # CLI interface (extract + serve)
```

### Architecture Layers

The application uses a **3-tier architecture**:

1. **Interface Layer** (CLI + HTTP)
   - CLI commands (`extract`, `serve`)
   - FastAPI HTTP endpoints (`/api/v1/analyze`, `/api/v1/health`, `/api/v1/info`)
   - Handles user input, validation, and output formatting

2. **Service Layer**
   - `ExtractionService` - Core extraction logic
   - Framework-agnostic extraction workflow
   - Result aggregation and error handling
   - Shared by both CLI and HTTP interfaces

3. **Extraction Layer**
   - Framework-specific extractors
   - Tree-sitter AST parsing
   - Route detection and normalization
   - OpenAPI spec generation

### Implementation Approach

All extractors use **Tree-sitter Query Language** for pattern matching:

1. **Parse source code into AST**: Tree-sitter parses Python, JavaScript, and TypeScript files into abstract syntax trees

2. **Query for patterns**: Framework-specific queries written in S-expression syntax match route definitions
   ```scheme
   ; Example: Flask route decorator
   (decorated_definition
     (decorator
       (call
         function: (attribute
           object: (identifier) @obj_name
           attribute: (identifier) @method_name)
         arguments: (argument_list) @args))
     definition: (function_definition
       name: (identifier) @func_name))
   ```

3. **Extract route information**: Captured nodes are processed to extract:
   - HTTP methods (GET, POST, etc.)
   - Path patterns with parameters
   - Handler function names
   - Path prefixes from routers/blueprints/controllers

4. **Normalize to OpenAPI**: Routes are normalized to OpenAPI 3.1 format with proper parameter schemas

This declarative approach replaced 1,050+ lines of imperative tree traversal code, improving maintainability and accuracy.

## Contributing

Contributions are welcome! To add support for a new framework:

1. **Create a new extractor** in `api_extractor/extractors/python/` or `api_extractor/extractors/javascript/`
2. **Extend `BaseExtractor`** and implement required methods:
   - `get_file_extensions()` - Return list of file extensions to process
   - `extract_routes_from_file()` - Use Tree-sitter queries to extract routes
   - `_extract_path_parameters()` - Parse path parameters
   - `_normalize_path()` - Convert to OpenAPI format
3. **Write Tree-sitter queries** to match framework-specific patterns:
   - Study the framework's AST structure using Tree-sitter playground
   - Write S-expression queries to capture route decorators/functions
   - Extract HTTP methods, paths, and parameters from captured nodes
4. **Add test fixtures** in `tests/fixtures/` with sample code
5. **Create unit tests** in `tests/unit/` covering:
   - Basic route extraction
   - Path parameter handling
   - Router/Blueprint mounting
   - Edge cases (empty decorators, multiple decorators, etc.)
6. **Validate against real projects** to ensure production readiness
7. **Update CLI** in `cli.py` to register the new extractor

### Example: Adding a New Framework

See existing extractors like `express.py`, `nestjs.py`, or `spring_boot.py` for reference implementation using Tree-sitter Query Language.

## Spring Boot Example

### Basic Controller

Given a Spring Boot controller:

```java
package com.example.api;

import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping
    public List<User> getAllUsers() {
        return userService.findAll();
    }

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping
    public User createUser(@RequestBody CreateUserRequest request) {
        return userService.create(request);
    }

    @PutMapping("/{id}")
    public User updateUser(
        @PathVariable Long id,
        @RequestBody CreateUserRequest request
    ) {
        return userService.update(id, request);
    }

    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
    }

    @GetMapping("/search")
    public List<User> searchUsers(
        @RequestParam String query,
        @RequestParam(required = false) Integer limit
    ) {
        return userService.search(query, limit);
    }
}
```

### Extraction

Running:
```bash
api-extractor extract ./src --verbose
```

Output:
```
Detecting frameworks...
  ✓ Found: spring_boot
Extracting routes...
  spring_boot: 6 endpoints found
Generating OpenAPI spec...
✓ Written to openapi.json
```

### Generated OpenAPI Spec

The extractor generates a complete OpenAPI 3.1.0 specification:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Extracted API",
    "version": "1.0.0"
  },
  "paths": {
    "/api/users": {
      "get": {
        "tags": ["spring_boot"],
        "operationId": "getAllUsers",
        "responses": {
          "200": { "description": "Success" }
        }
      },
      "post": {
        "tags": ["spring_boot"],
        "operationId": "createUser",
        "responses": {
          "200": { "description": "Success" }
        }
      }
    },
    "/api/users/{id}": {
      "get": {
        "tags": ["spring_boot"],
        "operationId": "getUser",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": { "description": "Success" }
        }
      },
      "put": { /* ... */ },
      "delete": { /* ... */ }
    },
    "/api/users/search": {
      "get": {
        "tags": ["spring_boot"],
        "operationId": "searchUsers",
        "responses": {
          "200": { "description": "Success" }
        }
      }
    }
  }
}
```

### Supported Spring Boot Features

The Spring Boot extractor handles:
- ✅ `@RestController` and `@Controller` class annotations
- ✅ Class-level `@RequestMapping` for path prefixes
- ✅ Method-level mappings: `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`
- ✅ `@PathVariable` for path parameters (e.g., `{id}`)
- ✅ `@RequestParam` for query parameters (including `required = false`)
- ✅ `@RequestBody` for request body detection
- ✅ Multiple path parameters per endpoint
- ✅ Java type mapping to OpenAPI types (String, Integer, Long, Boolean, List, etc.)

## Troubleshooting

### No endpoints found
- Ensure you're running the extractor on the correct directory (source code, not build artifacts)
- Check that the framework is correctly detected with `--verbose` flag

### Routes missing from output
- For Express: Ensure routers are defined and mounted in the same file
- For Flask: Check that Blueprint mounting (`app.register_blueprint()`) is present
- For NestJS: Verify controllers are decorated with `@Controller()` and methods with HTTP decorators

### Path parameters not extracted
- Check that parameter syntax matches the framework:
  - Express/NestJS/Fastify: `:paramName`
  - Flask: `<type:paramName>` or `<paramName>`
  - FastAPI: `{paramName}`

### Performance issues
- The extractor processes all matching files in the directory
- For large codebases, consider extracting from specific subdirectories
- Use `.gitignore` patterns are not currently supported - manually exclude `node_modules`, `venv`, etc.

## License

MIT License
