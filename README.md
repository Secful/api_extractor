# API Extractor

Automatically extract REST API definitions from source code and generate OpenAPI specifications.

## Features

- **Automatic Framework Detection**: Detects web frameworks in your codebase
- **Multi-Framework Support**: Supports Python (FastAPI, Flask, Django REST) and JavaScript/TypeScript (Express, NestJS, Fastify)
- **OpenAPI 3.1 Output**: Generates standard OpenAPI specifications in JSON or YAML
- **S3 Support**: Can analyze code from S3 buckets
- **Tree-sitter Based**: Uses Tree-sitter Query Language for accurate AST parsing and pattern matching
- **Production Validated**: Tested against real-world projects including truthy (NestJS) and Postman tutorial patterns

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

### Basic Usage

Extract API definitions from a local directory:

```bash
api-extractor extract /path/to/project
```

### Specify Output Format

Generate YAML output:

```bash
api-extractor extract /path/to/project --output api-spec.yaml --format yaml
```

### Manual Framework Specification

Bypass automatic detection:

```bash
api-extractor extract /path/to/project --framework flask --framework express
```

### S3 Source

Extract from S3:

```bash
api-extractor extract s3://my-bucket/code/ --s3 --output openapi.json
```

### Verbose Output

Show detailed extraction progress:

```bash
api-extractor extract /path/to/project --verbose
```

## CLI Reference

### Command: `extract`

Extract API routes from source code and generate OpenAPI specification.

```bash
api-extractor extract <PATH> [OPTIONS]
```

### Arguments

- `PATH` - Path to codebase (local directory or S3 URI with `--s3` flag)

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | path | `openapi.json` | Output file path |
| `--format` | `-f` | choice | `json` | Output format (`json` or `yaml`) |
| `--framework` | `-w` | choice | auto-detect | Framework(s) to extract (can specify multiple times) |
| `--s3` | - | flag | false | Treat path as S3 URI |
| `--verbose` | `-v` | flag | false | Show detailed extraction progress |
| `--title` | - | string | `Extracted API` | API title in OpenAPI spec |
| `--version` | - | string | `1.0.0` | API version in OpenAPI spec |
| `--help` | `-h` | flag | - | Show help message |

### Supported Frameworks

Use with `--framework` option:
- `fastapi` - FastAPI (Python)
- `flask` - Flask (Python)
- `django_rest` - Django REST Framework (Python)
- `express` - Express (JavaScript/Node.js)
- `nestjs` - NestJS (TypeScript/JavaScript)
- `fastify` - Fastify (JavaScript/Node.js)

### Exit Codes

- `0` - Success
- `1` - Framework detection failed (no frameworks found)
- `2` - Invalid input (path not found, invalid S3 URI, etc.)
- `3` - Extraction error (parse failures, no endpoints found, etc.)

### Examples

**Basic extraction with automatic detection:**
```bash
api-extractor extract /path/to/project
```

**Multiple frameworks:**
```bash
api-extractor extract . --framework flask --framework express
```

**Custom output with metadata:**
```bash
api-extractor extract . \
  --output my-api.yaml \
  --format yaml \
  --title "My API" \
  --version "2.0.0" \
  --verbose
```

**S3 source:**
```bash
api-extractor extract s3://my-bucket/code/ \
  --s3 \
  --output openapi.json
```

**Specific framework (bypass detection):**
```bash
api-extractor extract . --framework fastapi
```

### Environment Variables

None currently supported. All configuration is via CLI arguments.

## Supported Frameworks

### Python
- ✅ **FastAPI**: Route decorators (`@app.get`, `@router.post`), APIRouter, path parameters, type hints
- ✅ **Flask**: Blueprints, `@app.route()`, method-specific decorators (`@app.get`), path converters (`<int:id>`)
- ✅ **Django REST Framework**: ViewSets, APIView, `@api_view` decorator, URL patterns

### JavaScript/TypeScript
- ✅ **Express**: Router mounting (`app.use()`), middleware chains, path parameters (`:param`), route methods
- ✅ **NestJS**: Controllers (`@Controller()`), HTTP decorators (`@Get()`, `@Post()`), multiple decorators, path composition, versioning
- ✅ **Fastify**: Route registration (`fastify.get()`), path parameters (`:param`), schema validation

## Pattern Support

### Path Parameters
All frameworks support extracting path parameters and normalizing them to OpenAPI format:
- Express/NestJS/Fastify: `/users/:id` → `/users/{id}`
- Flask: `/users/<int:id>` → `/users/{id}`
- FastAPI: `/users/{user_id}` → `/users/{user_id}`

### Router/Blueprint Mounting
- **Express**: `app.use('/api', router)` - Correctly applies prefix to all routes
- **Flask**: `Blueprint('api', __name__, url_prefix='/api')` - Tracks blueprint prefixes
- **FastAPI**: `app.include_router(router, prefix='/api')` - Handles router inclusion
- **NestJS**: `@Controller('users')` - Path composition with controller decorators

### Middleware & Guards
- Express: Detects middleware in route chains (e.g., `app.get('/path', auth, handler)`)
- NestJS: Recognizes guards (`@UseGuards()`) and other decorators without treating them as routes

## Known Limitations

1. **Cross-file module resolution**: Extractors work best with single-file or same-directory patterns. Express routers defined in separate files and imported via `require()` may not have their mount paths correctly applied.

2. **Dynamic routes**: Routes defined programmatically (e.g., generated in loops, loaded from config) cannot be extracted.

3. **Type inference**: For untyped JavaScript code, parameter types default to `string`.

4. **Complex path patterns**: Regex-based routes or custom path matchers are not supported.

## Example

Given a FastAPI application:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id}
```

Running the extractor:

```bash
api-extractor extract . --verbose
```

Output:

```
Detecting frameworks...
  ✓ Found: fastapi
Extracting routes...
  fastapi: 1 endpoints found
Generating OpenAPI spec...
✓ Written to openapi.json
```

Generated OpenAPI spec (openapi.json):

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Extracted API",
    "version": "1.0.0"
  },
  "paths": {
    "/users/{user_id}": {
      "get": {
        "tags": ["fastapi"],
        "parameters": [
          {
            "name": "user_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "integer"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  }
}
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Running Tests with Coverage

```bash
pytest tests/ -v --cov=api_extractor --cov-report=term-missing
```

### Test Statistics

- **Total Tests**: 40 (100% passing)
- **Coverage**: 57% overall
  - Framework extractors: 88-90%
  - Core parser: 64%
  - Base extractor: 83%

### Test Breakdown by Framework

| Framework | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| FastAPI | 4 | 90% | ✅ Passing |
| Flask | 5 | 89% | ✅ Passing |
| Django REST | 4 | 89% | ✅ Passing |
| Express | 18 | 89% | ✅ Passing |
| NestJS | 5 | 88% | ✅ Passing |
| Fastify | 4 | 89% | ✅ Passing |

## Validation

The extractors have been validated against real-world codebases:

### Express Validation
Tested against patterns from **Postman's "How to Create a REST API with Node.js and Express" tutorial**:
- ✅ Basic CRUD operations
- ✅ Router mounting with `app.use()`
- ✅ Multiple routers with different prefixes
- ✅ Middleware in routes
- ✅ Nested path parameters
- ✅ API versioning patterns
- ✅ REST API best practices
- ✅ Complex path patterns

### NestJS Validation
Tested against **truthy** (https://github.com/gobeam/truthy), a production NestJS application:
- ✅ 39 endpoints successfully extracted
- ✅ Controller path prefixes
- ✅ HTTP method decorators with and without paths
- ✅ Multiple decorators per method (`@Get()` + `@ApiQuery()`)
- ✅ Path parameter extraction and normalization
- ✅ Guard and interceptor decorators (correctly ignored)
- ✅ Class-level decorators

## Architecture

### Project Structure

```
api_extractor/
├── core/
│   ├── models.py           # Data models
│   ├── detector.py         # Framework detection
│   ├── parser.py           # Tree-sitter wrapper
│   └── base_extractor.py  # Base extractor class
├── extractors/
│   ├── python/
│   │   ├── fastapi.py     # FastAPI extractor
│   │   ├── flask.py       # Flask extractor
│   │   └── django_rest.py # Django REST extractor
│   └── javascript/
│       ├── express.py     # Express extractor
│       ├── nestjs.py      # NestJS extractor
│       └── fastify.py     # Fastify extractor
├── input_handlers/
│   ├── local.py           # Local filesystem handler
│   └── s3.py              # S3 handler
├── openapi/
│   ├── models.py          # OpenAPI models
│   └── builder.py         # OpenAPI spec builder
└── cli.py                 # CLI interface
```

### Implementation Approach

All extractors use **Tree-sitter Query Language** for pattern matching:

1. **Parse source code into AST**: Tree-sitter parses Python, JavaScript, and TypeScript files into abstract syntax trees

2. **Query for patterns**: Framework-specific queries written in S-expression syntax match route definitions
   ```scheme
   ; Example: Flask route decorator
   (decorated_definition
     (decorator
       (call
         function: (attribute
           object: (identifier) @obj_name
           attribute: (identifier) @method_name)
         arguments: (argument_list) @args))
     definition: (function_definition
       name: (identifier) @func_name))
   ```

3. **Extract route information**: Captured nodes are processed to extract:
   - HTTP methods (GET, POST, etc.)
   - Path patterns with parameters
   - Handler function names
   - Path prefixes from routers/blueprints/controllers

4. **Normalize to OpenAPI**: Routes are normalized to OpenAPI 3.1 format with proper parameter schemas

This declarative approach replaced 1,050+ lines of imperative tree traversal code, improving maintainability and accuracy.

## Contributing

Contributions are welcome! To add support for a new framework:

1. **Create a new extractor** in `api_extractor/extractors/python/` or `api_extractor/extractors/javascript/`
2. **Extend `BaseExtractor`** and implement required methods:
   - `get_file_extensions()` - Return list of file extensions to process
   - `extract_routes_from_file()` - Use Tree-sitter queries to extract routes
   - `_extract_path_parameters()` - Parse path parameters
   - `_normalize_path()` - Convert to OpenAPI format
3. **Write Tree-sitter queries** to match framework-specific patterns:
   - Study the framework's AST structure using Tree-sitter playground
   - Write S-expression queries to capture route decorators/functions
   - Extract HTTP methods, paths, and parameters from captured nodes
4. **Add test fixtures** in `tests/fixtures/` with sample code
5. **Create unit tests** in `tests/unit/` covering:
   - Basic route extraction
   - Path parameter handling
   - Router/Blueprint mounting
   - Edge cases (empty decorators, multiple decorators, etc.)
6. **Validate against real projects** to ensure production readiness
7. **Update CLI** in `cli.py` to register the new extractor

### Example: Adding a New Framework

See existing extractors like `express.py` or `nestjs.py` for reference implementation using Tree-sitter Query Language.

## Troubleshooting

### No endpoints found
- Ensure you're running the extractor on the correct directory (source code, not build artifacts)
- Check that the framework is correctly detected with `--verbose` flag
- Try manually specifying the framework with `--framework`

### Routes missing from output
- For Express: Ensure routers are defined and mounted in the same file
- For Flask: Check that Blueprint mounting (`app.register_blueprint()`) is present
- For NestJS: Verify controllers are decorated with `@Controller()` and methods with HTTP decorators

### Path parameters not extracted
- Check that parameter syntax matches the framework:
  - Express/NestJS/Fastify: `:paramName`
  - Flask: `<type:paramName>` or `<paramName>`
  - FastAPI: `{paramName}`

### Performance issues
- The extractor processes all matching files in the directory
- For large codebases, consider extracting from specific subdirectories
- Use `.gitignore` patterns are not currently supported - manually exclude `node_modules`, `venv`, etc.

## License

MIT License
