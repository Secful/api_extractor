#!/usr/bin/env python3
"""Test pattern matching."""

import re

body_text = """{
    return articleQueryService
        .findBySlug(slug, user)
        .map(articleData -> ResponseEntity.ok(articleResponse(articleData)))
        .orElseThrow(ResourceNotFoundException::new);
  }"""

# Test chained pattern
chained_pattern = r'return\s+([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\([^)]*\)\s*\.map\s*\('
match = re.search(chained_pattern, body_text)
print(f"Chained pattern match: {match}")

# Try with DOTALL flag to match across newlines
match2 = re.search(chained_pattern, body_text, re.DOTALL)
print(f"Chained pattern match (DOTALL): {match2}")

# Try simpler pattern that allows newlines
simple_chained = r'return\s+([a-zA-Z_]\w+)\s*\.([a-zA-Z_]\w+)\s*\('
match3 = re.search(simple_chained, body_text)
print(f"Simple pattern match: {match3}")
if match3:
    print(f"  Groups: {match3.groups()}")
