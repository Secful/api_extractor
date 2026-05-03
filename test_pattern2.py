#!/usr/bin/env python3
"""Test pattern matching with actual text."""

import re

body_text = """{
    return articleQueryService
        .findBySlug(slug, user)
        .map(articleData -> ResponseEntity.ok(articleResponse(articleData)))
        .orElseThrow(ResourceNotFoundException::new);
  }"""

# Pattern 2c
pattern2c = r'return\s+(?!ResponseEntity)([a-zA-Z_]\w+)\.([a-zA-Z_]\w+)\s*\('
match2c = re.search(pattern2c, body_text)
print(f"Pattern 2c match: {match2c}")

# Try adding \s* before the dot
pattern2c_fixed = r'return\s+(?!ResponseEntity)([a-zA-Z_]\w+)\s*\.([a-zA-Z_]\w+)\s*\('
match2c_fixed = re.search(pattern2c_fixed, body_text)
print(f"Pattern 2c fixed match: {match2c_fixed}")
if match2c_fixed:
    print(f"  Service: {match2c_fixed.group(1)}, Method: {match2c_fixed.group(2)}")
