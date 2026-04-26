# Flask Extractor

Extracts REST API routes from Flask applications including full Blueprint support.

## How It Works

### Detection Pattern

Flask routes use the `@app.route()` decorator or method shortcuts:

```python
from flask import Flask, Blueprint

app = Flask(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

@app.route('/users/<int:user_id>', methods=['GET', 'POST'])
def get_user(user_id):
    return {"id": user_id}

@api_bp.get('/products')
def list_products():
    return []
```

### Tree-sitter AST Structure

The extractor uses a two-pass approach:

**Pass 1: Extract Blueprints**
```
assignment
  left: identifier (blueprint_var)
  right: call
    function: identifier ("Blueprint")
    arguments
      keyword_argument
        name: "url_prefix"
        value: string
```

**Pass 2: Extract Routes**
```
decorated_definition
  decorator
    call
      function: attribute
        object: identifier (app or blueprint_var)
        attribute: identifier ("route", "get", "post", etc.)
      arguments
        string (path)
        keyword_argument (methods)
  function_definition
```

### Extraction Process

#### Phase 1: Blueprint Discovery

1. **Find Blueprint Instantiation**
   - Look for `Blueprint(name, import_name, url_prefix='/api')`
   - Store mapping: `{blueprint_var: url_prefix}`

2. **Track Blueprint Variables**
   - Example: `api_bp = Blueprint(...)` → `api_bp` maps to `/api`

#### Phase 2: Route Extraction

1. **Find Decorated Functions**
   - `@app.route()` - App-level routes
   - `@blueprint.route()` - Blueprint routes
   - `@app.get()`, `@app.post()` - Method shortcuts

2. **Extract HTTP Methods**
   - From `methods=['GET', 'POST']` argument
   - From decorator name: `@app.get()` → GET
   - Default: GET if not specified

3. **Extract Path**
   - Parse Flask parameter syntax: `<int:id>`, `<string:name>`
   - Combine with Blueprint prefix if applicable

4. **Compose Full Path**
   - Blueprint prefix + route path
   - Example: `/api` + `/users` → `/api/users`

### Path Parameter Syntax

Flask uses converter syntax:

| Flask | OpenAPI | Type |
|-------|---------|------|
| `<user_id>` | `{user_id}` | string |
| `<int:user_id>` | `{user_id}` | integer |
| `<float:price>` | `{price}` | number |
| `<string:name>` | `{name}` | string |
| `<path:filepath>` | `{filepath}` | string |
| `<uuid:id>` | `{id}` | string |

### Example Extraction

**Input:**
```python
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/users/<int:user_id>', methods=['GET', 'PUT'])
def user_detail(user_id):
    return {"id": user_id}
```

**Extracted Route:**
```json
{
  "path": "/api/v1/users/{user_id}",
  "methods": ["GET", "PUT"],
  "handler_name": "user_detail",
  "parameters": [
    {
      "name": "user_id",
      "location": "path",
      "type": "integer",
      "required": true
    }
  ]
}
```

**Generated OpenAPI:**
```yaml
/api/v1/users/{user_id}:
  get:
    tags: [flask]
    operationId: user_detail
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
  put:
    tags: [flask]
    operationId: user_detail
    parameters:
      - name: user_id
        in: path
        required: true
        schema:
          type: integer
```

## Features

### ✅ Supported

- **Blueprint url_prefix**: Full composition with route paths
- **@app.route()**: Standard route decorator
- **Method Shortcuts**: `@app.get()`, `@app.post()`, etc.
- **HTTP Methods**: Multiple methods per route via `methods=[]`
- **Path Converters**: All Flask converters mapped to types
- **Multiple Blueprints**: Tracks all blueprints in file

### ⚠️ Partial Support

- **Query Parameters**: Not extracted from `request.args`
- **Request Body**: Not extracted from `request.json`
- **Nested Blueprints**: Only single-level prefix supported

### ❌ Not Supported

- **Dynamic Routes**: From `add_url_rule()`
- **MethodView Classes**: Class-based views not parsed
- **Blueprint Registration**: Doesn't follow `app.register_blueprint()`
- **URL Building**: Doesn't parse `url_for()` calls

## Blueprint Composition

### Standard Blueprint

```python
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/users')
def users():
    pass

app.register_blueprint(api_bp)
```

**Extracted:** `/api/users` ✅

### Nested Blueprints

```python
v1_bp = Blueprint('v1', __name__, url_prefix='/v1')
api_bp = Blueprint('api', __name__, url_prefix='/api')

# api_bp registered under v1_bp
v1_bp.register_blueprint(api_bp)
```

**Extracted:** `/api/users` (missing `/v1` prefix) ⚠️

## Method Detection

### Explicit Methods List

```python
@app.route('/users', methods=['GET', 'POST', 'PUT'])
def users():
    pass
```

**Result:** 3 separate endpoints (GET, POST, PUT)

### Method Shortcuts

```python
@app.get('/users')
def get_users():
    pass

@app.post('/users')
def create_user():
    pass
```

**Result:** 2 separate endpoints

### Default Method

```python
@app.route('/users')  # No methods specified
def users():
    pass
```

**Result:** GET endpoint (Flask default)

## Code Coverage

**89%** - Highest coverage among all extractors

## Testing

Run tests:
```bash
pytest tests/unit/test_flask_extractor.py -v
```

Sample fixture: `tests/fixtures/python/sample_flask.py`

## Limitations

1. **Nested Blueprints**: Only single-level prefix composition
2. **Class-Based Views**: MethodView not supported
3. **Dynamic Routes**: `add_url_rule()` not detected
4. **Request Context**: Can't analyze `request.args`, `request.json`
5. **Blueprint Options**: Only extracts `url_prefix`, not subdomain, etc.

## Future Enhancements

1. Nested Blueprint composition (multi-level prefixes)
2. MethodView class-based views
3. Query parameter extraction from `request.args` usage
4. Request body detection from `request.json` usage
5. Parse docstrings for operation descriptions
