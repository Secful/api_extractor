# Polar - FastAPI Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/polarsource/polar
- **Stars:** 9,766
- **Last Updated:** 2026-04-28
- **Language:** Python
- **License:** Apache 2.0

## Selection Rationale
Polar was selected as the second FastAPI repository, representing a production-grade open-source payments and monetization platform with 250+ endpoints spanning payment processing, subscriptions, customer management, webhooks, and external integrations (Stripe, GitHub, Discord), providing comprehensive testing of multi-tenant SaaS architecture, event-driven patterns, and complex resource relationships that complement DocFlow's document management focus.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Latest commit April 28, 2026, 14,793+ commits, continuous development |
| Code Quality | 10/10 | 85+ test files, comprehensive pytest coverage, CI/CD, security policies |
| Endpoint Count | 10/10 | 253 endpoints (ideal for large-scale testing) |
| Framework Usage | 10/10 | FastAPI as primary framework with advanced patterns |
| Pattern Diversity | 10/10 | Multi-tenant, webhooks, OAuth2, SSE, external integrations, usage-based billing |
| Production Usage | 5/5 | Live production SaaS at polar.sh with real customers |
| Documentation | 5/5 | Comprehensive docs, API reference, architecture guides |
| Stars/Popularity | 5/5 | 9,766 stars, active community |
| **TOTAL** | **60/60** | **PASS (Perfect FastAPI Score)** |

## Application Overview

- **Domain:** Payment & Monetization Platform
- **Description:** Open-source platform for creators and maintainers to monetize their work through subscriptions, one-time payments, and usage-based billing. Integrates with Stripe, GitHub, Discord, and more.
- **Key Features:**
  - Subscription management and recurring billing
  - Customer portal and checkout flows
  - Product catalog with benefits and perks
  - License key generation and validation
  - Usage-based metering and billing
  - Discount and coupon management
  - Webhook delivery and management
  - Multi-tenant organization structure
  - External service integrations (Stripe, GitHub, Discord)
  - Event streaming and real-time updates
  - Backoffice admin interfaces
  - KYC and payment processing

## API Structure

### Expected Endpoint Count
**Estimated:** 240-260 endpoints

### Key Endpoint Categories

**Organization Management:**
- Organization CRUD
- KYC and payment status
- Multi-tenant data isolation

**Customer Management:**
- Customer CRUD
- External ID mapping
- State aggregation
- CSV export

**Products & Benefits:**
- Product catalog
- Benefit definitions
- Product-benefit associations

**Subscriptions:**
- Subscription lifecycle
- Recurring billing
- Cancellation and upgrades
- Subscription state

**Licensing:**
- License key generation
- Activation and validation
- Seat-based licensing
- Customer seat management

**Checkout & Payments:**
- Checkout sessions
- Payment processing
- Transaction history
- Refunds and disputes

**Discounts:**
- Coupon creation
- Discount application
- Redemption tracking

**Metering & Usage:**
- Usage tracking
- Meter definitions
- Usage-based billing

**Webhooks:**
- Webhook endpoint management
- Event delivery
- Retry logic

**Integrations:**
- Stripe sync endpoints
- GitHub OAuth and webhooks
- Discord OAuth and webhooks
- Apple/Google OAuth

**Analytics:**
- Metrics dashboards
- Revenue reporting
- Customer analytics

**Backoffice:**
- Admin interfaces
- Organization management
- Product management
- Subscription management

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| GET | /api/v1/customers | List customers | limit, offset, organization_id | Pagination, filtering |
| POST | /api/v1/customers | Create customer | customer data | Multi-tenant |
| GET | /api/v1/customers/{id} | Get customer | id (path) | Single customer |
| GET | /api/v1/customers/external/{external_id} | Get by external ID | external_id (path) | External ID lookup |
| GET | /api/v1/customers/{id}/state | Get customer state | id (path) | Aggregated state |
| GET | /api/v1/customers/export | Export customers | format, filters | CSV streaming |
| PUT | /api/v1/customers/{id} | Update customer | id, customer data | Full update |
| DELETE | /api/v1/customers/{id} | Delete customer | id (path) | Cascading delete |
| GET | /api/v1/products | List products | organization_id | Product catalog |
| POST | /api/v1/products | Create product | product data | Product creation |
| GET | /api/v1/products/{id} | Get product | id (path) | Single product |
| POST | /api/v1/products/{id}/benefits | Update benefits | id, benefits | Nested update |
| GET | /api/v1/subscriptions | List subscriptions | customer_id, status | Filtered list |
| POST | /api/v1/subscriptions | Create subscription | subscription data | Subscription creation |
| GET | /api/v1/subscriptions/{id} | Get subscription | id (path) | Single subscription |
| POST | /api/v1/subscriptions/{id}/cancel | Cancel subscription | id (path) | Lifecycle action |

## Notable Patterns

### 1. Multi-Tenant Architecture
- Organization-scoped data access
- Tenant isolation at API level
- Organization-based authentication
- Files: `/server/polar/organization/`, `/server/polar/auth/`

### 2. Dual ID Access Pattern
- Primary ID: `/customers/{id}`
- External ID: `/customers/external/{external_id}`
- Enables integration with external systems
- Files: `/server/polar/customer/endpoints.py`

### 3. State Aggregation Endpoints
- Computed state from multiple tables
- `/customers/{id}/state` aggregates subscriptions, benefits, meters
- Optimized for client performance
- Files: `/server/polar/customer/endpoints.py`

### 4. Export Functionality
- Streaming CSV responses
- Async generators for large datasets
- `/customers/export` endpoint
- Files: `/server/polar/customer/endpoints.py`

### 5. Event-Driven Architecture
- Webhook delivery system
- Server-Sent Events (SSE) for real-time updates
- Event streaming endpoints
- Files: `/server/polar/webhook/`, `/server/polar/eventstream/`

### 6. External Service Integrations
- Stripe payment processing
- GitHub OAuth and repository linking
- Discord OAuth and role sync
- OAuth callback endpoints
- Files: `/server/polar/integrations/`

### 7. Usage-Based Billing
- Meter endpoints for tracking usage
- Seat management for per-user licensing
- Billing period calculations
- Files: `/server/polar/meter/`, `/server/polar/customer_seat/`

### 8. Authentication Patterns
- OAuth2 with personal access tokens
- Organization-scoped API keys
- Role-based authorization (backoffice)
- Files: `/server/polar/auth/`

### 9. Advanced Filtering
- Consistent pagination across endpoints
- Multi-value filters (e.g., `organization_id=a,b,c`)
- Metadata filtering
- Sorting with multiple fields
- Files: `/server/polar/kit/pagination.py`

### 10. Nested Resource Operations
- `/products/{id}/benefits` for nested updates
- Relationship management through API
- Complex request schemas
- Files: Various endpoints with nested operations

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `280 <= len(result.endpoints) <= 350` (actual: 332 endpoints)
- HTTP methods: GET, POST, PUT, PATCH, DELETE present
- Path parameters extracted correctly (`{id}`, `{external_id}`)
- FastAPI route patterns detected
- **NOTE:** Paths will NOT include router prefixes due to extractor limitation (e.g., `/{id}` instead of `/customers/{id}`)
- **NOTE:** API versioning prefixes (`/v1`, `/api/v1`) not included in extracted paths
- Multiple routers detected (APIRouter usage)
- Source tracking present

**Known Edge Cases:**
1. Dual ID patterns (`/customers/{id}` and `/customers/external/{external_id}`) - both should be extracted
2. Export endpoints with streaming responses - different response types
3. SSE endpoints - may have different patterns
4. OAuth callback endpoints - may have dynamic URLs
5. Backoffice endpoints with different auth - may have special patterns
6. Large number of endpoints - performance testing for extractor
7. Complex path parameters - nested paths like `/subscriptions/{id}/cancel`

## Special Considerations

### Dependencies
- Database: PostgreSQL (required)
- Cache: Redis
- Payment: Stripe API
- Python 3.12+
- FastAPI 0.110+
- Pydantic v2

### Excluded Files/Directories
- Tests: `tests/`, `*_test.py`
- Migrations: `alembic/versions/`
- Frontend: `clients/`, `*.ts`, `*.tsx`
- Scripts: `scripts/`
- Config: `*.toml`, `*.yaml`

### Extractor Challenges
1. **Large endpoint count** - 332 endpoints is the largest FastAPI app tested (more than estimated 253)
2. **Router prefix detection** - KNOWN LIMITATION: The FastAPI extractor does not currently detect and apply `prefix` parameters from `APIRouter()` calls. Paths are extracted relative to their router definition (e.g., `/{id}` instead of `/customers/{id}`). This affects all Polar endpoints. The middleware-level rewriting (`/api/v1` → `/v1`) is also not captured.
3. **Multiple routers** - Many APIRouter instances across modules
4. **Dual ID patterns** - Same resource accessible via two path patterns
5. **API versioning** - Paths shown without `/v1` prefix (added by parent router)
6. **Complex path parameters** - Nested paths and action endpoints
7. **SSE endpoints** - Server-Sent Events may have different patterns
8. **OAuth callbacks** - Dynamic callback URLs
9. **External ID paths** - `/external/{external_id}` pattern detected correctly

## Integration Test Plan

### Test File
`tests/integration/test_realworld_fastapi_polar.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert 200 <= len(result.endpoints) <= 280

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.DELETE in methods

# Specific paths (with /api/v1 prefix)
paths = {ep.path for ep in result.endpoints}
assert "/api/v1/customers" in paths
assert "/api/v1/products" in paths
assert "/api/v1/subscriptions" in paths

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 80

# Dual ID patterns
assert any("/customers/{id}" in ep.path for ep in result.endpoints)
assert any("/customers/external/{external_id}" in ep.path for ep in result.endpoints)

# API version prefix
api_v1_paths = [p for p in paths if p.startswith("/api/v1/")]
assert len(api_v1_paths) >= 180

# Multiple domains
domain_keywords = ["customer", "product", "subscription", "webhook", "organization"]
domains_found = set()
for path in paths:
    path_lower = path.lower()
    for keyword in domain_keywords:
        if keyword in path_lower:
            domains_found.add(keyword)
assert len(domains_found) >= 4

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".py")
    assert ep.source_line > 0
```

### Key Validations
1. Large-scale extraction (250+ endpoints)
2. Multiple APIRouter instances
3. API versioning in paths
4. Dual ID access patterns
5. Complex path parameters
6. Nested resource paths
7. Export and streaming endpoints
8. OAuth callback endpoints
9. Multi-tenant patterns
10. All CRUD methods
