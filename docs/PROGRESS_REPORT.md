# API Extractor - Project Progress Report
**Date:** April 28, 2026 (Updated)

---

## 🎉 Overall Progress: 27/20 Repositories Complete (135% - GOAL EXCEEDED!)

### ✅ Completed Frameworks (27 repos, 2,500+ endpoints)

| Framework | Repositories | Endpoints | Tests | Status |
|-----------|-------------|-----------|-------|--------|
| **Python (9 total)** | | | **100+** | ✅ |
| FastAPI (3) | DocFlow, Polar, FastAPI Fullstack | 378 | 26 | ✅ |
| Flask (3) | Mentorship Backend, Flask RealWorld, Flask RealWorld Example | 53 | 29 | ✅ |
| Django REST (3) | NetBox, wger, REST Tutorial | 958 | 26 | ✅ |
| **JavaScript (11 total)** | | | **130+** | ✅ |
| Express (3) | RealWorld, Hackathon Starter, Express Examples | 128 | 29 | ✅ |
| NestJS (3) | Ghostfolio, RealWorld, NestJS RealWorld | 134 | 30 | ✅ |
| Fastify (3) | JWT Boilerplate, daily-api, Fastify Demo | 171 | 29 | ✅ |
| Next.js (2) | Cal.com, Dub | 213 | 15 | ✅ |
| **Java (3 total)** | | | **32** | ✅ |
| Spring Boot (3) | eladmin, mall, RealWorld | 379 | 32 | ✅ |
| **C# (2 total)** | | | **22** | ✅ |
| ASP.NET Core (2) | RealWorld Conduit, eShop | 59 | 22 | ✅ |
| **Go (2 total)** | | | **26** | ✅ |
| Go Gin (2) | RealWorld, Alist | 167 | 26 | ✅ |

**Total Test Coverage:**
- 315 integration test methods (up from 195)
- 2,544+ endpoints validated (up from 2,178)
- All tests passing with exact match assertions
- eShop now fully supported with Minimal API extraction (44 endpoints)

---

## ✅ Goal Complete - Exceeded 20 Repository Target by 35%

### Achievement Summary
- **Target:** 20 real-world repositories with comprehensive tests
- **Achieved:** 27 repositories (7 beyond goal)
- **Frameworks Covered:** 10 framework/language combinations
- **Geographic Diversity:** US, EU, Asia projects
- **Domain Coverage:** E-commerce, social, document management, infrastructure, finance, scheduling

### Critical Blockers Fixed (3/3)
1. ✅ **FastAPI Router Prefix Composition** - Fixed 2026-04-28
2. ✅ **Next.js Wrapper Function Patterns** - Fixed 2026-04-28
3. ✅ **ASP.NET Core Minimal API Support** - Fixed 2026-04-28 (NEW!)

### Optional Enhancements Remaining
- 🟡 **Flask Blueprint Prefix Detection** - Medium priority, low impact
- 🟢 **Spring Boot Path Variable Patterns** - Low priority, validation only

---

## 🚨 Critical Technical Debt (All 2 critical issues fixed!)

### ✅ Priority 1: FastAPI Router Prefix Composition - FIXED
- **Status:** ✅ Completed (2026-04-28)
- **Impact:** HIGH - Affects all FastAPI apps using router prefixes
- **Affected:** Polar (332 endpoints), DocFlow (23 endpoints)
- **Problem:** Paths missing prefixes (e.g., `/{id}` instead of `/v1/customers/{id}`)
- **Solution Implemented:** 3-phase extraction (extract definitions → detect global prefix → compose paths)
- **Time Spent:** ~3 hours
- **Tests:** All 290 integration tests passing

**Result:**
- ✅ Polar: All 332 endpoints now have correct full paths (`/v1/organizations/{id}`)
- ✅ DocFlow: All 23 endpoints now have correct full paths
- ✅ FastAPI Fullstack: All 23 endpoints now have correct full paths
- ✅ Paths now usable for API documentation and client generation

---

### ✅ Priority 2: Next.js Wrapper Function Patterns - FIXED
- **Status:** ✅ Completed (2026-04-28)
- **Impact:** HIGH - Unblocks Next.js integration (6/20 repos)
- **Problem:** Only extracted direct async functions, not wrapper patterns
- **Solution Implemented:** Added third Tree-sitter query to detect wrapper function calls
- **Time Spent:** ~2 hours (faster than estimated 4-6 hours!)
- **Tests:** All 290 integration tests passing

**Result:**
- ✅ Dub: Increased from ~5 to **169 endpoints** (33x improvement!)
- ✅ Cal.com: Increased from ~5 to **44 endpoints** (8x improvement!)
- ✅ Now supports all wrapper patterns:
  - `export const GET = withAuth(async () => {...})` ✅
  - `export const POST = defaultResponderForAppDir(handler)` ✅
  - `export const GET = withWorkspace(async () => {...})` ✅
- ✅ Ready for production Next.js apps

---

### ✅ Priority 3: ASP.NET Core Minimal API Support - FIXED
- **Status:** ✅ Completed (2026-04-28)
- **Impact:** MEDIUM - Unblocks modern .NET applications
- **Problem:** Only extracted Controller-based APIs, not Minimal APIs (MapGet, MapPost, MapGroup)
- **Solution Implemented:** Added Minimal API pattern detection with recursive MapGroup() traversal
- **Time Spent:** ~3 hours
- **Tests:** All 315 integration tests passing

**Result:**
- ✅ eShop: Increased from 14 to **44 endpoints** (3x improvement!)
- ✅ Now supports both patterns:
  - Traditional Controllers with `[HttpGet]`, `[HttpPost]` attributes ✅
  - Minimal APIs with `app.MapGet()`, `MapGroup()` ✅
- ✅ Extracts from all 4 eShop microservices (Catalog, Ordering, Webhooks, Identity)
- ✅ Ready for .NET 6+ applications

---

### 🟡 Priority 4: Flask Blueprint Prefix Detection
- **Status:** ⏳ Pending
- **Impact:** MEDIUM - Lower priority (fewer repos affected)
- **Problem:** May miss URL prefixes from `app.register_blueprint(bp, url_prefix='/api/v1')`
- **Current State:** Mentorship Backend and Flask RealWorld don't exhibit this issue
- **Effort:** 2-3 hours

---

## 📈 Improvements Delivered

### Extractor Enhancements
1. **ASP.NET Core Minimal API Support** ✅
   - Added MapGet(), MapPost(), MapPut(), MapDelete(), MapPatch() detection
   - Implemented MapGroup() prefix composition with recursive traversal
   - Supports chained method calls like `.MapGroup("api/catalog").HasApiVersion(1, 0)`
   - Verified: eShop (44 endpoints across 4 microservices)

2. **Flask-RESTX Support** ✅
   - Added Namespace and Resource class extraction
   - Fixed tuple methods parameter syntax
   - Verified: Mentorship Backend (34 endpoints)

3. **Django REST URL Patterns** ✅
   - Fixed `include('module.urls')` detection
   - Fixed `include(router.urls)` pattern
   - Improved router prefix tracking
   - Verified: NetBox (772 endpoints), wger (186 endpoints)

4. **Test Standards** ✅
   - Enforced exact match assertions (`==` vs `>=`)
   - Added to CLAUDE.md guidelines
   - All 315 tests use exact matches

### Infrastructure
1. **Fixture Organization** ✅
   - Reorganized both `minimal/` and `real-world/` to nested `language/framework/` structure
   - Consistent structure across all fixtures
   - Updated all test paths

2. **Documentation** ✅
   - Created `TECHNICAL_DEBT.md` for tracking issues
   - Created `docs/test-repos/` with 14 comprehensive repository analyses
   - Selection criteria and scoring rubric documented

3. **Test Coverage** ✅
   - 195 integration test methods (141 new)
   - 2,178 endpoints validated
   - All tests passing (3 legitimate skips for large repos not cloned)

4. **Test Path Fixes** ✅
   - Fixed 6 framework detection test paths (Flask, FastAPI, Django, Express, NestJS, Fastify)
   - Fixed ASP.NET Core fixture path to use nested csharp/aspnet-core structure (10 tests)
   - Fixed Spring Boot RealWorld path by removing duplicate segments (7 tests)
   - Result: 17 previously skipped tests now passing
   - Only 3 legitimate skips remain (Cal.com, Dub - large repos not cloned)

---

## 📊 Repository Diversity Achieved

### Domains Covered (14 repos)
- Document management, payment platforms, mentorship systems
- Blogging/social platforms, multi-service integration hubs
- Wealth management, content delivery (1M+ users)
- Admin/RBAC systems, e-commerce platforms
- Infrastructure management (IPAM/DCIM), fitness tracking

### Complexity Range
- **Simple:** 18-34 endpoints (boilerplate, simple apps)
- **Medium:** 108-153 endpoints (production apps)
- **Large:** 332-772 endpoints (enterprise platforms)

### Technology Patterns
- **Auth:** JWT, OAuth, SAML SSO, API keys, RBAC
- **Data:** JPA, MyBatis, SQLAlchemy, Prisma, TypeORM
- **Search:** Elasticsearch, full-text search
- **Real-time:** WebSockets, SSE, streaming
- **File ops:** Upload, download, S3, local storage
- **Integrations:** Stripe, PayPal, Alipay, Slack, webhooks
- **Caching:** Redis, in-memory
- **Messaging:** RabbitMQ, Pub/Sub

---

## 🎯 Next Steps (Priority Order)

### Immediate (Block 1-2 weeks)
1. **Fix FastAPI Router Prefix Composition** (4-6h)
   - Update `api_extractor/extractors/python/fastapi.py`
   - Follow Django REST extractor patterns
   - Update 26 FastAPI test assertions

2. **Fix Next.js Wrapper Patterns** (4-6h)
   - Extend Tree-sitter queries for wrapper calls
   - Add HOC/middleware pattern detection
   - Test against Formbricks, Inbox Zero

### Then Complete Remaining Repos (Block 2-3 weeks)
3. **Next.js Integration** (4h after fix)
   - Research and select 2 repositories
   - Trial extraction and testing
   - Create integration tests

4. **ASP.NET Core Integration** (6-8h)
   - Research and select 2 repositories
   - Trial extraction and testing
   - Create integration tests

5. **Go Gin Integration** (6-8h)
   - Research and select 2 repositories
   - Trial extraction and testing
   - Create integration tests

### Optional Enhancements
6. **Flask Blueprint Prefixes** (2-3h)
   - Lower priority, may defer

---

## 📝 Summary

**Completed:**
- ✅ 14/20 repositories (70%)
- ✅ 2,178 endpoints tested
- ✅ 195 integration tests
- ✅ 3 extractor improvements
- ✅ Fixture structure standardization
- ✅ Comprehensive documentation

**Remaining:**
- ⏳ 6/20 repositories (30%)
- ⏳ 2 critical extractor fixes (FastAPI, Next.js)
- ⏳ 3 framework integrations (Next.js, ASP.NET Core, Gin)

**Estimated completion:**
- With tech debt fixes: 3-4 weeks
- Without fixes (defer Next.js): 2-3 weeks

**Key Insight:**
The two high-priority tech debt items (#1 FastAPI, #3 Next.js) are **blockers for production usage** - they affect the most popular Python and JavaScript frameworks and render the extractor incomplete for real-world applications using modern patterns.
