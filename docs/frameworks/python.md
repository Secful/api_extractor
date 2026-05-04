# Python Framework Support

API Extractor supports three major Python web frameworks with comprehensive route extraction capabilities.

## Supported Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **FastAPI** | All versions | `requirements.txt`, `pyproject.toml`, imports | ✅ FastAPI Full-Stack Template |
| **Flask** | All versions | `requirements.txt`, `pyproject.toml`, imports | ✅ Flask RealWorld (DataDog) |
| **Django REST Framework** | 3.x+ | `requirements.txt`, `pyproject.toml`, imports | ✅ Django REST Tutorial |

## Key Features

- Route decorator detection (`@app.route`, `@router.get`, `@api_view`)
- Blueprint and APIRouter support
- ViewSet and generic views (Django REST)
- Path parameters and query parameters
- Request/response type hints (FastAPI, Flask-RESTX)

## FastAPI

Python framework with type hints and automatic OpenAPI generation.

### Example

```python
from fastapi import FastAPI, APIRouter

router = APIRouter(prefix="/api/users")

@router.get("/")
async def get_users() -> List[User]:
    return await user_service.find_all()

@router.get("/{user_id}")
async def get_user(user_id: int) -> User:
    return await user_service.find_one(user_id)

@router.post("/")
async def create_user(user: UserCreate) -> User:
    return await user_service.create(user)
```

**Detection:** `fastapi` in requirements/pyproject.toml
**Validated on:** FastAPI Full-Stack Template

### Supported Features

- ✅ Route decorators (`@app.get`, `@router.post`)
- ✅ APIRouter with prefix support
- ✅ Path parameters with type hints
- ✅ Query parameters with type hints
- ✅ Request body with Pydantic models
- ✅ Response type annotations

## Flask

Lightweight WSGI web framework with flexible routing patterns.

### Example

```python
from flask import Flask, Blueprint

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/users')
def get_users():
    return {'users': []}

@api.route('/users/<int:user_id>')
def get_user(user_id):
    return {'id': user_id}

@api.route('/users', methods=['POST'])
def create_user():
    return {'user': request.json}
```

**Detection:** `flask` in requirements/pyproject.toml
**Validated on:** Flask RealWorld (DataDog)

### Supported Features

- ✅ `@app.route()` decorator
- ✅ Blueprint support with `url_prefix`
- ✅ Path converters (`<int:id>`, `<string:name>`)
- ✅ Method-specific decorators (`@app.get`, `@app.post`)
- ✅ Multiple HTTP methods per route

## Django REST Framework

Powerful toolkit for building Web APIs with Django.

### Example

```python
from rest_framework import viewsets
from rest_framework.decorators import api_view, action

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'activated'})

@api_view(['GET', 'POST'])
def user_list(request):
    if request.method == 'GET':
        users = User.objects.all()
        return Response(users)
```

**Detection:** `djangorestframework` in requirements/pyproject.toml
**Validated on:** Django REST Tutorial

### Supported Features

- ✅ ViewSet and ModelViewSet
- ✅ APIView class-based views
- ✅ `@api_view` decorator
- ✅ `@action` decorator for custom endpoints
- ✅ URL pattern detection
- ✅ Router registration

## Usage

### Basic Extraction

```bash
# Detect and extract from Python project
api-extractor extract /path/to/python/project
```

### Framework-Specific Extraction

```bash
# FastAPI project
api-extractor extract /path/to/fastapi-app --output fastapi-spec.json

# Flask project
api-extractor extract /path/to/flask-app --output flask-api.yaml --format yaml

# Django REST project
api-extractor extract /path/to/django-app --output django-api.json
```

## Pattern Support

### Path Parameters

All Python frameworks support path parameters with normalization:

- **Flask**: `/users/<int:id>` → `/users/{id}`
- **FastAPI**: `/users/{user_id}` → `/users/{user_id}`
- **Django**: `path('<int:pk>/activate/', ...)` → `/{pk}/activate/`

### Router/Blueprint Mounting

- **FastAPI**: `app.include_router(router, prefix='/api')` - Handles router inclusion
- **Flask**: `Blueprint('api', __name__, url_prefix='/api')` - Tracks blueprint prefixes
- **Django REST**: `router.register(r'users', UserViewSet)` - URL pattern composition

## Validation Library Support

API Extractor can extract validation schemas from common Python libraries:

| Framework | Validation Libraries |
|-----------|---------------------|
| FastAPI | Pydantic (built-in) |
| Flask | Marshmallow, Flask-RESTX, flask-smorest |
| Django REST | DRF Serializers |

## Known Limitations

1. **Dynamic routes**: Routes defined programmatically (e.g., generated in loops, loaded from config) cannot be extracted
2. **Cross-file resolution**: Works best with single-file or same-directory patterns
3. **Complex URL patterns**: Regex-based Django URL patterns are not fully supported

## Troubleshooting

### No endpoints found

- Ensure you're running the extractor on the source directory (not `__pycache__` or build artifacts)
- Check that the framework is correctly detected with `--verbose` flag
- Verify that route decorators are using standard patterns

### Routes missing from output

- **Flask**: Check that Blueprint mounting (`app.register_blueprint()`) is present in the same file
- **FastAPI**: Verify that routers are included with `app.include_router()`
- **Django REST**: Ensure ViewSets are registered with routers

### Path parameters not extracted

- Check that parameter syntax matches the framework:
  - Flask: `<type:paramName>` or `<paramName>`
  - FastAPI: `{paramName}`
  - Django: `<int:pk>` or similar converters

## Docker Image Extraction

When extracting from Docker images:

| Status | Notes |
|--------|-------|
| ✅ **No preprocessing required** | Python source files (.py) are deployed as-is in Docker images |

Python is the easiest language for extraction from Docker containers since source code is typically included in the image without compilation.
