# Django REST Framework Extractor

Extracts REST API routes from Django REST Framework ViewSets and views.

## How It Works

### Detection Pattern

Django REST uses class-based views:

```python
from rest_framework import viewsets
from rest_framework.decorators import api_view, action
from rest_framework.views import APIView

class UserViewSet(viewsets.ModelViewSet):
    def list(self, request):
        return Response([])

    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        return Response({})

@api_view(['GET', 'POST'])
def order_list(request):
    return Response([])
```

### Tree-sitter AST Structure

**ViewSet Pattern:**
```
class_declaration
  name: identifier
  superclasses: argument_list
    attribute (contains "ViewSet")
  body: block
    function_definition (method)
```

**Function-Based View:**
```
decorated_definition
  decorator (@api_view)
    call
      arguments: list (methods)
  function_definition
```

### Extraction Process

#### ViewSet Routes

1. **Detect ViewSet Classes**
   - Check if class inherits from `ViewSet`, `ModelViewSet`, `ReadOnlyModelViewSet`
   - Base class name contains "ViewSet"

2. **Generate Base Path**
   - From class name: `UserViewSet` → `/users`
   - Rules:
     - Remove "ViewSet" suffix
     - Convert CamelCase to snake_case
     - Pluralize (add 's' if not present)

3. **Map Standard Methods**
   - `list()` → GET `/users`
   - `retrieve()` → GET `/users/{pk}`
   - `create()` → POST `/users`
   - `update()` → PUT `/users/{pk}`
   - `partial_update()` → PATCH `/users/{pk}`
   - `destroy()` → DELETE `/users/{pk}`

4. **Handle Custom Actions**
   - Parse `@action` decorator for:
     - `detail=True` → `/users/{pk}/action-name`
     - `detail=False` → `/users/action-name`
     - `methods=['POST']` → HTTP methods

#### APIView Routes

1. **Detect APIView Classes**
   - Check if class inherits from `APIView`

2. **Generate Base Path**
   - From class name: `ProductAPIView` → `/products`

3. **Map HTTP Methods**
   - `get()` → GET
   - `post()` → POST
   - `put()` → PUT
   - `patch()` → PATCH
   - `delete()` → DELETE

#### Function-Based Views

1. **Detect @api_view Decorator**
   - Parse decorator arguments for methods list

2. **Generate Path**
   - From function name: `order_list` → `/order-list`
   - Convert underscores to hyphens

### Path Generation Examples

| Class Name | Generated Path |
|------------|----------------|
| `UserViewSet` | `/users` |
| `ItemViewSet` | `/items` |
| `ProductAPIView` | `/products` |
| `OrderAPIView` | `/orders` |

### ViewSet Method Mapping

| Method | HTTP | Path | Description |
|--------|------|------|-------------|
| `list()` | GET | `/resource` | List all |
| `retrieve()` | GET | `/resource/{pk}` | Get one |
| `create()` | POST | `/resource` | Create |
| `update()` | PUT | `/resource/{pk}` | Full update |
| `partial_update()` | PATCH | `/resource/{pk}` | Partial update |
| `destroy()` | DELETE | `/resource/{pk}` | Delete |

### Example Extraction

**Input:**
```python
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer

    def list(self, request):
        return Response([])

    def retrieve(self, request, pk=None):
        return Response({"id": pk})

    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        return Response({"status": "password set"})
```

**Extracted Routes:**
```json
[
  {
    "path": "/users",
    "method": "GET",
    "handler_name": "UserViewSet.list"
  },
  {
    "path": "/users/{pk}",
    "method": "GET",
    "handler_name": "UserViewSet.retrieve",
    "parameters": [
      {"name": "pk", "in": "path", "type": "integer"}
    ]
  },
  {
    "path": "/users/{pk}/set_password",
    "method": "POST",
    "handler_name": "set_password"
  }
]
```

## Features

### ✅ Supported

- **ViewSet Auto-Routes**: Automatic CRUD route generation
- **ModelViewSet**: Full CRUD (list, retrieve, create, update, destroy)
- **ReadOnlyModelViewSet**: Read-only (list, retrieve)
- **APIView**: HTTP method handlers
- **@api_view**: Function-based views with method list
- **Path Generation**: Auto-generate paths from class names
- **pk Parameter**: Automatic for detail routes

### ⚠️ Partial Support

- **@action Decorator**: Basic support (some edge cases)
- **Custom Actions**: Simple detail/list actions
- **Serializer Classes**: Detected but not schema-extracted

### ❌ Not Supported

- **URL Patterns**: Doesn't parse `urlpatterns` from `urls.py`
- **Router Registration**: Doesn't follow `DefaultRouter()`
- **ViewSet Mixins**: Custom mixins not analyzed
- **Permission Classes**: Not extracted
- **Filter/Pagination**: Not detected
- **Nested Routers**: From `drf-nested-routers`

## Custom Actions

### @action Decorator

```python
class UserViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        return Response({})

    @action(detail=False, methods=['get'])
    def recent(self, request):
        return Response([])
```

**Extracted:**
- POST `/users/{pk}/set_password` (detail=True)
- GET `/users/recent` (detail=False)

## Path Parameter Detection

Django REST uses `pk` by default:

```python
def retrieve(self, request, pk=None):
    pass
```

**Parameter:**
- Name: `pk`
- Type: `integer` (Django convention)
- Required: `true`

## Code Coverage

**67%** - Good coverage on ViewSet extraction

## Testing

Run tests:
```bash
pytest tests/unit/test_django_extractor.py -v
```

Sample fixture: `tests/fixtures/python/sample_django.py`

## Limitations

1. **URL Configuration**: Doesn't parse `urls.py` for actual routes
2. **Router Registration**: Can't follow `router.register()`
3. **Custom Routers**: Non-standard routers not supported
4. **Serializer Schemas**: Doesn't extract field definitions
5. **Permission/Auth**: Not detected
6. **Nested Resources**: Nested routes not supported

## URL Pattern Resolution

Django REST routes are typically defined in `urls.py`:

```python
# urls.py
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'products', ProductViewSet, basename='product')
```

The extractor **cannot parse this** because it only analyzes ViewSet files, not URL configuration.

### Workaround

Path generation is automatic from class names:
- `UserViewSet` → `/users`
- `ProductViewSet` → `/products`

If your actual URL differs, you'll need to:
1. Use descriptive ViewSet names
2. Or manually adjust the generated OpenAPI spec

## Future Enhancements

1. Parse `urls.py` for actual route registration
2. Follow `router.register()` calls
3. Extract serializer schemas for request/response bodies
4. Detect permission classes
5. Support nested routers (drf-nested-routers)
6. Parse docstrings for operation descriptions
