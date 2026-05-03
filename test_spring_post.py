#!/usr/bin/env python3
"""Debug Spring Boot POST response extraction."""

from api_extractor.extractors.java.spring_boot import SpringBootExtractor

extractor = SpringBootExtractor()

# Read and parse ArticlesApi.java
source_code = extractor._read_file("tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/ArticlesApi.java")
tree = extractor.parser.parse_source(source_code, "java")

# Find createArticle method
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

    if method_name == "createArticle":
        print(f"Found method: {method_name}\n")

        # Extract return type
        return_type_raw = extractor._extract_return_type(method_decl_node, source_code)
        print(f"Return type raw: {return_type_raw}")

        # Get body node
        body_node = None
        for child in method_decl_node.children:
            if child.type == "block":
                body_node = child
                break

        if body_node:
            body_text = extractor.parser.get_node_text(body_node, source_code)
            print(f"Body text type: {type(body_text)}")
            print(f"Body text preview:\n{body_text[:500]}\n")

            # Test patterns manually
            import re

            # Pattern 1
            pattern1 = r'return\s+ResponseEntity\.\w+\s*\(\s*([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match1 = re.search(pattern1, body_text)
            print(f"Pattern 1 match: {match1}")

            # Pattern 2
            pattern2 = r'return\s+([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match2 = re.search(pattern2, body_text)
            print(f"Pattern 2 match: {match2}")

            # Pattern 3
            pattern3 = r'put\s*\(\s*"[^"]+"\s*,\s*([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match3 = re.search(pattern3, body_text)
            print(f"Pattern 3 match: {match3}")
            if match3:
                print(f"  Service var: {match3.group(1)}")
                print(f"  Service method: {match3.group(2)}")

        # Test _find_service_field_type manually
        if match3:
            service_var = match3.group(1)
            service_method = match3.group(2)
            service_type = extractor._find_service_field_type(method_decl_node, service_var, source_code)
            print(f"\nService field type for '{service_var}': {service_type}")

            # Test heuristic manually
            if service_type:
                print(f"\nTesting heuristic:")
                print(f"  service_type: {service_type}")
                print(f"  service_method: {service_method}")
                print(f"  'QueryService' in service_type: {'QueryService' in service_type}")
                if "QueryService" in service_type:
                    base_name = service_type.replace("QueryService", "")
                    print(f"  base_name: {base_name}")
                    print(f"  'find' in service_method.lower(): {'find' in service_method.lower()}")
                    if "find" in service_method.lower():
                        result = f"{base_name}Data"
                        print(f"  SHOULD RETURN: {result}")

        # Try service method tracing
        service_response = extractor._extract_service_method_response(
            method_decl_node,
            source_code,
            "tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/ArticlesApi.java"
        )
        print(f"Service response type: {service_response}")

        break
