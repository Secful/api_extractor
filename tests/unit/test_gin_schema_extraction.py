"""Unit tests for Gin schema extraction."""

from __future__ import annotations

import pytest

from api_extractor.extractors.go.gin import GinExtractor


class TestGinStructParsing:
    """Test struct definition extraction."""

    def test_simple_struct_extraction(self, tmp_path):
        """Test extraction of simple struct with json tags."""
        go_code = '''
package main

type User struct {
    ID       uint   `json:"id"`
    Username string `json:"username"`
    Email    string `json:"email"`
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        tree = extractor.parser.parse_source(go_code.encode(), "go")
        struct_schemas = extractor._find_struct_definitions(tree, go_code.encode())

        assert "User" in struct_schemas
        user_schema = struct_schemas["User"]
        assert user_schema.type == "object"
        assert "id" in user_schema.properties
        assert "username" in user_schema.properties
        assert "email" in user_schema.properties

    def test_struct_with_required_fields(self, tmp_path):
        """Test struct with binding:required tag."""
        go_code = '''
package main

type CreateUserRequest struct {
    Username string `json:"username" binding:"required"`
    Email    string `json:"email" binding:"required"`
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        tree = extractor.parser.parse_source(go_code.encode(), "go")
        struct_schemas = extractor._find_struct_definitions(tree, go_code.encode())

        assert "CreateUserRequest" in struct_schemas
        schema = struct_schemas["CreateUserRequest"]
        assert schema.required == ["username", "email"]

    def test_struct_with_omitempty(self, tmp_path):
        """Test struct with omitempty tag (not required)."""
        go_code = '''
package main

type Product struct {
    ID    uint    `json:"id"`
    Name  string  `json:"name" binding:"required"`
    Price float64 `json:"price,omitempty"`
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        tree = extractor.parser.parse_source(go_code.encode(), "go")
        struct_schemas = extractor._find_struct_definitions(tree, go_code.encode())

        assert "Product" in struct_schemas
        schema = struct_schemas["Product"]
        # Only 'name' and 'id' are required ('price' has omitempty)
        assert "name" in schema.required
        assert "id" in schema.required
        assert "price" not in schema.required


class TestGinGoTagParsing:
    """Test Go struct tag parsing."""

    def test_parse_json_tag_simple(self):
        """Test parsing simple json tag."""
        extractor = GinExtractor()
        result = extractor._parse_go_tag('`json:"user_id"`')

        assert "json" in result
        assert result["json"] == "user_id"

    def test_parse_json_tag_with_omitempty(self):
        """Test parsing json tag with omitempty."""
        extractor = GinExtractor()
        result = extractor._parse_go_tag('`json:"user_id,omitempty"`')

        assert result["json"] == "user_id"
        assert result.get("omitempty") is True

    def test_parse_binding_tag(self):
        """Test parsing binding:required tag."""
        extractor = GinExtractor()
        result = extractor._parse_go_tag('`json:"username" binding:"required"`')

        assert result["json"] == "username"
        assert result["binding"] == "required"

    def test_parse_multiple_tags(self):
        """Test parsing multiple tags."""
        extractor = GinExtractor()
        result = extractor._parse_go_tag('`json:"email,omitempty" binding:"email"`')

        assert result["json"] == "email"
        assert result.get("omitempty") is True
        assert result["binding"] == "email"


class TestGinGoTypeParsing:
    """Test Go type to OpenAPI type conversion."""

    def test_basic_types(self):
        """Test basic Go type mapping."""
        extractor = GinExtractor()

        assert extractor._parse_go_type("string") == "string"
        assert extractor._parse_go_type("int") == "integer"
        assert extractor._parse_go_type("int64") == "integer"
        assert extractor._parse_go_type("uint") == "integer"
        assert extractor._parse_go_type("float64") == "number"
        assert extractor._parse_go_type("bool") == "boolean"

    def test_pointer_types(self):
        """Test pointer type handling."""
        extractor = GinExtractor()

        assert extractor._parse_go_type("*string") == "string"
        assert extractor._parse_go_type("*User") == "object"

    def test_slice_types(self):
        """Test slice (array) type handling."""
        extractor = GinExtractor()

        assert extractor._parse_go_type("[]string") == "array"
        assert extractor._parse_go_type("[]User") == "array"

    def test_map_types(self):
        """Test map (object) type handling."""
        extractor = GinExtractor()

        assert extractor._parse_go_type("map[string]string") == "object"
        assert extractor._parse_go_type("map[string]User") == "object"


class TestGinHandlerSchemaExtraction:
    """Test handler function schema extraction."""

    def test_extract_request_body_from_bind(self, tmp_path):
        """Test extracting request body from BindJSON call."""
        go_code = '''
package main

type CreateUserRequest struct {
    Username string `json:"username"`
    Email    string `json:"email"`
}

func CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        return
    }
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        tree = extractor.parser.parse_source(go_code.encode(), "go")
        struct_schemas = extractor._find_struct_definitions(tree, go_code.encode())

        handler_schemas = extractor._extract_handler_schemas(
            "CreateUser", tree, go_code.encode(), struct_schemas
        )

        assert "request_body" in handler_schemas
        assert handler_schemas["request_body"].type == "object"
        assert "username" in handler_schemas["request_body"].properties
        assert "email" in handler_schemas["request_body"].properties

    def test_extract_response_from_json_call(self, tmp_path):
        """Test extracting response from c.JSON call."""
        go_code = '''
package main

type User struct {
    ID       uint   `json:"id"`
    Username string `json:"username"`
}

func GetUser(c *gin.Context) {
    user := User{ID: 1, Username: "john"}
    c.JSON(http.StatusOK, user)
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        tree = extractor.parser.parse_source(go_code.encode(), "go")
        struct_schemas = extractor._find_struct_definitions(tree, go_code.encode())

        handler_schemas = extractor._extract_handler_schemas(
            "GetUser", tree, go_code.encode(), struct_schemas
        )

        assert "response_schema" in handler_schemas
        assert handler_schemas["response_schema"].type == "object"
        assert "id" in handler_schemas["response_schema"].properties
        assert "username" in handler_schemas["response_schema"].properties

    def test_skip_error_response_gin_h(self, tmp_path):
        """Test skipping gin.H error responses."""
        go_code = '''
package main

type User struct {
    ID       uint   `json:"id"`
    Username string `json:"username"`
}

func CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    user := User{ID: 1, Username: req.Username}
    c.JSON(http.StatusOK, user)
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        tree = extractor.parser.parse_source(go_code.encode(), "go")
        struct_schemas = extractor._find_struct_definitions(tree, go_code.encode())

        handler_schemas = extractor._extract_handler_schemas(
            "CreateUser", tree, go_code.encode(), struct_schemas
        )

        # Should extract User response, not gin.H error
        assert "response_schema" in handler_schemas
        assert handler_schemas["response_schema"].type == "object"
        assert "id" in handler_schemas["response_schema"].properties
        assert "username" in handler_schemas["response_schema"].properties

    def test_extract_array_response(self, tmp_path):
        """Test extracting array response from []Type{}."""
        go_code = '''
package main

type User struct {
    ID       uint   `json:"id"`
    Username string `json:"username"`
}

func GetAllUsers(c *gin.Context) {
    users := []User{
        {ID: 1, Username: "john"},
        {ID: 2, Username: "jane"},
    }
    c.JSON(http.StatusOK, users)
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        tree = extractor.parser.parse_source(go_code.encode(), "go")
        struct_schemas = extractor._find_struct_definitions(tree, go_code.encode())

        handler_schemas = extractor._extract_handler_schemas(
            "GetAllUsers", tree, go_code.encode(), struct_schemas
        )

        assert "response_schema" in handler_schemas
        # Should be wrapped in array schema
        assert handler_schemas["response_schema"].type == "array"
        assert handler_schemas["response_schema"].items is not None
        assert handler_schemas["response_schema"].items.type == "object"
        assert "id" in handler_schemas["response_schema"].items.properties


class TestGinRouteExtraction:
    """Test complete route extraction with schemas."""

    def test_route_with_request_and_response_schemas(self, tmp_path):
        """Test extracting route with both request and response schemas."""
        go_code = '''
package main

type CreateUserRequest struct {
    Username string `json:"username" binding:"required"`
    Email    string `json:"email" binding:"required"`
}

type User struct {
    ID       uint   `json:"id"`
    Username string `json:"username"`
    Email    string `json:"email"`
}

func CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    user := User{ID: 1, Username: req.Username, Email: req.Email}
    c.JSON(http.StatusOK, user)
}

func SetupRoutes(router *gin.Engine) {
    router.POST("/users", CreateUser)
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        routes = extractor.extract_routes_from_file(str(file_path))

        assert len(routes) == 1
        route = routes[0]

        # Check request body schema
        assert "request_body" in route.metadata
        request_schema = route.metadata["request_body"]
        assert request_schema.type == "object"
        assert "username" in request_schema.properties
        assert "email" in request_schema.properties
        assert request_schema.required == ["username", "email"]

        # Check response schema
        assert "response_schema" in route.metadata
        response_schema = route.metadata["response_schema"]
        assert response_schema.type == "object"
        assert "id" in response_schema.properties
        assert "username" in response_schema.properties
        assert "email" in response_schema.properties

    def test_endpoint_population(self, tmp_path):
        """Test that endpoints are correctly populated with schemas."""
        go_code = '''
package main

type User struct {
    ID       uint   `json:"id"`
    Username string `json:"username"`
}

func GetUser(c *gin.Context) {
    user := User{ID: 1, Username: "john"}
    c.JSON(http.StatusOK, user)
}

func SetupRoutes(router *gin.Engine) {
    router.GET("/users/:id", GetUser)
}
'''
        file_path = tmp_path / "test.go"
        file_path.write_text(go_code)

        extractor = GinExtractor()
        routes = extractor.extract_routes_from_file(str(file_path))

        assert len(routes) == 1

        # Convert to endpoints
        endpoints = extractor._route_to_endpoints(routes[0])
        assert len(endpoints) == 1

        endpoint = endpoints[0]
        assert endpoint.path == "/users/{id}"

        # Check response schema
        assert endpoint.responses
        assert endpoint.responses[0].response_schema is not None
        assert endpoint.responses[0].response_schema.type == "object"
        assert "id" in endpoint.responses[0].response_schema.properties
        assert "username" in endpoint.responses[0].response_schema.properties
