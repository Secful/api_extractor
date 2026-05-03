#!/usr/bin/env python3
"""Debug article slug endpoints."""

from api_extractor.extractors.java.spring_boot import SpringBootExtractor

extractor = SpringBootExtractor()

# Read and parse ArticleApi.java
source_code = extractor._read_file("tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/ArticleApi.java")
tree = extractor.parser.parse_source(source_code, "java")

# Find methods
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

    if method_name in ("article", "updateArticle"):
        print(f"\n{'='*60}")
        print(f"Method: {method_name}")
        print(f"{'='*60}\n")

        # Get body node
        body_node = None
        for child in method_decl_node.children:
            if child.type == "block":
                body_node = child
                break

        if body_node:
            body_text = extractor.parser.get_node_text(body_node, source_code)
            print(f"Body text:\n{body_text[:300]}...\n")

            # Test patterns manually
            import re

            # Pattern 1
            pattern1 = r'return\s+ResponseEntity\.\w+\s*\(\s*([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match1 = re.search(pattern1, body_text)
            print(f"Pattern 1 match: {match1}")

            # Pattern 3 (HashMap)
            pattern3 = r'put\s*\(\s*"[^"]+"\s*,\s*([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match3 = re.search(pattern3, body_text)
            print(f"Pattern 3 match: {match3}")

            # Pattern 2 (helper)
            pattern2 = r'(?:return\s+\w+\s*\(|\.body\s*\(\s*\w+\s*\()\s*([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match2 = re.search(pattern2, body_text)
            print(f"Pattern 2 match: {match2}")

            # Pattern 2b (chained)
            pattern2b = r'return\s+([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\([^)]*\)\s*\.map\s*\('
            match2b = re.search(pattern2b, body_text)
            print(f"Pattern 2b match: {match2b}")

            # Pattern 2c (simple return)
            pattern2c = r'return\s+(?!ResponseEntity)([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
            match2c = re.search(pattern2c, body_text)
            print(f"Pattern 2c match: {match2c}")
            if match2c:
                print(f"  Service: {match2c.group(1)}, Method: {match2c.group(2)}")

            print()

        # Try service method tracing
        service_response = extractor._extract_service_method_response(
            method_decl_node,
            source_code,
            "tests/fixtures/real-world/java/spring-boot/spring-boot-realworld-example-app/src/main/java/io/spring/api/ArticleApi.java"
        )
        print(f"Service response type: {service_response}")
