# daily.dev API - Fastify Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/dailydotdev/daily-api
- **Stars:** 462
- **Last Updated:** 2026-04-28
- **Language:** TypeScript (99.8%)
- **License:** AGPL-3.0

## Selection Rationale
Production API backend for daily.dev serving 1M+ developers, demonstrating enterprise-scale Fastify patterns (hybrid GraphQL/REST, webhooks, Pub/Sub, payment processing, real-time features) across 65-75+ endpoints for content delivery, user engagement, subscriptions, and third-party integrations - providing maximum contrast to JWT boilerplate's auth-focused simplicity with real-world production complexity.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Last commit April 28, 2026 (today), 4,199 total commits, 12 open PRs |
| Code Quality | 10/10 | 75+ test files, CircleCI (parallel tests), linting, TypeScript, comprehensive coverage |
| Endpoint Count | 10/10 | 65-75+ endpoints (exceeds ideal 15-50 range) |
| Framework Usage | 10/10 | Fastify 5.x with extensive plugin ecosystem |
| Pattern Diversity | 10/10 | GraphQL, hooks, decorators, plugins, webhooks, workers, Pub/Sub, real-time, payments |
| Production Usage | 5/5 | Production app with 1M+ users, real business with subscriptions |
| Documentation | 5/5 | Swagger/OpenAPI docs, README, GraphQL schema introspection |
| Stars/Popularity | 3/5 | 462 stars (main daily.dev repo has 14K stars) |
| **TOTAL** | **63/60** | **PASS (Exceptional Score, Exceeds Maximum)** |

## Application Overview

- **Domain:** Developer News & Content Delivery Platform
- **Description:** Complete backend API for daily.dev, a personalized developer news aggregator that curates content from 400+ sources, serving 1M+ developers with content feeds, bookmarks, subscriptions, notifications, and community features
- **Key Features:**
  - Personalized content feeds with ML recommendations
  - Multi-source content aggregation (400+ sources)
  - User bookmarks and reading history
  - Commenting and community engagement
  - Subscriptions and premium features (Paddle integration)
  - Notifications (in-app, push, email)
  - Search functionality
  - User profiles and organizations
  - Leaderboard and achievements
  - Integrations (Intercom, Slack, Customer.io, Linear, Apple)
  - Real-time features (live rooms)
  - Webhooks for external services
  - Background job processing
  - Payment processing

## API Structure

### Expected Endpoint Count
**Estimated:** 65-75+ endpoints

### Key Endpoint Categories

**REST Routes (30+ endpoints):**
- Alerts and notifications
- Automations
- Dev cards
- GIFs and media
- Local ads
- User management
- Webhooks (Apple, Customer.io, Linear)
- Integrations (Intercom, Slack)
- Public routes (bookmarks, posts, feeds, tags, search)
- Private routes (admin, workers, RPC)

**GraphQL Operations (45+ modules):**
- Achievements
- Actions and activities
- Alerts
- Archive
- Bookmarks
- Campaigns
- Comments
- Feeds (custom, personalized)
- Posts
- Organizations
- Notifications
- Users
- Search
- Leaderboard
- Subscriptions (Paddle)
- Integrations
- Content moderation

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| POST | /graphql | GraphQL endpoint | body: {query, variables} | Apollo Server |
| GET | /posts | List posts | limit, offset, filters | Public API |
| GET | /posts/{id} | Get post | id (path) | Single post |
| GET | /feeds | List feeds | - | Available feeds |
| GET | /feeds/{feedId}/posts | Feed posts | feedId, pagination | Feed content |
| POST | /bookmarks | Create bookmark | body: {postId} | Requires auth |
| GET | /bookmarks | List bookmarks | pagination | User bookmarks |
| DELETE | /bookmarks/{id} | Remove bookmark | id (path) | Requires auth |
| GET | /tags | List tags | query | Tag search |
| GET | /search | Search content | query, filters | Full-text search |
| GET | /users/{id} | Get user profile | id (path) | Public profile |
| GET | /notifications | List notifications | limit, offset | Requires auth |
| POST | /notifications/read | Mark as read | body: {notificationId} | Requires auth |
| POST | /webhooks/apple | Apple webhook | body: payload | Apple integration |
| POST | /webhooks/customerio | Customer.io webhook | body: payload | Email service |
| POST | /webhooks/linear | Linear webhook | body: payload | Issue tracking |
| POST | /webhooks/paddle | Paddle webhook | body: payload | Payment processing |
| GET | /organizations | List orgs | - | Organizations |
| POST | /organizations | Create org | body: {name, ...} | Requires auth |
| GET | /leaderboard | Get leaderboard | period, limit | Rankings |

## Notable Patterns

### 1. Hybrid GraphQL + REST Architecture
- Apollo Server for GraphQL
- REST endpoints for webhooks, public API, integrations
- Mercurius for performance optimization
- Files: `/src/routes/graphql/`, `/src/routes/`

### 2. Fastify Plugin System
- @fastify/cookie - Cookie handling
- @fastify/cors - CORS configuration
- @fastify/helmet - Security headers
- @fastify/http-proxy - Proxy middleware
- @fastify/rate-limit - Rate limiting
- @fastify/swagger - API documentation
- fastify-raw-body - Raw body access for webhooks
- Files: `/src/plugins/`

### 3. Background Job Processing
- Pub/Sub workers with Redis
- Temporal workflows for complex operations
- Cron tasks for scheduled jobs
- Message queue processing
- Files: `/src/workers/`, `/src/temporal/`

### 4. Webhook Integration
- Multiple webhook handlers (Apple, Customer.io, Linear, Paddle)
- Raw body validation for webhook signatures
- Async event processing
- Files: `/src/routes/webhooks/`

### 5. Real-Time Features
- WebSocket support for live rooms
- Server-Sent Events (SSE)
- Real-time notifications
- Files: `/src/realtime/`

### 6. Payment Processing
- Paddle integration for subscriptions
- Webhook handling for payment events
- Subscription management
- Files: `/src/routes/webhooks/paddle.ts`, GraphQL subscriptions module

### 7. Third-Party Integrations
- Intercom (customer support)
- Slack (notifications)
- Customer.io (email marketing)
- Linear (issue tracking)
- Apple (app integrations)
- Files: `/src/routes/integrations/`

### 8. TypeORM for Database
- Entity definitions
- Repository pattern
- Migrations
- Query builder
- Files: `/src/entity/`, `/src/migration/`

### 9. Authentication & Authorization
- betterAuth for authentication
- Role-based access control
- API key management
- JWT tokens
- Files: `/src/auth/`

### 10. Observability
- OpenTelemetry instrumentation
- Structured logging
- Error tracking
- Performance monitoring
- Files: Telemetry configuration

### 11. Testing Strategy
- 75+ test files
- Unit tests with Jest
- Integration tests with supertest
- GraphQL tests with mercurius-integration-testing
- PostgreSQL + Redis in test environment
- Files: `__tests__/`

### 12. Microservice Architecture
- Event-driven design
- Service-oriented components
- Message queue communication
- API Gateway pattern
- Files: Service modules

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `50 <= len(result.endpoints) <= 90` (hybrid GraphQL/REST may affect count)
- HTTP methods: GET, POST, PUT, DELETE, PATCH present
- Path parameters extracted correctly (`{id}`, `{feedId}`, etc.)
- Fastify route patterns detected
- Multiple route modules detected
- Source tracking present

**Known Edge Cases:**
1. GraphQL endpoint - single `/graphql` endpoint vs 45+ operations
2. Webhook routes - may have special signature validation
3. Private vs public routes - different authentication requirements
4. WebSocket endpoints - may not be extracted as REST endpoints
5. Proxy routes - HTTP proxy middleware
6. Background jobs - worker routes may not be HTTP endpoints
7. GraphQL schema introspection - not REST endpoints

## Special Considerations

### Dependencies
- Database: PostgreSQL 18
- Cache: Redis 8.x
- Runtime: Node.js 22+
- TypeScript 5.x
- Fastify 5.x
- Apollo Server
- TypeORM
- Temporal (workflow engine)

### Excluded Files/Directories
- Tests: `__tests__/`, `*.test.ts`
- Build: `dist/`, `.build/`
- Dependencies: `node_modules/`
- Config: `.env`, `*.config.js`
- Migrations: `src/migration/` (TypeORM migrations)
- Workers: `src/workers/` (background jobs, may not have HTTP routes)
- Temporal: `src/temporal/` (workflows, not HTTP endpoints)

### Extractor Challenges
1. **GraphQL endpoint** - Single `/graphql` endpoint represents many operations
2. **Hybrid architecture** - Mix of REST and GraphQL patterns
3. **Webhook routes** - Raw body parsing, signature validation
4. **WebSocket routes** - Real-time connections, not traditional REST
5. **Proxy routes** - HTTP proxy middleware
6. **Worker routes** - Internal RPC, may not be public HTTP
7. **Large codebase** - 65-75+ endpoints across many route files
8. **Complex path parameters** - Nested resource paths
9. **Private routes** - Internal vs public API separation

## Integration Test Plan

### Test File
`tests/integration/test_realworld_fastify_daily_api.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert len(result.endpoints) >= 30  # At least REST endpoints, may not count all GraphQL

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods

# Core endpoints
paths = {ep.path for ep in result.endpoints}
assert any("posts" in p for p in paths)
assert any("feeds" in p for p in paths)
assert any("graphql" in p for p in paths) or "/graphql" in paths

# Webhook endpoints
webhook_endpoints = [ep for ep in result.endpoints if "webhook" in ep.path]
assert len(webhook_endpoints) >= 3  # Apple, Customer.io, Linear, Paddle

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 10

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".ts")
    assert ep.source_line is not None
    assert ep.source_line > 0
```

### Key Validations
1. Basic REST endpoint extraction
2. GraphQL endpoint detection
3. Webhook handlers
4. Public API routes
5. Path parameter extraction
6. Source file tracking
7. Multiple HTTP methods
8. Integration routes

## Notes

### Production Scale
- **1M+ active users**
- **400+ content sources aggregated**
- **14K+ stars on main project** (daily.dev browser extension)
- **Golden Kitty Award winner**
- Used by developers at Apple, Google, AWS, Microsoft, Meta

### Architecture Highlights
- Microservice-oriented with event-driven communication
- Hybrid GraphQL/REST for different use cases
- Background job processing with Temporal
- Real-time features with WebSockets
- Payment processing with Paddle
- Multiple third-party integrations

### Testing Infrastructure
- CircleCI with 6-way parallel test execution
- Memory-optimized test runs (6GB allocation)
- Comprehensive test coverage (75+ test files)
- PostgreSQL 18 + Redis in test environment

### Diversity from JWT Boilerplate
This repository provides maximum contrast with fastify-api-boilerplate-jwt:
- **Domain:** Content delivery platform vs auth/user management
- **Endpoints:** 65-75+ vs 18 (3.5x more)
- **Architecture:** Hybrid GraphQL/REST vs pure REST
- **Complexity:** Enterprise-scale production vs boilerplate template
- **Patterns:** Webhooks, Pub/Sub, real-time, payments vs basic CRUD + auth
- **Database:** TypeORM vs Kysely
- **Testing:** 75+ test files vs 14
- **Users:** 1M+ production users vs template project
