# Real-World Fixtures

This directory contains real-world application repositories added as git submodules for comprehensive integration testing of the API extractors.

## Overview

Real-world fixtures ensure that extractors work correctly with production-quality codebases that use actual patterns, project structures, and conventions found in the wild.

## Fixture Repositories

### JavaScript/TypeScript Frameworks

#### 1. Fastify Demo (`fastify-demo`)
- **Repository**: https://github.com/fastify/demo
- **Description**: Official Fastify demo application showcasing production best practices
- **Framework Version**: Fastify with TypeScript
- **Application Type**: Task management API with authentication and file uploads
- **Key Features**:
  - Plugin-based architecture
  - JWT authentication
  - File upload/download
  - CSV export
  - Role-based access control (RBAC)
  - Swagger/OpenAPI documentation

**Expected Endpoints** (14+ total):
- `GET /` - Home/welcome
- `POST /login` - Authentication
- `PUT /update-password` - User password update
- `GET /` - List tasks (with pagination)
- `POST /` - Create task
- `GET /{id}` - Get task by ID
- `PATCH /{id}` - Update task
- `DELETE /{id}` - Delete task (admin)
- `POST /{id}/assign` - Assign task to user (moderator)
- `POST /{id}/upload` - Upload file to task
- `GET /{filename}/image` - Get task image
- `DELETE /{filename}/image` - Delete task image
- `GET /download/csv` - Export tasks as CSV

#### 2. Express Examples (`express-examples`)
- **Repository**: https://github.com/expressjs/express (examples directory)
- **Description**: Official Express.js examples covering various patterns
- **Framework Version**: Express.js (latest)
- **Application Type**: Collection of focused examples
- **Key Features**:
  - Various routing patterns
  - Middleware examples
  - REST API examples
  - MVC structure examples

**Expected Patterns**:
- Basic route registration: `app.get()`, `app.post()`, etc.
- Router usage: `router.get()`, `router.post()`, etc.
- Parameter handling: `:id`, `:userId`, etc.

#### 3. NestJS RealWorld (`nestjs-realworld`)
- **Repository**: https://github.com/lujakob/nestjs-realworld-example-app
- **Description**: Production-ready NestJS backend implementing RealWorld API spec
- **Framework Version**: NestJS with TypeScript
- **Application Type**: Blogging platform API (Conduit)
- **Key Features**:
  - Decorator-based routing (`@Get()`, `@Post()`, etc.)
  - Module organization
  - Dependency injection
  - JWT authentication
  - Swagger/OpenAPI

**Expected Endpoints**:
- User authentication and registration
- Article CRUD operations
- Comments on articles
- Favoriting articles
- Following users
- User profiles
- Tags

#### 4. Cal.com (`cal.com`)
- **Repository**: https://github.com/calcom/cal.com
- **Description**: Production calendar scheduling platform with Next.js API routes
- **Framework Version**: Next.js 14+ (App Router & Pages Router)
- **Application Type**: Enterprise calendar and scheduling platform
- **Key Features**:
  - Both App Router and Pages Router patterns
  - OAuth integrations
  - Webhook handling
  - Payment processing (Stripe)
  - CSRF protection

**Expected Endpoints** (11+ detected):
- `GET /api/csrf` - CSRF token endpoint
- `GET /api/ip` - IP detection
- `GET /api/stripe/webhook` - Stripe webhook handler
- `GET /api/video/recording` - Video recording endpoint
- `GET /api/integrations/stripepayment/webhook` - Payment webhook

**Clone Command**:
```bash
git clone --depth 1 https://github.com/calcom/cal.com.git tests/fixtures/real-world/cal.com
```

#### 5. Dub (`dub`)
- **Repository**: https://github.com/dubinc/dub
- **Description**: Production link management platform built with Next.js App Router
- **Framework Version**: Next.js 14+ (primarily App Router)
- **Application Type**: Link shortening and analytics SaaS platform
- **Key Features**:
  - App Router architecture (route.ts files)
  - Link management API
  - Analytics endpoints
  - OAuth 2.0 integration
  - AI embeddings
  - Webhook callbacks

**Expected Endpoints** (31+ detected):
- `GET /api` - API root
- `POST /api/ai/sync-embeddings` - AI embeddings sync
- `GET /api/analytics/dashboard` - Analytics data
- `POST /api/auth/reset-password` - Password reset
- `GET /api/callback/bitly` - OAuth callback
- `GET /api/links/exists` - Link existence check
- `GET /api/links/metatags` - Link metadata
- `POST /api/oauth/token` - OAuth token endpoint
- `GET /api/qr` - QR code generation

**Clone Command**:
```bash
git clone --depth 1 https://github.com/dubinc/dub.git tests/fixtures/real-world/dub
```

**Note**: These repositories are large and are added to `.gitignore`. Clone them locally for testing:
```bash
cd tests/fixtures/real-world
git clone --depth 1 https://github.com/calcom/cal.com.git
git clone --depth 1 https://github.com/dubinc/dub.git
```

### Python Frameworks

#### 4. FastAPI Full Stack (`fastapi-fullstack`)
- **Repository**: https://github.com/tiangolo/full-stack-fastapi-template
- **Description**: Official full-stack template from FastAPI creator
- **Framework Version**: FastAPI (latest)
- **Application Type**: Full-stack app with backend API
- **Key Features**:
  - APIRouter with prefixes
  - Pydantic models
  - SQLModel ORM
  - JWT authentication
  - Automatic OpenAPI docs

**Expected Endpoints**:
- `/api/v1/login/` - Login endpoints
- `/api/v1/users/` - User CRUD operations
- `/api/v1/items/` - Item CRUD operations
- `/api/v1/utils/` - Utility endpoints

**Backend Structure**: `backend/app/api/routes/`

#### 5. Django REST Tutorial (`django-rest-tutorial`)
- **Repository**: https://github.com/encode/rest-framework-tutorial
- **Description**: Official Django REST Framework tutorial
- **Framework Version**: Django REST Framework (latest)
- **Application Type**: Tutorial progression (pastebin-like API)
- **Key Features**:
  - ViewSets with ModelViewSet
  - Generic views and APIView
  - Serializers
  - Authentication
  - Permissions

**Expected Patterns**:
- ViewSet-based endpoints (list, create, retrieve, update, destroy)
- Custom actions with `@action` decorator
- Function-based views with `@api_view`

#### 6. Flask RealWorld (`flask-realworld`)
- **Repository**: https://github.com/DataDog/flask-realworld-example-app
- **Description**: Flask implementation of RealWorld API (actively maintained by DataDog)
- **Framework Version**: Flask 3.x
- **Application Type**: Blogging platform API (Conduit)
- **Key Features**:
  - Blueprint-based organization
  - SQLAlchemy ORM
  - Flask-JWT-Extended
  - RESTful API structure
  - Modular domain structure (articles, profiles, users)

**Expected Endpoints**:
- User authentication and registration
- Article CRUD operations
- Comments management
- Article favoriting
- User following
- Profile management
- Tag listing

**Backend Structure**: Modular with blueprints for each domain

## Managing Submodules

### Initial Setup

After cloning the repository, initialize submodules:

```bash
git submodule update --init --recursive
```

### Updating Submodules

To update all submodules to their latest versions:

```bash
git submodule update --remote
```

To update a specific submodule:

```bash
git submodule update --remote tests/fixtures/real-world/fastify-demo
```

### Checking Submodule Status

```bash
git submodule status
```

## Running Integration Tests

### All Integration Tests

```bash
pytest tests/integration/
```

### Specific Framework Tests

Each framework has its own standalone real-world test file:

```bash
# JavaScript/TypeScript frameworks
pytest tests/integration/test_realworld_express.py -v
pytest tests/integration/test_realworld_fastify.py -v
pytest tests/integration/test_realworld_nestjs.py -v
pytest tests/integration/test_realworld_nextjs.py -v

# Python frameworks
pytest tests/integration/test_realworld_fastapi.py -v
pytest tests/integration/test_realworld_flask.py -v
pytest tests/integration/test_realworld_django.py -v

# Java frameworks
pytest tests/integration/test_realworld_spring_boot.py -v
```

### With Coverage

```bash
pytest tests/integration/ --cov=api_extractor --cov-report=html
```

## CI/CD Considerations

When running tests in CI/CD pipelines, ensure submodules are initialized:

```yaml
# GitHub Actions example
- name: Checkout code
  uses: actions/checkout@v4
  with:
    submodules: recursive

# Or manually:
- name: Initialize submodules
  run: git submodule update --init --recursive
```

## Maintenance

### When to Update Submodules

- Quarterly review of submodule versions
- When new features are added to frameworks
- When fixing extractor bugs that were found in real-world code

### Frozen Versions

Submodules are pinned to specific commits to ensure test reproducibility. The commits are recorded in `.gitmodules` and the parent repository's index.

To see which commit each submodule is at:

```bash
git submodule status
```

## Adding New Real-World Fixtures

When adding a new real-world fixture:

1. **Research**: Find a high-quality, actively maintained repository
2. **Add submodule**: `git submodule add <url> tests/fixtures/real-world/<name>`
3. **Document**: Add entry to this README with expected endpoints
4. **Test**: Create integration test file in `tests/integration/test_realworld_<framework>.py`
5. **Verify**: Ensure extractor works correctly
6. **Commit**: Commit the `.gitmodules` change and submodule reference

## Criteria for Real-World Fixtures

Good real-world fixtures should be:

- **Actively maintained**: Recent commits, not archived
- **Production quality**: Follows best practices
- **Well-structured**: Clear organization, good examples
- **Reasonable size**: Not too large (< 10MB), but not trivial
- **Representative**: Uses common patterns for that framework
- **Documented**: Clear documentation of what it does
- **Official or community recognized**: From framework creators or highly starred

## Size Considerations

Real-world fixtures can be large. They are:
- Not committed directly to the repository (git submodules)
- Downloaded on-demand
- Can be excluded from certain test runs if needed

To skip integration tests:

```bash
pytest tests/unit/  # Only run unit tests
```
