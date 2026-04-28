# wger - Django REST Framework Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/wger-project/wger
- **Stars:** 6,012
- **Last Updated:** 2026-04-28
- **Language:** Python
- **License:** AGPL-3.0

## Selection Rationale
wger was selected as the second Django REST Framework repository, representing a production fitness/workout management platform with clean multi-app architecture, comprehensive DRF patterns including nested routing and custom actions, deployed at wger.de with 50+ ViewSets providing excellent mid-range complexity testing between simple tutorials and enterprise-scale apps like NetBox.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Latest commit April 2026, continuous development |
| Code Quality | 9/10 | 125 test files, CI/CD, Coveralls, comprehensive coverage |
| Endpoint Count | 10/10 | ~50-60 endpoints (ideal mid-range) |
| Framework Usage | 10/10 | DRF v3.17 as primary framework, Django 5.2 |
| Pattern Diversity | 9/10 | Nested routes, custom actions, file uploads, filtering, JWT auth |
| Production Usage | 5/5 | Live production deployment at wger.de |
| Documentation | 4/5 | Good API docs, deployment guides, some areas could be expanded |
| Stars/Popularity | 5/5 | 6,012 stars, active community |
| **TOTAL** | **57/60** | **PASS (High Django Score)** |

## Application Overview

- **Domain:** Fitness & Workout Management
- **Description:** Self-hosted fitness/workout, nutrition, and weight tracker with exercise database, workout planning, progress tracking, and gym management features.
- **Key Features:**
  - Exercise database with videos, images, and instructions
  - Workout plan creation and scheduling
  - Nutrition tracking with Open Food Facts integration
  - Progress photos and body measurements
  - Weight tracking and goals
  - Multi-tenant gym management
  - REST API for all resources
  - Celery for background tasks
  - OpenAPI schema with drf-spectacular

## API Structure

### Expected Endpoint Count
**Estimated:** 50-70 endpoints

### Key Endpoint Categories

**Exercises:**
- Exercise database (exercises, categories, equipment, muscles)
- Exercise images, videos, comments
- Exercise translations

**Workouts:**
- Workout plans and templates
- Workout days, sets, settings
- Workout sessions and logs

**Nutrition:**
- Meal plans and nutrition plans
- Ingredients and meals
- Diary entries
- Nutritional goals

**Progress Tracking:**
- Body weight entries
- Body measurements
- Progress photos
- Workout logs

**User Management:**
- User profiles and preferences
- Authentication (JWT)
- Gym management (multi-tenancy)

**Gallery:**
- User images
- Progress photos

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| GET | /api/v2/exercise/ | List exercises | limit, offset, language | Pagination, filtering |
| POST | /api/v2/exercise/ | Create exercise | exercise data | Auth required |
| GET | /api/v2/exercise/{id}/ | Get exercise | id (path) | Single exercise |
| PUT | /api/v2/exercise/{id}/ | Update exercise | id, exercise data | Full update |
| PATCH | /api/v2/exercise/{id}/ | Partial update | id, partial data | Partial update |
| DELETE | /api/v2/exercise/{id}/ | Delete exercise | id (path) | Delete |
| GET | /api/v2/exercise/{id}/images/ | List exercise images | id (path) | Nested resource |
| POST | /api/v2/exercise/{id}/images/ | Upload image | id, image file | File upload |
| GET | /api/v2/exercisecategory/ | List categories | filtering params | Categories |
| GET | /api/v2/muscle/ | List muscles | - | Muscle groups |
| GET | /api/v2/equipment/ | List equipment | - | Exercise equipment |
| GET | /api/v2/workout/ | List workouts | user filter | User workouts |
| POST | /api/v2/workout/ | Create workout | workout data | Create plan |
| GET | /api/v2/nutritionplan/ | List nutrition plans | filtering | Nutrition plans |
| GET | /api/v2/weight/ | List weight entries | date range | Weight tracking |
| POST | /api/v2/weight/ | Log weight entry | weight data | Add entry |

## Notable Patterns

### 1. Authentication
- JWT-based (djangorestframework-simplejwt)
- Token authentication for API access
- Permission-based access control
- Files: `/wger/core/api/permissions.py`, `/wger/utils/permissions.py`

### 2. Nested Routing
- Exercises with nested images, videos, comments
- Workouts with nested days, sets, sessions
- Hierarchical resource relationships
- Files: ViewSets in `/wger/*/api/views.py`

### 3. Custom ViewSet Actions
- `@action` decorators for custom endpoints
- Statistics endpoints
- Export/import functionality
- Files: Multiple ViewSets with custom actions

### 4. File Upload Handling
- Exercise images and videos
- Progress photos
- Multipart form-data support
- Files: `/wger/exercises/api/views.py`, `/wger/gallery/api/views.py`

### 5. Filtering & Search
- Django Filter Backend integration
- Complex query parameter filtering
- Search across multiple fields
- Files: Filter classes in API views

### 6. OpenAPI Schema
- drf-spectacular integration
- Auto-generated API documentation
- Schema endpoint at `/api/schema/`
- Files: `/wger/core/api/schema.py`

### 7. Multi-Tenancy
- Gym management features
- Per-tenant data isolation
- Admin/member roles
- Files: `/wger/gym/` app

### 8. Celery Integration
- Background task processing
- Async operations for heavy computations
- Files: `/wger/*/tasks.py`

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `40 <= len(result.endpoints) <= 80`
- HTTP methods: GET, POST, PUT, PATCH, DELETE present
- Path parameters extracted correctly (`{id}`)
- DRF ViewSet patterns detected
- Router-based URL generation
- URL prefixes from include() properly applied (`/api/v2/`)
- Nested routes detected

**Known Edge Cases:**
1. Custom actions with `@action` decorator - may create additional endpoints
2. Nested routes (e.g., `/exercise/{id}/images/`) - ensure proper extraction
3. API versioning (`/api/v2/`) - ensure version prefix is captured
4. File upload endpoints - may have different handling
5. Multi-app structure - multiple Django apps (exercises, workouts, nutrition, etc.)
6. OpenAPI schema endpoint - may be included in extraction

## Special Considerations

### Dependencies
- Database: PostgreSQL (production), SQLite (development)
- Cache: Redis (optional)
- Message queue: RabbitMQ/Redis (for Celery)
- Python 3.11+
- Django 5.2+, DRF 3.17+

### Excluded Files/Directories
- Tests: `*/tests/`, `*_test.py`
- Migrations: `*/migrations/`
- Frontend: `wger/core/static/`, `wger/core/templates/`
- Docs: `docs/`
- Configuration: `settings*.py`

### Extractor Challenges
1. **API versioning** - URLs include `/api/v2/` prefix
2. **Nested ViewSets** - Exercise images/videos nested under exercises
3. **Custom actions** - `@action` decorators create additional endpoints
4. **Multi-app structure** - Many Django apps (exercises, workouts, nutrition, etc.)
5. **File upload endpoints** - Different parameter types
6. **Translation system** - Some endpoints support multiple languages

## Integration Test Plan

### Test File
`tests/integration/test_realworld_django_wger.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert 40 <= len(result.endpoints) <= 80

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.PATCH in methods
assert HTTPMethod.DELETE in methods

# Specific paths (with /api/v2 prefix)
paths = {ep.path for ep in result.endpoints}
assert any("/api/v2/exercise" in p for p in paths)
assert any("/api/v2/workout" in p for p in paths)
assert any("/api/v2/nutritionplan" in p for p in paths)

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 15

# ViewSet patterns
# Should have both list and detail endpoints
list_endpoints = [ep for ep in result.endpoints if "{" not in ep.path and ep.method == HTTPMethod.GET]
detail_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(list_endpoints) >= 10
assert len(detail_endpoints) >= 20

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".py")
    assert ep.source_line > 0

# API version prefix
api_v2_paths = [p for p in paths if p.startswith("/api/v2/")]
assert len(api_v2_paths) >= 30

# Multiple Django apps
app_keywords = ["exercise", "workout", "nutrition", "weight", "gallery"]
apps_found = set()
for path in paths:
    path_lower = path.lower()
    for keyword in app_keywords:
        if keyword in path_lower:
            apps_found.add(keyword)
assert len(apps_found) >= 3
```

### Key Validations
1. DRF ViewSet endpoint generation
2. Router-based URL patterns with `/api/v2/` prefix
3. Multiple Django apps (exercises, workouts, nutrition, etc.)
4. Custom actions with `@action` decorator
5. Nested routes (exercises/{id}/images)
6. All CRUD methods (GET, POST, PUT, PATCH, DELETE)
7. File upload endpoints (multipart/form-data)
8. API versioning in paths
