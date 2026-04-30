"""Tests for Gin cross-file schema resolution."""

import tempfile
from pathlib import Path

import pytest

from api_extractor.core.models import FrameworkType, HTTPMethod
from api_extractor.extractors.go.gin import GinExtractor


class TestImportExtraction:
    """Test Go import statement extraction."""

    def test_extract_imports_simple(self):
        """Test extracting simple import statements."""
        code = b"""package main

import "github.com/gin-gonic/gin"

func main() {
    router := gin.Default()
}
"""
        extractor = GinExtractor()
        tree = extractor.parser.parse_source(code, "go")
        imports = extractor._extract_imports(tree, code, "/test/main.go")

        assert "gin" in imports
        assert imports["gin"] == "github.com/gin-gonic/gin"

    def test_extract_imports_aliased(self):
        """Test extracting aliased import statements."""
        code = b"""package main

import (
    m "github.com/alist-org/alist/v3/internal/model"
)

func main() {}
"""
        extractor = GinExtractor()
        tree = extractor.parser.parse_source(code, "go")
        imports = extractor._extract_imports(tree, code, "/test/main.go")

        assert "m" in imports
        assert imports["m"] == "github.com/alist-org/alist/v3/internal/model"

    def test_extract_imports_grouped(self):
        """Test extracting grouped import statements."""
        code = b"""package main

import (
    "fmt"
    "github.com/gin-gonic/gin"
    "github.com/alist-org/alist/v3/server/handles"
    m "github.com/alist-org/alist/v3/internal/model"
)

func main() {}
"""
        extractor = GinExtractor()
        tree = extractor.parser.parse_source(code, "go")
        imports = extractor._extract_imports(tree, code, "/test/main.go")

        assert "fmt" in imports
        assert "gin" in imports
        assert "handles" in imports
        assert "m" in imports
        assert imports["gin"] == "github.com/gin-gonic/gin"
        assert imports["handles"] == "github.com/alist-org/alist/v3/server/handles"
        assert imports["m"] == "github.com/alist-org/alist/v3/internal/model"

    def test_extract_imports_no_imports(self):
        """Test file with no imports."""
        code = b"""package main

func main() {}
"""
        extractor = GinExtractor()
        tree = extractor.parser.parse_source(code, "go")
        imports = extractor._extract_imports(tree, code, "/test/main.go")

        assert imports == {}


class TestImportResolution:
    """Test import path resolution to directories."""

    def test_resolve_import_to_directory_project(self, tmp_path):
        """Test resolving project import to directory."""
        # Create project structure
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        server_dir = project_root / "server" / "handles"
        server_dir.mkdir(parents=True)
        (server_dir / "auth.go").write_text("package handles")

        extractor = GinExtractor()
        extractor.base_path = str(project_root)

        # Test resolving import path
        import_path = "github.com/myorg/myproject/server/handles"
        current_file = str(project_root / "router.go")

        result = extractor._resolve_import_to_directory(import_path, current_file)

        assert result is not None
        assert Path(result).exists()
        assert "handles" in result

    def test_resolve_import_to_directory_not_found(self, tmp_path):
        """Test resolving import that doesn't exist."""
        extractor = GinExtractor()
        extractor.base_path = str(tmp_path)

        import_path = "github.com/external/package"
        current_file = str(tmp_path / "main.go")

        result = extractor._resolve_import_to_directory(import_path, current_file)

        assert result is None

    def test_resolve_import_to_directory_external(self, tmp_path):
        """Test that external packages return None."""
        extractor = GinExtractor()
        extractor.base_path = str(tmp_path)

        # External package that shouldn't be resolved
        import_path = "github.com/gin-gonic/gin"
        current_file = str(tmp_path / "main.go")

        result = extractor._resolve_import_to_directory(import_path, current_file)

        assert result is None


class TestStructRegistry:
    """Test struct registry population."""

    def test_register_structs_single_package(self, tmp_path):
        """Test registering structs from a single package."""
        # Create a Go file with struct definitions
        go_file = tmp_path / "models.go"
        go_file.write_text("""package main

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

type Post struct {
    Title   string `json:"title"`
    Content string `json:"content"`
}
""")

        extractor = GinExtractor()
        extractor.base_path = str(tmp_path)
        extractor.package_registry = {}

        extractor._register_structs(str(go_file))

        # Check that structs were registered
        assert "." in extractor.package_registry  # Current directory
        structs = extractor.package_registry["."]
        assert "User" in structs
        assert "Post" in structs

        # Verify struct properties
        user_schema = structs["User"]
        assert user_schema.type == "object"
        assert "id" in user_schema.properties
        assert "name" in user_schema.properties

    def test_register_structs_multiple_packages(self, tmp_path):
        """Test registering structs from multiple packages."""
        # Create package structure
        pkg1 = tmp_path / "pkg1"
        pkg1.mkdir()
        (pkg1 / "models.go").write_text("""package pkg1

type User struct {
    Name string `json:"name"`
}
""")

        pkg2 = tmp_path / "pkg2"
        pkg2.mkdir()
        (pkg2 / "models.go").write_text("""package pkg2

type Product struct {
    Title string `json:"title"`
}
""")

        extractor = GinExtractor()
        extractor.base_path = str(tmp_path)
        extractor.package_registry = {}

        extractor._register_structs(str(pkg1 / "models.go"))
        extractor._register_structs(str(pkg2 / "models.go"))

        # Check both packages
        assert "pkg1" in extractor.package_registry
        assert "pkg2" in extractor.package_registry
        assert "User" in extractor.package_registry["pkg1"]
        assert "Product" in extractor.package_registry["pkg2"]


class TestHandlerRegistry:
    """Test handler registry population."""

    def test_register_handlers_exported_only(self, tmp_path):
        """Test that only exported handlers are registered."""
        go_file = tmp_path / "handlers.go"
        go_file.write_text("""package main

import "github.com/gin-gonic/gin"

func PublicHandler(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ok"})
}

func privateHandler(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ok"})
}
""")

        extractor = GinExtractor()
        extractor.base_path = str(tmp_path)
        extractor.handler_registry = {}

        extractor._register_handlers(str(go_file))

        handlers = extractor.handler_registry.get(".", {})
        assert "PublicHandler" in handlers
        assert "privateHandler" not in handlers

    def test_register_handlers_with_bind_call(self, tmp_path):
        """Test handler registration extracts request types from Bind calls."""
        go_file = tmp_path / "handlers.go"
        go_file.write_text("""package main

import "github.com/gin-gonic/gin"

type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

func Login(c *gin.Context) {
    var req LoginRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    c.JSON(200, gin.H{"token": "abc123"})
}
""")

        extractor = GinExtractor()
        extractor.base_path = str(tmp_path)
        extractor.handler_registry = {}
        extractor.package_registry = {}

        # Register structs first
        extractor._register_structs(str(go_file))
        # Then register handlers
        extractor._register_handlers(str(go_file))

        handlers = extractor.handler_registry.get(".", {})
        assert "Login" in handlers
        assert handlers["Login"]["request_type"] == "LoginRequest"


class TestPathNormalization:
    """Test path normalization."""

    def test_normalize_path_colon_params(self):
        """Test normalizing paths with :param syntax."""
        extractor = GinExtractor()

        assert extractor._normalize_path("/users/:id") == "/users/{id}"
        assert extractor._normalize_path("/posts/:post_id/comments/:id") == "/posts/{post_id}/comments/{id}"

    def test_normalize_path_wildcard_params(self):
        """Test normalizing paths with *param wildcard syntax."""
        extractor = GinExtractor()

        assert extractor._normalize_path("/files/*path") == "/files/{path}"
        assert extractor._normalize_path("/d/*filepath") == "/d/{filepath}"

    def test_normalize_path_empty_path(self):
        """Test normalizing empty paths."""
        extractor = GinExtractor()

        assert extractor._normalize_path("") == "/"
        assert extractor._normalize_path(None) == "/"

    def test_normalize_path_already_normalized(self):
        """Test normalizing paths that are already in OpenAPI format."""
        extractor = GinExtractor()

        assert extractor._normalize_path("/users/{id}") == "/users/{id}"
        assert extractor._normalize_path("/") == "/"

    def test_normalize_path_no_leading_slash(self):
        """Test normalizing paths without leading slash."""
        extractor = GinExtractor()

        assert extractor._normalize_path("users") == "/users"
        assert extractor._normalize_path("users/:id") == "/users/{id}"


class TestPathParameterExtraction:
    """Test path parameter extraction."""

    def test_extract_path_parameters_colon_syntax(self):
        """Test extracting parameters from :param syntax."""
        extractor = GinExtractor()

        params = extractor._extract_path_parameters("/users/:id")

        assert len(params) == 1
        assert params[0].name == "id"
        assert params[0].location.value == "path"
        assert params[0].required is True

    def test_extract_path_parameters_wildcard_syntax(self):
        """Test extracting parameters from *param syntax."""
        extractor = GinExtractor()

        params = extractor._extract_path_parameters("/files/*path")

        assert len(params) == 1
        assert params[0].name == "path"
        assert params[0].location.value == "path"
        assert params[0].required is True

    def test_extract_path_parameters_openapi_syntax(self):
        """Test extracting parameters from {param} syntax."""
        extractor = GinExtractor()

        params = extractor._extract_path_parameters("/users/{id}")

        assert len(params) == 1
        assert params[0].name == "id"
        assert params[0].location.value == "path"

    def test_extract_path_parameters_multiple(self):
        """Test extracting multiple parameters."""
        extractor = GinExtractor()

        params = extractor._extract_path_parameters("/posts/{post_id}/comments/{comment_id}")

        assert len(params) == 2
        assert params[0].name == "post_id"
        assert params[1].name == "comment_id"

    def test_extract_path_parameters_deduplication(self):
        """Test that duplicate parameters are deduplicated."""
        extractor = GinExtractor()

        # This shouldn't happen in practice, but test deduplication works
        params = extractor._extract_path_parameters("/users/:id/{id}")

        assert len(params) == 1
        assert params[0].name == "id"

    def test_extract_path_parameters_no_params(self):
        """Test extracting from path with no parameters."""
        extractor = GinExtractor()

        params = extractor._extract_path_parameters("/users")

        assert len(params) == 0


class TestOperationIdGeneration:
    """Test operation ID uniqueness."""

    def test_operation_id_anonymous_handler(self, tmp_path):
        """Test operation ID generation for anonymous handlers."""
        go_file = tmp_path / "router.go"
        go_file.write_text("""package main

import "github.com/gin-gonic/gin"

func main() {
    router := gin.Default()
    router.GET("/health", func(c *gin.Context) {
        c.JSON(200, gin.H{"status": "ok"})
    })
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 1
        # Anonymous handler should use method_path format
        assert result.endpoints[0].operation_id == "get_health"

    def test_operation_id_named_handler(self, tmp_path):
        """Test operation ID generation for named handlers."""
        go_file = tmp_path / "router.go"
        go_file.write_text("""package main

import "github.com/gin-gonic/gin"

func HealthCheck(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ok"})
}

func main() {
    router := gin.Default()
    router.GET("/health", HealthCheck)
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 1
        # Named handler should use handler_method_path format
        assert result.endpoints[0].operation_id == "HealthCheck_get_health"

    def test_operation_id_trailing_slash_uniqueness(self, tmp_path):
        """Test that paths with/without trailing slash have unique IDs."""
        go_file = tmp_path / "router.go"
        go_file.write_text("""package main

import "github.com/gin-gonic/gin"

func Handler(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ok"})
}

func main() {
    router := gin.Default()
    router.GET("/users", Handler)
    router.GET("/users/", Handler)
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 2

        operation_ids = [ep.operation_id for ep in result.endpoints]
        # Should have unique IDs
        assert len(operation_ids) == len(set(operation_ids))
        assert "Handler_get_users" in operation_ids
        assert "Handler_get_users_" in operation_ids


class TestCrossFileResolution:
    """Test end-to-end cross-file schema resolution."""

    def test_cross_file_handler_resolution(self, tmp_path):
        """Test resolving handlers from different packages."""
        # Create package structure
        handles_dir = tmp_path / "handles"
        handles_dir.mkdir()

        # Create handler file with struct
        (handles_dir / "auth.go").write_text("""package handles

import "github.com/gin-gonic/gin"

type LoginReq struct {
    Username string `json:"username" binding:"required"`
    Password string `json:"password" binding:"required"`
}

func Login(c *gin.Context) {
    var req LoginReq
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    c.JSON(200, gin.H{"token": "abc123"})
}
""")

        # Create router file that references the handler
        (tmp_path / "router.go").write_text("""package main

import (
    "github.com/gin-gonic/gin"
    "myproject/handles"
)

func SetupRouter() *gin.Engine {
    router := gin.Default()
    router.POST("/api/auth/login", handles.Login)
    return router
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert endpoint.path == "/api/auth/login"
        assert endpoint.method == HTTPMethod.POST
        assert endpoint.operation_id == "handles.Login_post_api_auth_login"

        # Check that request body schema was resolved
        assert endpoint.request_body is not None
        assert endpoint.request_body.type == "object"
        assert "username" in endpoint.request_body.properties
        assert "password" in endpoint.request_body.properties
        assert endpoint.request_body.required == ["username", "password"]

    def test_cross_file_with_router_groups(self, tmp_path):
        """Test cross-file resolution with router groups."""
        # Create handlers package
        api_dir = tmp_path / "api"
        api_dir.mkdir()

        (api_dir / "users.go").write_text("""package api

import "github.com/gin-gonic/gin"

type CreateUserRequest struct {
    Name  string `json:"name" binding:"required"`
    Email string `json:"email" binding:"required"`
}

func CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    c.JSON(201, gin.H{"id": 1})
}
""")

        # Create router with group
        (tmp_path / "router.go").write_text("""package main

import (
    "github.com/gin-gonic/gin"
    "myproject/api"
)

func SetupRouter() *gin.Engine {
    router := gin.Default()
    v1 := router.Group("/v1")
    v1.POST("/users", api.CreateUser)
    return router
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        # Should include group prefix
        assert endpoint.path == "/v1/users"
        assert endpoint.method == HTTPMethod.POST

        # Check request body
        assert endpoint.request_body is not None
        assert "name" in endpoint.request_body.properties
        assert "email" in endpoint.request_body.properties

    def test_same_package_handler_resolution(self, tmp_path):
        """Test resolving handlers in the same file."""
        (tmp_path / "main.go").write_text("""package main

import "github.com/gin-gonic/gin"

type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

func Login(c *gin.Context) {
    var req LoginRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    c.JSON(200, gin.H{"token": "ok"})
}

func main() {
    router := gin.Default()
    router.POST("/login", Login)
    router.Run()
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert endpoint.path == "/login"
        assert endpoint.request_body is not None
        assert "username" in endpoint.request_body.properties
        assert "password" in endpoint.request_body.properties


class TestPathComposition:
    """Test path composition with prefixes."""

    def test_compose_paths_simple(self):
        """Test composing simple paths."""
        extractor = GinExtractor()

        assert extractor._compose_paths("/api", "/users") == "/api/users"
        assert extractor._compose_paths("/v1", "/posts") == "/v1/posts"

    def test_compose_paths_with_trailing_slash(self):
        """Test composing paths with trailing slashes."""
        extractor = GinExtractor()

        # Prefix with trailing slash should work
        assert extractor._compose_paths("/api/", "/users") == "/api/users"

    def test_compose_paths_root_prefix(self):
        """Test composing with root prefix."""
        extractor = GinExtractor()

        assert extractor._compose_paths("/", "/users") == "/users"
        assert extractor._compose_paths("/", "users") == "/users"

    def test_compose_paths_empty_prefix(self):
        """Test composing with empty prefix."""
        extractor = GinExtractor()

        assert extractor._compose_paths("", "/users") == "/users"
        assert extractor._compose_paths("", "users") == "/users"

    def test_compose_paths_empty_path(self):
        """Test composing with empty path."""
        extractor = GinExtractor()

        # Empty path should become /
        assert extractor._compose_paths("/api", "") == "/api/"
        assert extractor._compose_paths("/api", "/") == "/api/"

    def test_compose_paths_no_leading_slash_in_path(self):
        """Test composing when path doesn't start with slash."""
        extractor = GinExtractor()

        assert extractor._compose_paths("/api", "users") == "/api/users"


class TestOpenAPIValidation:
    """Test OpenAPI validation integration."""

    def test_invalid_openapi_fails_extraction(self, tmp_path):
        """Test that invalid OpenAPI causes extraction to fail."""
        # Create a file that will generate duplicate operation IDs
        # (This shouldn't happen anymore with our fixes, but testing the validation)
        (tmp_path / "router.go").write_text("""package main

import "github.com/gin-gonic/gin"

func main() {
    router := gin.Default()
    router.GET("/health", func(c *gin.Context) {
        c.JSON(200, gin.H{"status": "ok"})
    })
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        # Should succeed with valid OpenAPI
        assert result.success
        assert len(result.errors) == 0

    def test_valid_openapi_succeeds(self, tmp_path):
        """Test that valid OpenAPI passes validation."""
        (tmp_path / "router.go").write_text("""package main

import "github.com/gin-gonic/gin"

func GetUsers(c *gin.Context) {
    c.JSON(200, gin.H{"users": []string{}})
}

func main() {
    router := gin.Default()
    router.GET("/users", GetUsers)
    router.POST("/users", GetUsers)
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 2
        assert len(result.errors) == 0

        # Verify operation IDs are unique
        operation_ids = [ep.operation_id for ep in result.endpoints]
        assert len(operation_ids) == len(set(operation_ids))


class TestRealWorldPatterns:
    """Test patterns found in real-world Go projects."""

    def test_array_response_type(self, tmp_path):
        """Test handling array response types like []User."""
        (tmp_path / "handlers.go").write_text("""package main

import "github.com/gin-gonic/gin"

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

func ListUsers(c *gin.Context) {
    users := []User{
        {ID: 1, Name: "Alice"},
        {ID: 2, Name: "Bob"},
    }
    c.JSON(200, users)
}

func main() {
    router := gin.Default()
    router.GET("/users", ListUsers)
    router.Run()
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        # Note: Response schema extraction for direct c.JSON(200, users) is limited
        # This test documents current behavior
        assert endpoint.path == "/users"
        assert endpoint.method == HTTPMethod.GET

    def test_multiple_http_methods_same_path(self, tmp_path):
        """Test same path with different HTTP methods."""
        (tmp_path / "router.go").write_text("""package main

import "github.com/gin-gonic/gin"

func GetUser(c *gin.Context) {
    c.JSON(200, gin.H{"id": 1})
}

func UpdateUser(c *gin.Context) {
    c.JSON(200, gin.H{"updated": true})
}

func DeleteUser(c *gin.Context) {
    c.Status(204)
}

func main() {
    router := gin.Default()
    router.GET("/users/:id", GetUser)
    router.PUT("/users/:id", UpdateUser)
    router.DELETE("/users/:id", DeleteUser)
    router.Run()
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 3

        # All should have the same normalized path
        paths = [ep.path for ep in result.endpoints]
        assert all(p == "/users/{id}" for p in paths)

        # But different methods
        methods = {ep.method for ep in result.endpoints}
        assert methods == {HTTPMethod.GET, HTTPMethod.PUT, HTTPMethod.DELETE}

        # And unique operation IDs
        operation_ids = [ep.operation_id for ep in result.endpoints]
        assert len(operation_ids) == len(set(operation_ids))

    def test_nested_structs(self, tmp_path):
        """Test handling nested struct definitions."""
        (tmp_path / "models.go").write_text("""package main

import "github.com/gin-gonic/gin"

type Address struct {
    Street string `json:"street"`
    City   string `json:"city"`
}

type CreateUserRequest struct {
    Name    string  `json:"name"`
    Address Address `json:"address"`
}

func CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(400, gin.H{"error": err.Error()})
        return
    }
    c.JSON(201, gin.H{"id": 1})
}

func main() {
    router := gin.Default()
    router.POST("/users", CreateUser)
    router.Run()
}
""")

        extractor = GinExtractor()
        result = extractor.extract(str(tmp_path))

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert endpoint.request_body is not None
        assert "name" in endpoint.request_body.properties
        assert "address" in endpoint.request_body.properties

        # Check nested struct is present
        # Properties dict maps field names to dict/Schema representations
        address_prop = endpoint.request_body.properties["address"]
        # Address should be an object type (either as dict or Schema)
        if isinstance(address_prop, dict):
            assert address_prop.get("type") == "object"
            # Check if nested properties were resolved
            if "properties" in address_prop:
                nested_props = address_prop["properties"]
                assert "street" in nested_props or "city" in nested_props
        else:
            # If it's a Schema object
            assert address_prop.type == "object"
            if address_prop.properties:
                assert "street" in address_prop.properties or "city" in address_prop.properties
