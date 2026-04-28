# Fastify API Boilerplate JWT - Fastify Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/Tony133/fastify-api-boilerplate-jwt
- **Stars:** 587
- **Last Updated:** 2026-04-24
- **Language:** TypeScript (99.1%)
- **License:** MIT

## Selection Rationale
Production-ready REST API boilerplate demonstrating advanced Fastify patterns (plugins, decorators, hooks, preHandlers, TypeBox validation schemas) across 14 endpoints for authentication and user management, providing comprehensive testing of JWT authentication, role-based access control, and modern Fastify ecosystem integration - offering a distinct domain (auth/user management) compared to existing test repositories.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Last commit April 24, 2026 (4 days ago), consistent activity |
| Code Quality | 10/10 | Tests (14 files), CI/CD (Node 20/22/24), TypeScript, linting, commitlint |
| Endpoint Count | 7/10 | 14 endpoints (slightly below ideal 15-50, but well-distributed) |
| Framework Usage | 10/10 | Fastify 5.x as primary framework, extensive ecosystem usage |
| Pattern Diversity | 10/10 | Plugins, decorators, hooks, schemas (TypeBox), autoload, type providers |
| Production Usage | 3/5 | Boilerplate/template, but production-ready patterns |
| Documentation | 5/5 | README, Swagger/OpenAPI docs, inline documentation, .env.example |
| Stars/Popularity | 4/5 | 587 stars (good visibility, approaching 500+ target) |
| **TOTAL** | **59/60** | **PASS (Excellent Score)** |

## Application Overview

- **Domain:** Authentication & User Management System
- **Description:** Complete REST API boilerplate for building authenticated APIs with user management, JWT authentication (access + refresh tokens), role-based access control, password management (change, forgot/reset), and email integration
- **Key Features:**
  - User registration and authentication
  - JWT-based authentication (access tokens + refresh tokens)
  - Role-based authorization (admin, user roles)
  - User CRUD operations
  - Password management (change password, forgot/reset)
  - Email notifications (password reset)
  - Protected and public endpoints
  - Rate limiting
  - Security headers (Helmet)
  - Health monitoring
  - Swagger/OpenAPI documentation

## API Structure

### Expected Endpoint Count
**Estimated:** 14 endpoints

### Key Endpoint Categories

**Users (5 endpoints):**
- Create user
- List all users
- Get user by ID
- Update user
- Delete user

**Authentication (4 endpoints):**
- User login (get access + refresh tokens)
- Refresh access token
- Check authentication status
- Get authenticated user data

**Registration (1 endpoint):**
- User registration (public)

**Password Management (2 endpoints):**
- Change password (authenticated)
- Forgot password (initiate reset via email)

**Public/Protected Test (2 endpoints):**
- Public endpoint (no auth)
- Secured endpoint (requires JWT)

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| POST | /api/register | Register user | body: {name, email, password} | Public |
| POST | /api/authentication/login | Login user | body: {email, password} | Returns JWT tokens |
| POST | /api/authentication/refresh-token | Refresh token | body: {refreshToken} | Get new access token |
| GET | /api/authentication/is-authenticated | Check auth | Authorization header | Verify token validity |
| GET | /api/authentication/user-authenticated | Get auth user | Authorization header | Current user data |
| POST | /api/change-password | Change password | body: {oldPassword, newPassword} | Requires auth |
| POST | /api/forgot-password | Reset password | body: {email} | Sends reset email |
| POST | /api/users | Create user | body: {name, email, password, role} | Admin only |
| GET | /api/users | List users | - | Admin only |
| GET | /api/users/{id} | Get user | id (path) | Admin only |
| PUT | /api/users/{id} | Update user | id, body | Admin only |
| DELETE | /api/users/{id} | Delete user | id (path) | Admin only |
| GET | /api | Public endpoint | - | Health check |
| GET | /api/secure | Protected endpoint | Authorization header | Requires JWT |

## Notable Patterns

### 1. Plugin Architecture
- 12 custom plugins demonstrating Fastify plugin system
- Database plugin (Kysely connection)
- JWT plugin (@fastify/jwt)
- Swagger plugin (@fastify/swagger)
- Rate limit plugin (@fastify/rate-limit)
- Helmet plugin (@fastify/helmet)
- CORS plugin (@fastify/cors)
- Mailer plugin (Nodemailer)
- Under pressure plugin (health monitoring)
- Files: `/src/plugins/`

### 2. Custom Decorators
- `fastify.checkToken()` - Token validation decorator
- `fastify.checkRole(requiredRole)` - Role validation decorator
- Attached to Fastify instance for reuse
- Files: `/src/plugins/check-token.ts`, `/src/plugins/check-role.ts`

### 3. PreHandler Hooks
- Authentication hooks using `onRequest` and `preHandler`
- Role-based authorization hooks
- Applied per-route or per-plugin
- Files: Route definitions with `onRequest: [fastify.checkToken]`

### 4. TypeBox Schema Validation
- End-to-end type safety with @fastify/type-provider-typebox
- Request body, query params, path params validation
- Response schema validation
- Auto-generated TypeScript types from schemas
- Files: `/src/schemas/`

### 5. Autoload for Routes and Plugins
- Uses @fastify/autoload for automatic registration
- Convention-based routing
- Automatic plugin discovery
- Files: `/src/app.ts` (autoload configuration)

### 6. JWT Authentication with Refresh Tokens
- Access tokens (short-lived)
- Refresh tokens (long-lived, stored in DB)
- Token rotation on refresh
- Files: `/src/plugins/jwt.ts`, `/src/routes/authentication/`

### 7. Role-Based Access Control (RBAC)
- User roles: admin, user
- Role validation via decorator
- Protected routes by role
- Files: `/src/plugins/check-role.ts`, routes with role checks

### 8. Database Integration with Kysely
- Type-safe SQL query builder
- PostgreSQL database
- Migrations support
- Connection pooling
- Files: `/src/plugins/database.ts`, `/src/repositories/`

### 9. Service Layer Pattern
- Business logic in services
- Repositories for data access
- Controllers delegate to services
- Files: `/src/services/`, `/src/repositories/`

### 10. Password Security
- Argon2 hashing (bcrypt alternative)
- Salted password storage
- Password strength requirements
- Files: `/src/plugins/argon.ts`

### 11. Email Integration
- Nodemailer for email sending
- Password reset emails
- Template support
- Files: `/src/plugins/mailer.ts`

### 12. Security Middleware
- Helmet for security headers
- Rate limiting per endpoint
- CORS configuration
- Under pressure (load monitoring)
- Files: `/src/plugins/helmet.ts`, `/src/plugins/rate-limit.ts`

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `len(result.endpoints) == 14` (exact match per coding standards)
- HTTP methods: GET, POST, PUT, DELETE present
- Path parameters extracted correctly (`{id}`)
- Fastify route patterns detected
- Multiple modules detected
- Source tracking present

**Known Edge Cases:**
1. Autoload routes - automatic route registration may affect extraction
2. Plugin-based routes - routes registered via plugins
3. Decorators - should not be extracted as endpoints
4. Hooks - preHandler hooks should not create separate endpoints
5. TypeBox schemas - validation schemas not endpoints
6. JWT middleware - should not be extracted as endpoint

## Special Considerations

### Dependencies
- Database: PostgreSQL (via Kysely)
- Runtime: Node.js 20+
- TypeScript 6.x
- Fastify 5.x
- Kysely (SQL query builder)
- Argon2 (password hashing)
- Nodemailer (email)

### Excluded Files/Directories
- Tests: `*.test.ts`, `test/`
- Build: `dist/`, `.cache/`
- Dependencies: `node_modules/`
- Config: `.env`, `*.config.js`
- Database: `migrations/` (Kysely migrations)

### Extractor Challenges
1. **Autoload routes** - Routes registered automatically, need to parse file structure
2. **Plugin architecture** - Routes may be in plugin files
3. **TypeScript decorators** - Custom Fastify decorators
4. **TypeBox schemas** - Schema definitions vs route definitions
5. **Path parameters** - Fastify `:param` to OpenAPI `{param}` conversion
6. **Hooks** - Don't extract hooks as separate endpoints
7. **JWT middleware** - Authentication decorators not endpoints

## Integration Test Plan

### Test File
`tests/integration/test_realworld_fastify_jwt_boilerplate.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert len(result.endpoints) == 14

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.DELETE in methods

# Specific paths
paths = {ep.path for ep in result.endpoints}
assert "/api/register" in paths or "/register" in paths
assert any("authentication/login" in p for p in paths)
assert any("users" in p for p in paths)

# User CRUD endpoints
user_endpoints = [ep for ep in result.endpoints if "users" in ep.path]
assert len(user_endpoints) >= 5  # CRUD operations

# Authentication endpoints
auth_endpoints = [ep for ep in result.endpoints if "authentication" in ep.path]
assert len(auth_endpoints) >= 4  # Login, refresh, check auth, get user

# Password management
password_endpoints = [ep for ep in result.endpoints if "password" in ep.path]
assert len(password_endpoints) >= 2  # Change, forgot

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 3  # User CRUD with :id

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".ts")
    assert ep.source_line is not None
    assert ep.source_line > 0

# Multiple methods per path (user CRUD)
path_methods = {}
for ep in result.endpoints:
    if ep.path not in path_methods:
        path_methods[ep.path] = set()
    path_methods[ep.path].add(ep.method)

multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
assert len(multi_method_paths) >= 1  # At least users/:id has GET/PUT/DELETE
```

### Key Validations
1. All 14 endpoints extracted
2. User CRUD operations
3. Authentication endpoints (login, refresh, check)
4. Password management endpoints
5. Registration endpoint
6. Public vs protected endpoints
7. Path parameter extraction
8. Source file and line tracking
9. Multiple HTTP methods per path
10. All CRUD methods present

## Notes

### TypeBox Integration
The repository uses @fastify/type-provider-typebox for end-to-end type safety. This provides:
- Runtime validation via TypeBox schemas
- Compile-time TypeScript types derived from schemas
- Auto-generated Swagger documentation from schemas

This is a modern Fastify pattern worth testing.

### JWT Implementation
Uses a dual-token system:
- **Access tokens**: Short-lived (15 minutes), used for API requests
- **Refresh tokens**: Long-lived (7 days), stored in database, used to get new access tokens

This is a production-grade approach to JWT authentication.

### Role-Based Access Control
Implements RBAC with two roles:
- **admin**: Can manage users (CRUD operations)
- **user**: Can manage own account only

Protected routes check both authentication (valid token) and authorization (required role).

### Security Features
- Argon2 password hashing (more secure than bcrypt)
- Rate limiting (prevents brute force attacks)
- Helmet security headers
- CORS configuration
- Under pressure monitoring (prevents overload)
- JWT token rotation

### Diversity from Existing Repos
This repository provides contrast with existing test fixtures:
- **Domain:** Auth/user management vs blogging, wealth management, multi-service hub
- **Patterns:** Fastify plugins/decorators vs Express middleware, NestJS guards
- **Focus:** Authentication system vs content management
- **Architecture:** Plugin-based vs monolithic/modular
- **Database:** Kysely (query builder) vs TypeORM/Prisma (ORMs)
- **Validation:** TypeBox schemas vs class-validator/Joi
