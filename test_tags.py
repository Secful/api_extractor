#!/usr/bin/env python3
"""Debug tags GET response extraction."""

from api_extractor.extractors.java.spring_boot import SpringBootExtractor

extractor = SpringBootExtractor()

# Read and parse TagsApi.java
source_code = extractor._read_file("tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/TagsApi.java")
tree = extractor.parser.parse_source(source_code, "java")

# Find getTags method
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

    if method_name == "getTags":
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

            # Test pattern manually
            import re
            hashmap_pattern = r'put\s*\(\s*"[^"]+"\s*,\s*([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match = re.search(hashmap_pattern, body_text)
            print(f"HashMap pattern match: {match}")
            if match:
                print(f"  Service var: {match.group(1)}")
                print(f"  Service method: {match.group(2)}")

                # Check service field type
                service_type = extractor._find_service_field_type(method_decl_node, match.group(1), source_code)
                print(f"  Service type: {service_type}")

        # Try service method tracing
        service_response = extractor._extract_service_method_response(
            method_decl_node,
            source_code,
            "tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/TagsApi.java"
        )
        print(f"\nService response type: {service_response}")

        break
