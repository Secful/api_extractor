# Formbricks - Next.js Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/formbricks/formbricks
- **Stars:** 12,144
- **Last Updated:** 2026-04-28
- **Language:** TypeScript (92.6%)
- **License:** AGPL-3.0

## Selection Rationale
Production-grade survey and experience management platform (Qualtrics alternative) serving Fortune 500 companies including Siemens, IKEA, GitHub, and Ethereum Foundation, demonstrating enterprise-scale Next.js 16 app router patterns with versioned APIs (v1/v2/v3), SAML SSO, OAuth, webhooks, multi-channel integrations (Airtable, Notion, Slack), and comprehensive testing infrastructure - providing maximum diversity from cal.com's scheduling domain and dub's link management with a survey/feedback-centric architecture.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Last commit April 28, 2026 (today), continuous development |
| Code Quality | 10/10 | 448 tests, 19 CI/CD workflows (e2e, Docker, SonarQube, security scans) |
| Endpoint Count | 10/10 | 65 endpoints (ideal range for comprehensive testing) |
| Framework Usage | 10/10 | Next.js 16.2.4 with app router, modern patterns |
| Pattern Diversity | 10/10 | SAML/SSO, OAuth, webhooks, file storage, multi-channel integrations |
| Production Usage | 5/5 | Production SaaS with SOC 2, GDPR compliance |
| Documentation | 5/5 | Comprehensive docs, 226-line README, API specs, OpenAPI |
| Stars/Popularity | 5/5 | 12,144 stars |
| **TOTAL** | **60/60** | **PASS (Perfect Score)** |

## Application Overview

- **Domain:** Survey & Experience Management Platform
- **Description:** Open-source alternative to Qualtrics for creating and managing multi-channel surveys (web, email, mobile), collecting user feedback, and analyzing experience data. Enterprise-ready with SOC 2 and GDPR compliance.
- **Key Features:**
  - Multi-channel survey deployment (web widgets, email, mobile SDKs)
  - Survey builder with conditional logic
  - Integration hub (Airtable, Notion, Slack, Make, n8n, Zapier)
  - Real-time response pipeline processing
  - Display management (link surveys, app surveys, website surveys)
  - SAML SSO and OAuth authentication
  - Webhook system for event notifications
  - File storage and uploads
  - Multi-tenant architecture with teams and organizations
  - API versioning (v1, v2, v3)
  - Health monitoring and status checks

## API Structure

### Expected Endpoint Count
**Estimated:** 65 endpoints

### Key Endpoint Categories

**API Routes (app router structure):**
- Auth endpoints (OAuth callbacks, SAML SSO, invites)
- Survey management (CRUD, submission, completion)
- Response collection and processing
- Display management (link, app, website surveys)
- Integration endpoints (Airtable, Notion, Slack, webhooks)
- File storage and uploads
- Pipeline processing (real-time response handling)
- Health checks and status monitoring
- User and organization management
- Environment and project configuration
- Versioned API routes (v1, v2, v3)

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| POST | /api/auth/callback/[provider] | OAuth callback | provider (path) | Dynamic OAuth |
| GET | /api/v1/client/[environmentId]/displays | Get displays | environmentId (path) | Versioned API |
| POST | /api/v1/client/[environmentId]/displays/[displayId]/responded | Mark displayed | displayId (path) | Response tracking |
| POST | /api/v1/client/[environmentId]/responses | Submit response | body: Response | Response collection |
| GET | /api/v1/management/surveys | List surveys | query params | Survey management |
| POST | /api/v1/management/surveys | Create survey | body: Survey | Survey creation |
| GET | /api/v1/management/surveys/[surveyId] | Get survey | surveyId (path) | Single survey |
| PUT | /api/v1/management/surveys/[surveyId] | Update survey | surveyId, body | Survey update |
| DELETE | /api/v1/management/surveys/[surveyId] | Delete survey | surveyId (path) | Survey deletion |
| POST | /api/v1/management/storage/local | Upload file | multipart form | File upload |
| GET | /api/v1/management/me/organizations | List orgs | - | User orgs |
| POST | /api/v3/integrations/[integrationId]/webhook | Integration webhook | integrationId, body | Webhook handler |
| GET | /api/v1/client/[environmentId]/people/[userId]/displays | User displays | environmentId, userId | User-specific |
| POST | /api/auth/signup/invite | Accept invite | body: InviteToken | Team invites |
| GET | /api/pipeline | Health check | - | Monitoring |
| POST | /api/v1/client/[environmentId]/actions | Track action | body: Action | Event tracking |

## Notable Patterns

### 1. API Versioning
- Multiple API versions (v1, v2, v3)
- Allows backward compatibility and gradual migration
- Files: `/apps/web/app/api/v1/`, `/apps/web/app/api/v2/`, `/apps/web/app/api/v3/`

### 2. Next.js App Router
- Modern Next.js 16 with app router architecture
- Route handlers in `route.ts` files
- Dynamic segments with `[param]` notation
- Files: `/apps/web/app/api/`

### 3. Multi-Tenant Architecture
- Environment-based isolation
- Organization and team management
- User roles and permissions
- Files: Organization and environment models

### 4. OAuth & SAML Integration
- Multiple OAuth providers
- SAML SSO for enterprise authentication
- Dynamic callback routes
- Files: `/apps/web/app/api/auth/`

### 5. Webhook System
- Outbound webhooks for integrations
- Inbound webhook handlers
- Event-driven architecture
- Files: `/apps/web/app/api/v3/integrations/`

### 6. File Storage
- Local and cloud storage support
- File upload endpoints
- Secure file access
- Files: `/apps/web/app/api/v1/management/storage/`

### 7. Real-Time Pipeline
- Response processing pipeline
- Real-time display updates
- Event streaming
- Files: `/apps/web/app/api/pipeline/`

### 8. Integration Hub
- Airtable integration
- Notion integration
- Slack notifications
- Make, n8n, Zapier support
- Files: Integration package

### 9. Monorepo Structure
- Turborepo monorepo
- Multiple apps and packages
- Shared code across services
- Files: Root workspace configuration

### 10. Testing Infrastructure
- 448 test files
- E2E tests with Playwright
- Unit tests with Jest
- Integration tests
- Files: `__tests__/`, `*.test.ts`

### 11. CI/CD Pipeline
- 19 GitHub Actions workflows
- Automated testing (unit, e2e)
- Docker builds and deployment
- Security scanning (SonarQube)
- Code quality checks (linting, formatting)
- Files: `.github/workflows/`

### 12. Multi-Channel Surveys
- Web widget surveys
- Email surveys
- Mobile SDK surveys
- Link surveys
- Files: Display and survey packages

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `len(result.endpoints) == 65` (exact match per coding standards)
- HTTP methods: GET, POST, PUT, DELETE, PATCH present
- Path parameters extracted correctly (`{environmentId}`, `{surveyId}`, `{provider}`, etc.)
- Dynamic route segments converted to OpenAPI format
- Versioned API paths detected (`/api/v1/`, `/api/v2/`, `/api/v3/`)
- Source tracking present

**Known Edge Cases:**
1. Dynamic OAuth routes - `[provider]` should become `{provider}`
2. Multiple path parameters in single route
3. Versioned APIs - ensure version prefix included in path
4. Monorepo structure - only extract from main web app
5. Nested dynamic segments
6. Middleware routes - may not be API endpoints

## Special Considerations

### Dependencies
- Database: PostgreSQL
- Cache: Redis (optional)
- Runtime: Node.js 20+
- TypeScript 5.x
- Next.js 16.2.4
- Prisma ORM
- tRPC (some internal APIs)

### Excluded Files/Directories
- Tests: `__tests__/`, `*.test.ts`, `*.spec.ts`
- Build: `dist/`, `.next/`, `.turbo/`
- Dependencies: `node_modules/`
- Config: `.env`, `*.config.js`
- Packages: Other monorepo packages (only extract from `/apps/web/`)
- Documentation: `docs/`, `*.md`
- Scripts: `scripts/`, `bin/`

### Extractor Challenges
1. **Monorepo structure** - Multiple apps, need to focus on main web app
2. **App router** - Route handlers in `route.ts` files with exported HTTP methods
3. **Dynamic segments** - Convert `[param]` to `{param}` format
4. **API versioning** - Multiple versions of similar endpoints
5. **tRPC routes** - May have internal tRPC alongside REST
6. **Middleware** - Some routes may be middleware, not endpoints
7. **Large codebase** - 65+ endpoints across versioned APIs

## Integration Test Plan

### Test File
`tests/integration/test_realworld_nextjs_formbricks.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert len(result.endpoints) == 65  # Exact match per coding standards

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.DELETE in methods

# Versioned APIs
paths = {ep.path for ep in result.endpoints}
assert any("/api/v1/" in p for p in paths), "Should find v1 API endpoints"
assert any("/api/v2/" in p for p in paths) or any("/api/v3/" in p for p in paths), "Should find v2 or v3 endpoints"

# Core endpoints
assert any("surveys" in p for p in paths), "Should find survey endpoints"
assert any("responses" in p for p in paths), "Should find response endpoints"
assert any("displays" in p for p in paths), "Should find display endpoints"

# OAuth/Auth endpoints
auth_endpoints = [ep for ep in result.endpoints if "auth" in ep.path]
assert len(auth_endpoints) >= 3, "Should find authentication endpoints"

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 30, "Should find many parameterized endpoints"

# Dynamic segments properly converted
for ep in param_endpoints:
    assert "{" in ep.path and "}" in ep.path, f"Should use OpenAPI format: {ep.path}"
    assert "[" not in ep.path and "]" not in ep.path, f"Should not have Next.js format: {ep.path}"

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".ts") or ep.source_file.endswith(".tsx")
    assert ep.source_line is not None
    assert ep.source_line > 0
```

### Key Validations
1. App router endpoint extraction
2. Dynamic route segment conversion
3. API versioning detection
4. Multiple HTTP methods per route
5. Path parameter extraction
6. OAuth callback routes
7. Webhook endpoints
8. File upload endpoints
9. Multi-level nested routes
10. Source file tracking

## Notes

### Production Scale
- **SOC 2 compliant**
- **GDPR compliant**
- **Used by Fortune 500** (Siemens, IKEA, GitHub, Ethereum Foundation)
- **12K+ GitHub stars**
- **Active development** with daily commits

### Architecture Highlights
- Monorepo with Turborepo
- Next.js 16 app router (modern architecture)
- Multi-tenant with environment isolation
- Versioned APIs for backward compatibility
- Real-time response pipeline
- Multi-channel survey deployment

### Testing Infrastructure
- 448 test files across the codebase
- Playwright e2e tests
- Jest unit tests
- 19 CI/CD workflows
- Automated security scanning
- Code quality enforcement

### Diversity from Existing Fixtures
This repository provides maximum contrast with existing Next.js fixtures:
- **Domain:** Survey/feedback platform vs cal.com (scheduling) vs dub (links)
- **Endpoints:** 65 vs cal.com/dub (varied)
- **Architecture:** App router, monorepo, versioned APIs
- **Complexity:** Medium-high with multi-tenant, integrations, webhooks
- **Patterns:** SAML SSO, OAuth, webhooks, file storage, real-time pipeline
- **Testing:** 448 tests with comprehensive CI/CD
- **Production:** SOC 2 certified, Fortune 500 clients
