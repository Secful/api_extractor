# Lambda Verification Results ✅

## Test Command
```bash
unset AWS_PROFILE && python3 test_lambda_http.py spring-boot-realworld
```

## Results Summary

### Request Bodies: ✅ WORKING (75% coverage)

**Endpoints WITH request bodies (6/8):**
1. ✅ `/articles POST` - has NewArticleParam (title, description, body, tagList)
2. ✅ `/users POST` - has RegisterParam (email, username, password)
3. ✅ `/users/login POST` - has LoginParam (email, password)
4. ✅ `/articles/{slug} PUT` - has UpdateArticleParam
5. ✅ `/articles/{slug}/comments POST` - has NewCommentParam (body)
6. ✅ `/user PUT` - has UpdateUserParam

**Endpoints WITHOUT request bodies (2/8) - CORRECT:**
- ❌ `/articles/{slug}/favorite POST` - No @RequestBody in source (only path param)
- ❌ `/profiles/{username}/follow POST` - No @RequestBody in source (only path param)

### Response Schemas: ⚠️ EXPECTED LIMITATION (0% coverage)

**Why all responses are missing:**
The Spring Boot app uses untyped `ResponseEntity<?>` with dynamic HashMap construction:

```java
public ResponseEntity<?> createArticle(...) {
    return ResponseEntity.ok(
        new HashMap<String, Object>() {{
            put("article", articleQueryService.findById(...).get());
        }}
    );
}
```

This pattern cannot be extracted statically because:
- Return type is `ResponseEntity<?>` (wildcard - no type info)
- Actual response built at runtime
- Would require tracing service method calls

## Comparison: Before vs After

### BEFORE (Old Lambda)
```json
{
  "/articles": {
    "post": {
      "responses": {"200": {"description": "Success"}}
    }
  },
  "/users": {
    "post": {
      "responses": {"200": {"description": "Success"}}
    }
  }
}
```
- Request bodies: 2/8 endpoints (25%)
- Validation: None
- Required fields: None

### AFTER (Current Lambda) ✅
```json
{
  "/articles": {
    "post": {
      "requestBody": {
        "content": {
          "application/json": {
            "schema": {
              "type": "object",
              "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "body": {"type": "string"},
                "tagList": {"type": "array"}
              },
              "required": ["title", "description", "body"]
            }
          }
        },
        "required": true
      }
    }
  },
  "/users/login": {
    "post": {
      "requestBody": {
        "content": {
          "application/json": {
            "schema": {
              "type": "object",
              "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string"}
              },
              "required": ["email", "password"]
            }
          }
        },
        "required": true
      }
    }
  }
}
```
- Request bodies: 6/8 endpoints (75%) ✅ **+200% improvement**
- Validation: Email format, required fields ✅
- Required fields: All tracked ✅

## Verification Commands

### Check request body coverage:
```bash
jq '[.paths[][] | select(.requestBody)] | length' extracted_openapi.json
# Result: 6
```

### Check specific endpoint:
```bash
jq '.paths."/users/login".post.requestBody' extracted_openapi.json
```

### Check validation constraints:
```bash
jq '.paths."/users/login".post.requestBody.content."application/json".schema' extracted_openapi.json
```

## Conclusion

✅ **Lambda IS updated and working correctly!**

- Cross-file DTO resolution: **WORKING**
- Validation extraction: **WORKING** (email format, required fields)
- Request bodies: **6/8 endpoints (75%)**
- Response schemas: **0/14 endpoints (expected - see limitation above)**

The 2 missing request bodies are correct - those endpoints don't have `@RequestBody` annotations in the source code.

The missing response schemas are a **known limitation** documented in SPRING_BOOT_IMPROVEMENTS.md - they require runtime analysis or typed `ResponseEntity<T>` patterns.
