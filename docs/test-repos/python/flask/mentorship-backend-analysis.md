# Mentorship Backend - Flask Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/anitab-org/mentorship-backend
- **Stars:** 199
- **Last Updated:** 2023-08-26
- **Language:** Python
- **License:** GNU GPL v3

## Selection Rationale
Mentorship Backend was selected as the top-scoring Flask repository (58/60) demonstrating professional mentorship platform patterns with complex relationship management, nested resources, state machines, and production deployment. It represents enterprise-grade Flask-RESTX architecture.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 6/10 | Last commit August 2023 (19 months ago), but well-maintained |
| Code Quality | 10/10 | Comprehensive tests, CI/CD, Black, isort, Flake8, codecov |
| Endpoint Count | 10/10 | 33 endpoints - excellent variety |
| Framework Usage | 10/10 | Flask-RESTX as primary, Swagger integration |
| Pattern Diversity | 9/10 | JWT, email verification, RBAC, nested resources, state machines |
| Production Usage | 5/5 | Deployed on Heroku, real AnitaB.org mentorship program |
| Documentation | 5/5 | Extensive README, Swagger docs, contributing guidelines |
| Stars/Popularity | 3/5 | 199 stars, 450 forks |
| **TOTAL** | **58/60** | **PASS (Highest Score)** |

## Application Overview

- **Domain:** Social mentorship platform for women in tech
- **Description:** Platform connecting mentors and mentees with relationship management, task tracking, and admin controls.
- **Key Features:**
  - User registration with email verification
  - Mentorship relationship requests (send, accept, reject, cancel)
  - Task management within relationships
  - Task comments and discussions
  - Admin role management
  - Dashboard and statistics
  - Password management

## API Structure

### Expected Endpoint Count
**Estimated:** 33 endpoints

### Key Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| POST | /register | User registration | username, email, password | Registration |
| POST | /login | User login | username, password | JWT auth |
| POST | /refresh | Refresh token | refresh_token | Token refresh |
| GET | /user/confirm_email/{token} | Email verification | token (path) | Email verify |
| POST | /user/resend_email | Resend verification | - | Email |
| GET | /user | Get current user | - | Current user |
| PUT | /user | Update user profile | profile data | Update |
| DELETE | /user | Delete account | - | Account deletion |
| PUT | /user/change_password | Change password | old, new password | Password |
| GET | /users | List all users | - | User list |
| GET | /users/<id> | Get user by ID | id (path) | User detail |
| GET | /users/verified | List verified users | - | Verified users |
| GET | /home | Dashboard stats | - | Statistics |
| GET | /dashboard | User dashboard | - | Dashboard |
| POST | /mentorship_relation/send_request | Send mentorship request | mentor_id, notes | Create relation |
| GET | /mentorship_relations | List all relations | - | Relations list |
| PUT | /mentorship_relation/<id>/accept | Accept request | id (path) | State change |
| PUT | /mentorship_relation/<id>/reject | Reject request | id (path) | State change |
| PUT | /mentorship_relation/<id>/cancel | Cancel relation | id (path) | State change |
| DELETE | /mentorship_relation/<id> | Delete relation | id (path) | Delete |
| GET | /mentorship_relations/past | Past relations | - | Historical |
| GET | /mentorship_relations/current | Current relation | - | Active |
| GET | /mentorship_relations/pending | Pending requests | - | Pending |
| POST | /mentorship_relation/<id>/task | Create task | id, task data | Task creation |
| GET | /mentorship_relation/<id>/tasks | List tasks | id (path) | Tasks list |
| PUT | /mentorship_relation/<id>/task/<task_id>/complete | Complete task | ids (path) | Mark complete |
| DELETE | /mentorship_relation/<id>/task/<task_id> | Delete task | ids (path) | Delete task |
| POST | /mentorship_relation/<id>/task/<task_id>/comment | Add comment | ids, comment | Comment |
| GET | /mentorship_relation/<id>/task/<task_id>/comments | List comments | ids (path) | Comments |
| PUT | /mentorship_relation/<id>/task/<task_id>/comment/<cid> | Update comment | ids, comment | Update |
| DELETE | /mentorship_relation/<id>/task/<task_id>/comment/<cid> | Delete comment | ids (path) | Delete |
| POST | /admin/new | Assign admin | user_id | Admin role |
| POST | /admin/remove | Remove admin | user_id | Remove role |
| GET | /admins | List admins | - | Admin list |

## Notable Patterns

### 1. Authentication & Authorization
- JWT authentication with refresh tokens
- Email verification workflow
- Role-based access control (admin endpoints)
- Files: `/app/api/auth/`, `/app/utils/decorator_utils.py`

### 2. State Machine (Mentorship Relations)
- Pending → Accept/Reject
- Active → Cancel
- State transitions with validation
- Files: `/app/api/resources/mentorship_relation.py`

### 3. Nested Resources
- Relations → Tasks → Comments (3-level nesting)
- Complex path parameters
- Files: `/app/api/resources/task.py`, `/app/api/resources/task_comment.py`

### 4. Email Integration
- Flask-Mail for email verification
- Resend email functionality
- Files: `/app/utils/email_utils.py`

### 5. Database Migrations
- Flask-Migrate (Alembic)
- Schema version control
- Files: `/migrations/`

### 6. API Documentation
- Flask-RESTX with Swagger UI
- Auto-generated API docs
- Files: `/app/api/__init__.py`

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `30 <= len(result.endpoints) <= 36`
- HTTP methods: GET, POST, PUT, DELETE present
- Path parameters extracted correctly (`<id>`, `<task_id>`, `<cid>`)
- Source file tracking present
- Nested resource paths detected

**Known Edge Cases:**
1. Flask path parameter format `<id>` vs OpenAPI `{id}` - extractor should normalize
2. Deeply nested resources (3 levels) - should extract correctly
3. Multiple path parameters in single route
4. Email token in URL path

## Special Considerations

### Dependencies
- Database: PostgreSQL or SQLite
- Python 3.8+
- Flask-RESTX, Flask-JWT-Extended, Flask-Mail
- Email service (SMTP)

### Excluded Files/Directories
- Tests: `tests/`
- Docs: `docs/`
- Build: `.github/`, `scripts/`
- Migrations: `migrations/` (database schema, not API code)
- Virtual env: `venv/`, `.venv/`

### Extractor Challenges
1. **Flask-RESTX namespace structure** - Routes organized in namespaces
2. **Resource classes** - Flask-RESTX uses class-based views
3. **Nested path parameters** - Multiple `<param>` in single path
4. **Method decorators** - `@jwt_required`, `@admin_only`

## Integration Test Plan

### Test File
`tests/integration/test_realworld_flask_mentorship.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert 30 <= len(result.endpoints) <= 36

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.DELETE in methods

# Specific paths (Flask uses <param>, should normalize to {param})
paths = {ep.path for ep in result.endpoints}
assert "/users" in paths or "/users/{id}" in paths
assert any("mentorship_relation" in path for path in paths)
assert any("/task" in path for path in paths)

# Nested resources
nested_paths = [p for p in paths if p.count("/") > 3]
assert len(nested_paths) > 5

# Admin endpoints
admin_paths = [p for p in paths if "admin" in p.lower()]
assert len(admin_paths) >= 2

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".py")
    assert ep.source_line > 0
```

### Key Validations
1. Flask-RESTX resource detection
2. Path parameter normalization (`<id>` → `{id}`)
3. Nested resource paths
4. State machine endpoints (accept, reject, cancel)
5. Admin-specific endpoints
6. Email verification workflow
7. Multiple HTTP methods per resource
