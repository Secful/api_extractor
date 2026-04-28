# Ghostfolio - NestJS Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/ghostfolio/ghostfolio
- **Stars:** 8,284
- **Last Updated:** 2026-04-27
- **Language:** TypeScript (99.3%)
- **License:** AGPL-3.0

## Selection Rationale
Production-grade open source wealth management application built with NestJS, demonstrating comprehensive framework patterns (Guards, Interceptors, custom decorators, DTOs, validation pipes) across 113 REST endpoints for portfolio tracking, asset management, and financial analytics - providing real-world FinTech testing scenarios completely different from existing test domains.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Commits within 24 hours (April 27, 2026), daily activity, 1000+ commits |
| Code Quality | 10/10 | 26 test files, CI/CD with GitHub Actions, ESLint, Prettier, Nx monorepo |
| Endpoint Count | 10/10 | 113 endpoints across 32+ controllers |
| Framework Usage | 10/10 | NestJS as primary framework with extensive pattern usage |
| Pattern Diversity | 10/10 | Guards, Interceptors (4 custom), Pipes, DTOs, validation, versioning, decorators |
| Production Usage | 5/5 | Live SaaS at ghostfol.io, Docker Hub images, paying customers |
| Documentation | 5/5 | Comprehensive README, setup guides, API docs, self-hosting guide |
| Stars/Popularity | 5/5 | 8,284 stars, 1,104 forks, active community |
| **TOTAL** | **60/60** | **PASS (Perfect Score)** |

## Application Overview

- **Domain:** Financial Technology (FinTech) - Portfolio & Wealth Management
- **Description:** Open source platform for tracking stocks, ETFs, and cryptocurrencies across multiple platforms, with portfolio analytics, performance reporting, and dividend tracking
- **Key Features:**
  - Multi-asset portfolio tracking (stocks, ETFs, cryptocurrencies)
  - Multiple account management
  - Performance analytics and benchmarking
  - Dividend tracking and reporting
  - Market data integration
  - Import/export functionality (CSV, JSON)
  - Watchlists
  - AI integration for recommendations
  - Admin queue management
  - Cache control
  - User impersonation (admin feature)
  - Subscription/premium features
  - Public API access

## API Structure

### Expected Endpoint Count
**Estimated:** 113 endpoints

### Key Endpoint Categories

**Portfolio Management (25+ endpoints):**
- Portfolio details and holdings
- Performance metrics and charts
- Dividend information
- Investment timeline
- Benchmark comparisons
- Portfolio reports (PDF generation)

**Activities/Transactions (15+ endpoints):**
- CRUD operations for transactions
- Activity filtering (account, asset class, tag)
- Activity import (CSV, JSON)
- Activity validation

**Account Management (10+ endpoints):**
- Multi-account CRUD operations
- Account balances
- Account transfers
- Platform integrations

**User Management (12+ endpoints):**
- User registration and authentication
- User settings and preferences
- Subscription management
- Access token management

**Admin Operations (15+ endpoints):**
- Queue management (cleanup, retry)
- Cache control
- System configuration
- User impersonation
- Platform management
- Data gathering control

**Asset Management (20+ endpoints):**
- Asset search and lookup
- Market data endpoints
- Symbol profiles
- Historical data
- Benchmarks (S&P 500, etc.)
- Watchlist management

**Import/Export (8+ endpoints):**
- CSV export
- JSON export
- Activity import
- Portfolio templates

**Public API (8+ endpoints):**
- Public portfolio access
- Public user profiles
- Featured users

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| POST | /api/v1/auth/anonymous | Anonymous login | deviceId | Guest access |
| POST | /api/v1/auth/signIn | User login | email, password | JWT auth |
| GET | /api/v1/portfolio | Get portfolio | range, accounts, assetClasses, tags | Filtering |
| GET | /api/v1/portfolio/details | Portfolio details | range, accounts | Holdings |
| GET | /api/v1/portfolio/performance | Performance metrics | range, accounts | Analytics |
| GET | /api/v1/portfolio/dividends | Dividend information | range, accounts | Dividend tracking |
| POST | /api/v1/order | Create activity | body: Activity | Transaction |
| GET | /api/v1/order | List activities | skip, take, accounts, assetClasses | Pagination |
| GET | /api/v1/order/{id} | Get activity | id (path) | Single transaction |
| PUT | /api/v1/order/{id} | Update activity | id, body | Transaction edit |
| DELETE | /api/v1/order/{id} | Delete activity | id (path) | Remove transaction |
| POST | /api/v1/import | Import activities | body: activities[] | CSV/JSON import |
| POST | /api/v1/export/activities | Export activities | filters | CSV export |
| GET | /api/v1/account | List accounts | - | Multi-account |
| POST | /api/v1/account | Create account | body: Account | Account creation |
| GET | /api/v1/account/{id} | Get account | id (path) | Single account |
| PUT | /api/v1/account/{id} | Update account | id, body | Account edit |
| DELETE | /api/v1/account/{id} | Delete account | id (path) | Remove account |
| POST | /api/v1/account/transfer | Account transfer | from, to, amount | Balance transfer |
| GET | /api/v1/user | Get current user | - | User profile |
| PUT | /api/v1/user | Update user | body: UserUpdate | Settings update |
| POST | /api/v1/user/subscription | Subscribe | coupon | Premium upgrade |
| POST | /api/v1/access | Create access token | - | API token |
| DELETE | /api/v1/access/{id} | Revoke token | id (path) | Token removal |
| POST | /api/v1/admin/queue/cleanup | Queue cleanup | - | Admin operation |
| POST | /api/v1/admin/cache/flush | Flush cache | - | Cache control |
| GET | /api/v1/admin/users | List all users | - | Admin user list |
| POST | /api/v1/admin/user/{id}/impersonation | Impersonate user | id (path) | Admin feature |
| GET | /api/v1/search | Search assets | query | Asset search |
| GET | /api/v1/symbol/{dataSource}/{symbol} | Get symbol | dataSource, symbol | Market data |
| GET | /api/v1/benchmark | List benchmarks | - | S&P 500, etc. |
| GET | /api/v1/benchmark/{symbol} | Get benchmark | symbol (path) | Benchmark data |
| GET | /api/v1/watchlist | List watchlist | - | User watchlist |
| POST | /api/v1/watchlist | Add to watchlist | symbol | Add asset |
| DELETE | /api/v1/watchlist/{symbol} | Remove from watchlist | symbol (path) | Remove asset |
| GET | /api/v2/portfolio | Portfolio (v2) | - | Versioned endpoint |

## Notable Patterns

### 1. Guards - Permission-Based Authorization
- `HasPermissionGuard` - Custom guard for permission checking
- `AuthGuard('jwt')` - Passport JWT authentication
- Permission decorators (`@HasPermission(...)`)
- Files: `/apps/api/src/guards/`, `/apps/api/src/decorators/`

### 2. Interceptors - Custom Data Transformation
- `PerformanceLoggingInterceptor` - Request performance monitoring
- `RedactValuesInResponseInterceptor` - Sensitive data masking (account balances, values)
- `TransformDataSourceInRequestInterceptor` - Request data normalization
- `TransformDataSourceInResponseInterceptor` - Response data transformation
- Files: `/apps/api/src/interceptors/`

### 3. DTOs & Validation Pipes
- Comprehensive DTOs with class-validator decorators
- `@IsString`, `@IsNumber`, `@IsEnum`, `@IsOptional`, `@IsDate`, `@IsArray`
- Custom validators (`@IsAfter1970`, `@IsCurrencyCode`)
- Global `ValidationPipe` with whitelist and transform
- Files: `/apps/api/src/app/**/*.dto.ts`

### 4. Custom Decorators
- `@HasPermission(permission: string)` - Permission requirement
- `@Public()` - Public endpoint marker
- Files: `/apps/api/src/decorators/`

### 5. API Versioning
- `@Version('1')` and `@Version('2')` decorators
- Multiple API versions for backward compatibility
- Files: Controllers with versioned endpoints

### 6. Modular Architecture
- 60+ feature modules
- 62+ services
- 32+ controllers
- Clean separation of concerns (module → controller → service → repository)
- Files: `/apps/api/src/app/` module directories

### 7. Pagination & Filtering
- Query parameters: `skip`, `take` for pagination
- Complex filtering: `accounts`, `assetClasses`, `tags`, `range`
- Cursor-based and offset-based patterns
- Files: Activity, portfolio endpoints

### 8. Authentication & Authorization
- JWT-based authentication with Passport
- Anonymous user support (guest access)
- User impersonation for admin
- Access token management (API keys)
- Files: `/apps/api/src/app/auth/`, `/apps/api/src/guards/`

### 9. Import/Export Functionality
- CSV import with validation
- JSON import
- Activity export with streaming
- Files: `/apps/api/src/app/import/`, `/apps/api/src/app/export/`

### 10. Service Layer Pattern
- Clear separation: Controller → Service → Repository
- Dependency injection throughout
- Business logic in services
- Data access in repositories
- Files: All `*.service.ts` files

### 11. Queue Management
- Background job processing (market data, portfolio calculations)
- Admin queue control (cleanup, retry)
- Files: `/apps/api/src/app/admin/`

### 12. Caching Strategy
- Redis caching
- Cache flush endpoints (admin)
- Configurable caching
- Files: Cache configuration in services

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `90 <= len(result.endpoints) <= 130` (versioned endpoints may increase count)
- HTTP methods: GET, POST, PUT, DELETE present
- Path parameters extracted correctly (`{id}`, `{symbol}`, `{dataSource}`)
- NestJS route patterns detected (`@Controller()`, `@Get()`, `@Post()`, etc.)
- Multiple modules detected
- Source tracking present

**Known Edge Cases:**
1. API versioning (`@Version('1')`, `@Version('2')`) - may create duplicate paths with version prefix
2. Monorepo structure - need to target `/apps/api/` directory
3. Guards and Interceptors - should not be extracted as endpoints
4. Pipes and DTOs - validation logic, not endpoints
5. Complex query parameters - filtering may not be fully captured
6. Impersonation feature - may have special routing
7. Public vs authenticated endpoints - `@Public()` decorator
8. Nested module paths - proper path composition from module prefix

## Special Considerations

### Dependencies
- Database: PostgreSQL (via Prisma)
- Cache: Redis
- Runtime: Node.js 20+
- TypeScript 5.x
- NestJS 10.x
- Prisma ORM
- Passport JWT

### Monorepo Structure
```
ghostfolio/
├── apps/
│   ├── api/              # NestJS backend (TARGET FOR EXTRACTION)
│   └── client/           # Angular frontend
├── libs/                 # Shared libraries
└── prisma/              # Database schema
```

**Extraction Path:** `/apps/api/` (not root directory)

### Excluded Files/Directories
- Tests: `*.spec.ts`, `*.e2e-spec.ts`
- Client: `apps/client/` (Angular app)
- Libs: `libs/` (shared code)
- Build: `dist/`, `.cache/`
- Dependencies: `node_modules/`
- Config: `.env`, `*.config.js`

### Extractor Challenges
1. **Monorepo detection** - Must extract from `/apps/api/` subdirectory
2. **API versioning** - `@Version()` decorator may create version prefixes
3. **Module prefixes** - `@Controller('prefix')` at module level
4. **Guards as metadata** - Should not extract Guards/Interceptors as endpoints
5. **DTO imports** - Don't mistake DTO classes for route definitions
6. **Dependency injection** - Service imports in constructors
7. **Path parameter format** - NestJS `:param` to OpenAPI `{param}` conversion
8. **Prisma imports** - Don't extract Prisma client calls as routes

## Integration Test Plan

### Test File
`tests/integration/test_realworld_nestjs_ghostfolio.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert 90 <= len(result.endpoints) <= 130

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.DELETE in methods

# Portfolio endpoints
paths = {ep.path for ep in result.endpoints}
assert any("portfolio" in p for p in paths)
assert any("portfolio/details" in p for p in paths)
assert any("portfolio/performance" in p for p in paths)

# Activity/order endpoints
assert any("order" in p for p in paths)

# Account endpoints
assert any("account" in p for p in paths)

# User endpoints
assert any("user" in p for p in paths)

# Admin endpoints
admin_endpoints = [ep for ep in result.endpoints if "admin" in ep.path]
assert len(admin_endpoints) >= 10

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 20

# API versioning
versioned_endpoints = [ep for ep in result.endpoints if "/v1/" in ep.path or "/v2/" in ep.path]
assert len(versioned_endpoints) >= 80  # Most endpoints versioned

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".ts")
    assert "apps/api/" in ep.source_file  # Monorepo structure
    assert ep.source_line is not None
    assert ep.source_line > 0

# Multiple methods per path
path_methods = {}
for ep in result.endpoints:
    if ep.path not in path_methods:
        path_methods[ep.path] = set()
    path_methods[ep.path].add(ep.method)

multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
assert len(multi_method_paths) >= 10
```

### Key Validations
1. Portfolio management endpoints
2. Activity/transaction CRUD
3. Account management endpoints
4. User and authentication endpoints
5. Admin operation endpoints
6. Asset search and market data
7. Import/export functionality
8. API versioning (`/v1/`, `/v2/`)
9. Path parameter extraction
10. Source file tracking (monorepo `/apps/api/`)
11. Multiple HTTP methods per path
12. All CRUD methods present

## Notes

### Monorepo Consideration
The extractor must target the `/apps/api/` subdirectory specifically, as the repository is an Nx monorepo with multiple applications. The frontend (`apps/client/`) should be ignored.

### API Versioning
Ghostfolio uses NestJS `@Version()` decorator, which may result in paths like:
- `/v1/portfolio`
- `/v2/portfolio`

The extractor should handle versioned routes correctly.

### Production Usage
- **Live service:** https://ghostfol.io
- **Self-hosting:** Docker images available
- **Community:** Active Slack, social media presence
- **Premium tier:** Subscription-based revenue model
- **Real users:** Managing actual financial portfolios

### Architecture Insights
- Nx monorepo with workspace organization
- Clear module boundaries (portfolio, account, order, admin, etc.)
- Service-oriented architecture with dependency injection
- Prisma ORM for type-safe database access
- Redis caching for performance
- Background job processing for data updates
- PDF generation for reports
- Export streaming for large datasets

### Diversity from Existing Repos
This repository provides maximum contrast with existing test fixtures:
- **Domain:** FinTech (portfolio/wealth management) vs blogging, multi-service hub
- **Patterns:** Guards, Interceptors, custom decorators vs simpler auth
- **Complexity:** High (financial calculations, market data) vs Medium
- **Architecture:** Monorepo vs standard structure
- **Data Model:** Complex (assets, accounts, activities, users) vs simpler entities
