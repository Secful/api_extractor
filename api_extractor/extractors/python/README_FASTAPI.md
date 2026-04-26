# FastAPI Extractor

Extracts REST API routes from FastAPI applications using Tree-sitter AST parsing.

## How It Works

### Detection Pattern

FastAPI routes are defined using decorators on async/sync functions:

```python
from fastapi import FastAPI, APIRouter

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id}
```

### Tree-sitter AST Structure

The extractor looks for this pattern:

```
decorated_definition
  decorator
    call
      function: attribute
        object: identifier ("app" or router variable)
        attribute: identifier ("get", "post", "put", "delete", "patch")
      arguments
        string (path)
  function_definition
    name: identifier
    parameters: parameters
```

### Extraction Process

1. **Find Decorated Functions**
   - Search for `decorated_definition` nodes
   - Check if decorator is a method call on `app` or `router`

2. **Extract HTTP Method**
   - Parse decorator attribute: `@app.get()` → GET
   - Supported: get, post, put, delete, patch, head, options

3. **Extract Path**
   - Get first argument from decorator call
   - Path string: `"/users/{user_id}"`

4. **Extract Path Parameters**
   - Parse `{param_name}` or `{param_name:type}` from path
   - Map types: `int` → integer, `str` → string, `float` → number

5. **Get Function Details**
   - Function name for operation_id
   - Source file and line number

### Path Parameter Syntax

FastAPI supports optional type hints in path:

| FastAPI | OpenAPI | Type |
|---------|---------|------|
| `{user_id}` | `{user_id}` | string |
| `{user_id:int}` | `{user_id}` | integer |
| `{price:float}` | `{price}` | number |
| `{name:str}` | `{name}` | string |
| `{path:path}` | `{path}` | string |

### Example Extraction

**Input:**
```python
@app.get("/users/{user_id}")
async def get_user(user_id: int, token: str = Header(...)):
    return {"id": user_id}
```

**Extracted Route:**
```json
{
  "path": "/users/{user_id}",
  "method": "GET",
  "handler_name": "get_user",
  "parameters": [
    {
      "name": "user_id",
      "location": "path",
      "type": "string",
      "required": true
    }
  ]
}
```

**Generated OpenAPI:**
```yaml
/users/{user_id}:
  get:
    tags: [fastapi]
    operationId: get_user
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: string
```

## Features

### ✅ Supported

- **HTTP Method Decorators**: `@app.get()`, `@app.post()`, etc.
- **Path Parameters**: `{param}` with optional type hints
- **APIRouter**: Routes defined on router instances
- **Async/Sync Functions**: Both `async def` and `def`
- **Path Normalization**: Already OpenAPI format

### ⚠️ Partial Support

- **APIRouter Prefix**: Doesn't extract `prefix="/api"` from router
- **Query Parameters**: Not extracted from function signature
- **Request Body**: Not extracted from Pydantic models
- **Response Models**: Not extracted from `response_model=`
- **Dependencies**: Not extracted from `Depends()`

### ❌ Not Supported

- **Path Operations** from `APIRouter.include_router()`
- **Pydantic Model Schemas**: Type definitions not extracted
- **Validation Rules**: From `Query()`, `Path()`, etc.
- **Security Schemes**: From `Depends()` decorators

## APIRouter Handling

### Current Behavior

```python
router = APIRouter(prefix="/api")

@router.get("/users")
def get_users():
    pass

app.include_router(router)
```

**Extracted:** `/users` (missing `/api` prefix)

### Workaround

Include prefix in path:
```python
@router.get("/api/users")
def get_users():
    pass
```

## Code Coverage

**88%** - High coverage on core extraction logic

## Testing

Run tests:
```bash
pytest tests/unit/test_fastapi_extractor.py -v
```

Sample fixture: `tests/fixtures/python/sample_fastapi.py`

## Limitations

1. **Type Inference**: Only extracts types from path syntax, not function annotations
2. **Router Composition**: Doesn't follow `include_router()` calls
3. **Schema Extraction**: Doesn't parse Pydantic models for request/response schemas
4. **Query/Header Params**: Requires function signature analysis (not implemented)

## Future Enhancements

1. Extract `APIRouter(prefix=...)` for proper path composition
2. Parse function signatures for query/header parameters
3. Extract Pydantic model schemas for request/response bodies
4. Detect `Depends()` for security schemes
5. Parse docstrings for operation descriptions
