#!/usr/bin/env python3
"""Debug Comments GET response extraction."""

from api_extractor.extractors.java.spring_boot import SpringBootExtractor

extractor = SpringBootExtractor()

# Read and parse CommentsApi.java
source_code = extractor._read_file("tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/CommentsApi.java")
tree = extractor.parser.parse_source(source_code, "java")

# Find getComments method
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

    if method_name == "getComments":
        print(f"Found method: {method_name}\n")

        # Get body node
        body_node = None
        for child in method_decl_node.children:
            if child.type == "block":
                body_node = child
                break

        if body_node:
            body_text = extractor.parser.get_node_text(body_node, source_code)
            print(f"Body text:\n{body_text}\n")

        # Try service method tracing
        service_response = extractor._extract_service_method_response(
            method_decl_node,
            source_code,
            "tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/CommentsApi.java"
        )
        print(f"Service response type: {service_response}")

        break
