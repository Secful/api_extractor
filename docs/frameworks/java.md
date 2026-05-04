# Java Framework Support

API Extractor supports Spring Boot with comprehensive route extraction capabilities for REST APIs.

## Supported Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **Spring Boot** | 2.x, 3.x | `pom.xml`, `build.gradle`, imports, annotations | ✅ Spring Boot RealWorld |

## Key Features

- `@RestController` and `@Controller` detection
- Mapping annotations (`@GetMapping`, `@PostMapping`, etc.)
- `@RequestMapping` with method arrays
- Path variables and request parameters
- Maven and Gradle project support

## Spring Boot

Enterprise-grade framework for building production-ready Spring applications.

### Basic Controller Example

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

**Detection:** `pom.xml`/`build.gradle` dependencies, imports, `@RestController` annotations
**Validated on:** Spring Boot RealWorld (12 paths, 19 endpoints)

### Supported Features

- ✅ `@RestController` and `@Controller` class annotations
- ✅ Class-level `@RequestMapping` for path prefixes
- ✅ Method-level mappings: `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`
- ✅ `@PathVariable` for path parameters (e.g., `{id}`)
- ✅ `@RequestParam` for query parameters (including `required = false`)
- ✅ `@RequestBody` for request body detection
- ✅ Multiple path parameters per endpoint
- ✅ Java type mapping to OpenAPI types (String, Integer, Long, Boolean, List, etc.)
- ✅ Path constraint normalization (`{id:int}` → `{id}`)
- ✅ DTO and model extraction

### Parameter Annotations

Spring Boot uses annotations to bind request data to method parameters:

```java
@GetMapping("/users/{id}")
public User getUser(
    @PathVariable Long id,                          // Path parameter
    @RequestParam(required = false) String include  // Optional query param
) {
    return userService.findById(id);
}

@PostMapping("/users")
public User createUser(@RequestBody UserCreateDto dto) {  // Request body
    return userService.create(dto);
}
```

## Usage

### Basic Extraction

```bash
# Detect and extract from Spring Boot project
api-extractor extract /path/to/spring-boot/project
```

### Maven Project

```bash
# Extract from Maven project (looks for pom.xml)
api-extractor extract /path/to/maven-project --output spring-api.json
```

### Gradle Project

```bash
# Extract from Gradle project (looks for build.gradle)
api-extractor extract /path/to/gradle-project --output spring-api.yaml --format yaml
```

### Verbose Output

```bash
# Show detailed extraction progress
api-extractor extract /path/to/spring-boot-app --verbose
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
      "put": {
        "tags": ["spring_boot"],
        "operationId": "updateUser",
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
      "delete": {
        "tags": ["spring_boot"],
        "operationId": "deleteUser",
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
      }
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

## Pattern Support

### Path Parameters

Spring Boot uses OpenAPI-compliant path parameters:

- `@GetMapping("/{id}")` → `/api/users/{id}`
- `@GetMapping("/{userId}/posts/{postId}")` → `/api/users/{userId}/posts/{postId}`

Path constraints are automatically normalized:
- `{id:int}` → `{id}`
- `{slug:.*}` → `{slug}`

### Request Mapping

Multiple ways to define routes:

```java
// Method-specific annotations (preferred)
@GetMapping("/users")
@PostMapping("/users")
@PutMapping("/users/{id}")
@DeleteMapping("/users/{id}")
@PatchMapping("/users/{id}")

// Generic RequestMapping with method array
@RequestMapping(value = "/users", method = {RequestMethod.GET, RequestMethod.POST})

// Class-level prefix
@RequestMapping("/api")
public class UserController {
    @GetMapping("/users")  // Results in /api/users
}
```

## Validation Library Support

API Extractor can extract validation schemas from common Java libraries:

| Framework | Validation Libraries |
|-----------|---------------------|
| Spring Boot | Hibernate Validator (JSR-380), Jackson Annotations |

## Real-World Validation

Tested against **Spring Boot RealWorld** (https://github.com/gothinkster/spring-boot-realworld-example-app):

- ✅ 19 endpoints successfully extracted
- ✅ `@RestController` and `@Controller` detection
- ✅ Class-level `@RequestMapping` path prefixes
- ✅ Method-level mappings (`@GetMapping`, `@PostMapping`, etc.)
- ✅ Path variables with `@PathVariable` (single and multiple)
- ✅ Query parameters with `@RequestParam` (required and optional)
- ✅ Request body handling with `@RequestBody`
- ✅ Full RealWorld API specification (users, articles, profiles, comments, favorites, tags)

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

1. **Dynamic routes**: Routes defined programmatically (e.g., using custom route builders) cannot be extracted
2. **WebFlux**: Functional routing with `RouterFunction` is not currently supported (only annotation-based controllers)
3. **Complex path patterns**: Regex-based path matchers are not fully supported

## Troubleshooting

### No endpoints found

- Ensure you're running the extractor on the source directory (`src/main/java/`), not compiled classes (`target/` or `build/`)
- Check that the framework is correctly detected with `--verbose` flag
- Verify that controllers use `@RestController` or `@Controller` annotations

### Routes missing from output

- Check that controller classes are annotated with `@RestController` or `@Controller`
- Verify that methods use mapping annotations (`@GetMapping`, `@PostMapping`, etc.)
- Ensure class-level `@RequestMapping` is properly formatted

### Path parameters not extracted

- Check that parameters use `@PathVariable` annotation
- Verify path syntax uses curly braces: `/{id}` not `/:id`

## Docker Image Extraction

When extracting from Docker images:

| Status | Notes |
|--------|-------|
| ❌ **Decompilation required** | .class files → .java source |

Spring Boot applications are compiled to `.class` files (bytecode) in Docker images. To extract API definitions:

1. **Extract JAR/WAR** from Docker image
2. **Decompile** using tools like:
   - **JD-CLI** - Command-line Java decompiler
   - **fernflower** - IntelliJ IDEA's decompiler
   - **Procyon** - Modern Java decompiler

### Example Decompilation Process

```bash
# Extract JAR from Docker image
docker cp container-id:/app/application.jar ./

# Extract JAR contents
unzip application.jar -d extracted/

# Decompile with fernflower
java -jar fernflower.jar extracted/BOOT-INF/classes/ decompiled/

# Run API Extractor on decompiled source
api-extractor extract decompiled/ --output api.json
```

**Note**: Decompiled code may have formatting differences and missing comments, but API annotations are preserved.
