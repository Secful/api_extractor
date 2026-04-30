"""Tests for Spring Boot schema extraction."""

from api_extractor.extractors.java.spring_boot import SpringBootExtractor
from api_extractor.core.models import HTTPMethod
import pytest


@pytest.fixture
def extractor():
    """Create Spring Boot extractor instance."""
    return SpringBootExtractor()


def test_extract_return_type_simple(extractor, tmp_path):
    """Test extraction of simple return types."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;

    class User {
        private String name;
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }

    @RestController
    public class TestController {
        @GetMapping("/user")
        public User getUser() {
            return null;
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.method == HTTPMethod.GET
    assert endpoint.path == "/user"
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "name" in endpoint.responses[0].response_schema.properties


def test_extract_return_type_list(extractor, tmp_path):
    """Test extraction of List<T> return types."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;
    import java.util.List;

    class Product {
        private Long id;
        private String name;
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }

    @RestController
    public class TestController {
        @GetMapping("/products")
        public List<Product> getAllProducts() {
            return null;
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "array"
    assert endpoint.responses[0].response_schema.items is not None
    assert endpoint.responses[0].response_schema.items.type == "object"
    assert "id" in endpoint.responses[0].response_schema.items.properties
    assert "name" in endpoint.responses[0].response_schema.items.properties


def test_request_body_extraction(extractor, tmp_path):
    """Test extraction of @RequestBody schemas."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;

    class CreateUserRequest {
        private String username;
        private String email;
        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }
        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
    }

    class User {
        private Long id;
        private String username;
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }
    }

    @RestController
    public class TestController {
        @PostMapping("/users")
        public User createUser(@RequestBody CreateUserRequest request) {
            return null;
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.method == HTTPMethod.POST
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "object"
    assert "username" in endpoint.request_body.properties
    assert "email" in endpoint.request_body.properties

    # Verify response schema too
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "id" in endpoint.responses[0].response_schema.properties
    assert "username" in endpoint.responses[0].response_schema.properties


def test_response_entity_wrapper(extractor, tmp_path):
    """Test that ResponseEntity<T> is unwrapped to T."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;
    import org.springframework.http.ResponseEntity;

    class Product {
        private String name;
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }

    @RestController
    public class TestController {
        @GetMapping("/product")
        public ResponseEntity<Product> getProduct() {
            return null;
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "object"
    assert "name" in endpoint.responses[0].response_schema.properties


def test_void_return_type(extractor, tmp_path):
    """Test that void return types don't create response schemas."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;

    @RestController
    public class TestController {
        @DeleteMapping("/user/{id}")
        public void deleteUser(@PathVariable Long id) {
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.method == HTTPMethod.DELETE
    # Void methods should not have a response schema
    assert endpoint.responses[0].response_schema is None


def test_request_body_with_list(extractor, tmp_path):
    """Test extraction of List<T> in request body."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;
    import java.util.List;

    class User {
        private String name;
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }

    @RestController
    public class TestController {
        @PostMapping("/users/batch")
        public void createUsers(@RequestBody List<User> users) {
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    assert endpoint.request_body is not None
    assert endpoint.request_body.type == "array"
    assert endpoint.request_body.items is not None
    assert endpoint.request_body.items.type == "object"
    assert "name" in endpoint.request_body.items.properties


def test_nested_generic_types(extractor, tmp_path):
    """Test extraction of nested generic types like ResponseEntity<List<User>>."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;
    import org.springframework.http.ResponseEntity;
    import java.util.List;

    class Item {
        private String title;
        public String getTitle() { return title; }
        public void setTitle(String title) { this.title = title; }
    }

    @RestController
    public class TestController {
        @GetMapping("/items")
        public ResponseEntity<List<Item>> getItems() {
            return null;
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 1

    endpoint = result.endpoints[0]
    # Should unwrap ResponseEntity and handle List<Item>
    assert endpoint.responses[0].response_schema is not None
    assert endpoint.responses[0].response_schema.type == "array"
    assert endpoint.responses[0].response_schema.items is not None
    assert endpoint.responses[0].response_schema.items.type == "object"
    assert "title" in endpoint.responses[0].response_schema.items.properties


def test_multiple_dtos_in_file(extractor, tmp_path):
    """Test extraction when multiple DTOs exist in the same file."""
    java_code = """
    package com.example;

    import org.springframework.web.bind.annotation.*;

    class CreateRequest {
        private String name;
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
    }

    class UpdateRequest {
        private String description;
        public String getDescription() { return description; }
        public void setDescription(String description) { this.description = description; }
    }

    class Response {
        private Long id;
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
    }

    @RestController
    public class TestController {
        @PostMapping("/items")
        public Response create(@RequestBody CreateRequest request) {
            return null;
        }

        @PutMapping("/items/{id}")
        public Response update(@PathVariable Long id, @RequestBody UpdateRequest request) {
            return null;
        }
    }
    """

    file_path = tmp_path / "TestController.java"
    file_path.write_text(java_code)

    result = extractor.extract(str(tmp_path))

    assert result.success
    assert len(result.endpoints) == 2

    # Check POST endpoint
    post_endpoint = next(ep for ep in result.endpoints if ep.method == HTTPMethod.POST)
    assert post_endpoint.request_body is not None
    assert "name" in post_endpoint.request_body.properties
    assert post_endpoint.responses[0].response_schema is not None
    assert "id" in post_endpoint.responses[0].response_schema.properties

    # Check PUT endpoint
    put_endpoint = next(ep for ep in result.endpoints if ep.method == HTTPMethod.PUT)
    assert put_endpoint.request_body is not None
    assert "description" in put_endpoint.request_body.properties
    assert put_endpoint.responses[0].response_schema is not None
    assert "id" in put_endpoint.responses[0].response_schema.properties


def test_schema_extraction_coverage(extractor):
    """Test schema extraction coverage on real fixture."""
    result = extractor.extract("tests/fixtures/minimal/java/spring-boot")

    assert result.success
    assert len(result.endpoints) >= 7

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

    # All POST/PUT should have request bodies (DELETE and GET with params might not)
    assert endpoints_with_request_body == post_put_endpoints
