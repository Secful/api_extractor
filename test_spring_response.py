#!/usr/bin/env python3
"""Debug Spring Boot response extraction."""

from api_extractor.extractors.java.spring_boot import SpringBootExtractor

extractor = SpringBootExtractor()

# Read and parse ArticlesApi.java
source_code = extractor._read_file("tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/ArticlesApi.java")
tree = extractor.parser.parse_source(source_code, "java")

# Find getArticles method
method_query = """
(method_declaration
  name: (identifier) @method_name
  parameters: (formal_parameters) @params) @method_decl
"""

matches = extractor.parser.query(tree, method_query, "java")

for match in matches:
    method_name_node = match.get("method_name")
    method_decl_node = match.get("method_decl")

    if not method_name_node or not method_decl_node:
        continue

    method_name = extractor.parser.get_node_text(method_name_node, source_code)

    if method_name == "getArticles":
        print(f"Found method: {method_name}\n")

        # Extract return type
        return_type_raw = extractor._extract_return_type(method_decl_node, source_code)
        print(f"Return type raw: {return_type_raw}")

        # Try service method tracing
        service_response = extractor._extract_service_method_response(
            method_decl_node,
            source_code,
            "tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/ArticlesApi.java"
        )
        print(f"Service response type: {service_response}")

        # Find service field type
        body_text = extractor.parser.get_node_text(method_decl_node, source_code)
        print(f"\nMethod body preview:\n{body_text[:300]}")

        break
