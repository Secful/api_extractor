# Repository Selections Summary

## Overview

This document summarizes the 20 repositories selected for extended integration testing, organized by framework.

**Selection Date:** April 2026
**Total Repositories:** 20 (across 10 frameworks)
**Selection Criteria:** All repositories scored 35+/60 on comprehensive rubric

---

## Selected Repositories by Framework

### Python Frameworks (6 repositories)

#### FastAPI (2 repos)
1. **rag_api** (danny-avila/rag_api)
   - Score: 42/60
   - Domain: AI/ML - Retrieval-Augmented Generation
   - Endpoints: ~16
   - Stars: 796

2. **docflow** (jiisanda/docflow)
   - Score: 39/60
   - Domain: Document Management System
   - Endpoints: ~26
   - Stars: 267

#### Flask (2 repos)
1. **mentorship-backend** (anitab-org/mentorship-backend)
   - Score: 58/60
   - Domain: Social mentorship platform
   - Endpoints: ~33
   - Stars: 199

2. **flask-realworld-example-app** (gothinkster/flask-realworld-example-app)
   - Score: 54/60
   - Domain: Social blogging platform (RealWorld spec)
   - Endpoints: ~19
   - Stars: 903

#### Django REST Framework (2 repos)
1. **netbox** (netbox-community/netbox)
   - Score: 54/60
   - Domain: Network Infrastructure Management
   - Endpoints: 50-100+
   - Stars: 20,400+

2. **OnlineJudge** (QingdaoU/OnlineJudge)
   - Score: 46/60
   - Domain: Education / Competitive Programming
   - Endpoints: 30-50
   - Stars: 6,500+

---

### JavaScript/TypeScript Frameworks (8 repositories)

#### Express.js (2 repos)
1. **node-express-prisma-v1-official-app** (gothinkster/node-express-prisma-v1-official-app)
   - Score: 52/60
   - Domain: Social blogging platform (RealWorld spec - TypeScript + Prisma)
   - Endpoints: ~19
   - Stars: 178

2. **habitica** (HabitRPG/habitica)
   - Score: 62/60 (exceeds maximum)
   - Domain: Gamified habit tracker
   - Endpoints: 135+
   - Stars: 13,854

#### NestJS (2 repos)
1. **immich** (immich-app/immich)
   - Score: 56/60
   - Domain: Self-hosted photo and video management
   - Endpoints: ~248 (39 controllers)
   - Stars: 98,814

2. **ghostfolio** (ghostfolio/ghostfolio)
   - Score: 49/60
   - Domain: Wealth management and portfolio tracking
   - Endpoints: ~113 (33 controllers)
   - Stars: 8,284

#### Fastify (2 repos)
1. **tracearr** (connorgallopo/Tracearr)
   - Score: 48/60
   - Domain: Real-time monitoring dashboard for media servers
   - Endpoints: 35+
   - Stars: 1,785

2. **turborepo-remote-cache** (ducktors/turborepo-remote-cache)
   - Score: 43/60
   - Domain: Build cache infrastructure (Turborepo)
   - Endpoints: 5-8
   - Stars: 1,433

#### Next.js (2 repos)
1. **formbricks** (formbricks/formbricks)
   - Score: 58/60
   - Domain: Privacy-first survey and experience management
   - Endpoints: 30-50
   - Stars: 12,100+

2. **lobe-chat** (lobehub/lobe-chat)
   - Score: 52/60
   - Domain: AI workspace and agent collaboration platform
   - Endpoints: 25-40
   - Stars: 75,800+

---

### Java Frameworks (2 repositories)

#### Spring Boot (2 repos)
1. **mall** (macrozheng/mall)
   - Score: 47/60
   - Domain: E-commerce system
   - Endpoints: ~47 controllers
   - Stars: 83,500

2. **ruoyi-vue-pro** (YunaiV/ruoyi-vue-pro)
   - Score: 51/60
   - Domain: Enterprise management platform (CRM, ERP, BPM, AI)
   - Endpoints: 392+ controllers
   - Stars: 36,825

---

### C# Frameworks (2 repositories)

#### ASP.NET Core (2 repos)
1. **eShop** (dotnet/eShop)
   - Score: 48/60
   - Domain: E-commerce (microservices)
   - Endpoints: 30-50
   - Stars: 10,400

2. **dotnet-webapi-boilerplate** (fullstackhero/dotnet-webapi-boilerplate)
   - Score: 45/60
   - Domain: Multi-tenant SaaS/Enterprise platform
   - Endpoints: 20-40
   - Stars: 6,400

---

### Go Frameworks (2 repositories)

#### Gin (2 repos)
1. **alist** (AlistGo/alist)
   - Score: 51/60
   - Domain: File management and WebDAV server
   - Endpoints: ~164
   - Stars: 49,375

2. **paopao-ce** (rocboss/paopao-ce)
   - Score: 47/60
   - Domain: Micro-blogging social community platform
   - Endpoints: ~75
   - Stars: 4,494

---

## Diversity Analysis

### Domain Distribution
- **E-commerce:** 3 repos (mall, eShop, implied in some admin systems)
- **Social/Community:** 4 repos (flask-realworld, habitica, paopao-ce, lobe-chat)
- **Infrastructure/DevOps:** 3 repos (netbox, turborepo-remote-cache, alist)
- **Education/Learning:** 1 repo (OnlineJudge)
- **Content Management:** 3 repos (docflow, tracearr, immich)
- **Finance/Business:** 2 repos (ghostfolio, ruoyi-vue-pro)
- **AI/ML:** 2 repos (rag_api, lobe-chat)
- **Enterprise/SaaS:** 2 repos (dotnet-webapi-boilerplate, formbricks)

### Complexity Distribution
- **Simple (10-25 endpoints):** 5 repos
- **Medium (25-50 endpoints):** 9 repos
- **High (50-100 endpoints):** 3 repos
- **Very High (100+ endpoints):** 3 repos

### Organizational Distribution
- **Official/Corporate:** 2 repos (Microsoft eShop, NetBox community)
- **Large OSS Projects:** 8 repos (>10k stars)
- **Mid-size Projects:** 7 repos (1k-10k stars)
- **Smaller Active Projects:** 3 repos (<1k stars but high quality)

---

## Key Patterns Covered

### Authentication & Authorization
- JWT (16 repos)
- OAuth (4 repos)
- Multi-tenancy (3 repos)
- RBAC (8 repos)

### Data Operations
- Pagination (18 repos)
- Filtering/Search (15 repos)
- File Upload/Download (12 repos)
- Batch Operations (5 repos)

### Advanced Patterns
- WebSockets/Real-time (5 repos)
- Background Jobs (8 repos)
- Webhooks (4 repos)
- GraphQL alongside REST (2 repos)
- Microservices (2 repos)
- Multi-protocol (WebDAV, S3) (1 repo)

### Infrastructure
- Docker deployment (20 repos)
- CI/CD (18 repos)
- Monitoring/Observability (10 repos)
- Caching (15 repos)
- Message Queues (6 repos)

---

## Quality Metrics

### Average Scores by Framework
- Flask: 56/60 (highest average)
- NestJS: 52.5/60
- Next.js: 55/60
- Django: 50/60
- Gin: 49/60
- Spring Boot: 49/60
- ASP.NET Core: 46.5/60
- Express: 57/60
- Fastify: 45.5/60
- FastAPI: 40.5/60

### Maintenance Status
- Updated within 1 month: 12 repos
- Updated within 3 months: 6 repos
- Updated within 6 months: 2 repos

### Test Coverage
- Comprehensive tests: 16 repos
- Basic tests: 4 repos

---

## Expected Total Coverage

### Endpoint Count
- **Minimum estimate:** 800+ endpoints
- **Maximum estimate:** 1,200+ endpoints
- **Average per repo:** 40-60 endpoints

### Framework Coverage
- All 10 target frameworks: ✅
- Each framework has 3+ test repos (including existing): ✅
- Diverse patterns per framework: ✅

---

## Implementation Status

### Phase 1: Research & Selection ✅
- All 20 repositories researched
- All repositories scored against criteria
- All selections documented

### Phase 2: Documentation 🔄
- [ ] 20 individual analysis documents
- [ ] Master README updated
- [ ] Selection criteria documented

### Phase 3: Submodules ⏳
- [ ] Git submodules added
- [ ] .gitmodules updated
- [ ] Fixture README updated

### Phase 4: Integration Tests ⏳
- [ ] 20 test files created
- [ ] All tests passing
- [ ] Coverage validated

---

## Next Steps

1. Create individual analysis documents for each repository
2. Add repositories as git submodules
3. Create integration test files
4. Run initial extraction tests
5. Document any extraction issues
6. Update main README with new coverage stats

---

## References

- [Selection Criteria](selection-criteria.md)
- [Master README](README.md)
- Individual analysis documents in framework subdirectories
