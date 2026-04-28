# Extended Integration Test Repositories

## Overview

This directory contains research, analysis, and documentation for 20 additional real-world repositories used as integration test fixtures. These repositories complement the existing 11 fixtures to provide comprehensive validation of the API extractor across 10 frameworks.

**Goal:** Validate extractor against 31 total real-world repositories (11 existing + 20 new) covering diverse production patterns, architectural styles, and API designs.

---

## Status Dashboard

| Framework | Repository 1 | Repository 2 | Status |
|-----------|--------------|--------------|--------|
| **Python** | | | |
| FastAPI | [DocFlow](python/fastapi/docflow-analysis.md) | [Polar](python/fastapi/polar-analysis.md) | ✅ Complete |
| Flask | [Mentorship Backend](python/flask/mentorship-backend-analysis.md) | [Flask RealWorld](python/flask/flask-realworld-analysis.md) | ✅ Complete |
| Django REST | [NetBox](python/django/netbox-analysis.md) | [wger](python/django/wger-analysis.md) | ✅ Complete |
| **JavaScript/TypeScript** | | | |
| Express | [RealWorld](javascript/express/realworld-analysis.md) | [Hackathon Starter](javascript/express/hackathon-starter-analysis.md) | ✅ Complete |
| NestJS | [Ghostfolio](javascript/nestjs/ghostfolio-analysis.md) | [RealWorld](javascript/nestjs/realworld-analysis.md) | ✅ Complete |
| Fastify | [JWT Boilerplate](javascript/fastify/jwt-boilerplate-analysis.md) | [daily-api](javascript/fastify/daily-api-analysis.md) | ✅ Complete |
| Next.js | [TBD](javascript/nextjs/repo1-analysis.md) | [TBD](javascript/nextjs/repo2-analysis.md) | ⏳ Pending |
| **Java** | | | |
| Spring Boot | [eladmin](java/spring-boot/eladmin-analysis.md) | [mall](java/spring-boot/mall-analysis.md) | ✅ Complete |
| **C#** | | | |
| ASP.NET Core | [TBD](csharp/aspnetcore/repo1-analysis.md) | [TBD](csharp/aspnetcore/repo2-analysis.md) | ⏳ Pending |
| **Go** | | | |
| Gin | [TBD](go/gin/repo1-analysis.md) | [TBD](go/gin/repo2-analysis.md) | ⏳ Pending |

**Legend:**
- ✅ Complete - Analysis done, submodule added, tests passing
- 🔄 In Progress - Currently being researched/implemented
- ⏳ Pending - Not yet started

---

## Selection Criteria

All repositories are evaluated using a [comprehensive scoring rubric](selection-criteria.md) (60 points total, 35+ to pass):

**Primary Criteria (40 points):**
- Active Maintenance (0-10)
- Code Quality (0-10)
- API Endpoint Count (0-10)
- Framework Usage (0-10)

**Secondary Criteria (20 points):**
- Pattern Diversity (0-10)
- Production Usage (0-5)
- Documentation (0-5)
- Stars/Popularity (0-5)

**Diversity Requirements:**
- Different architectural patterns per framework
- Different domains (e-commerce, SaaS, social, CMS, etc.)
- Different complexity levels (simpler 10-25 endpoints, complex 25-50)
- Different organizations/authors

---

## Repository Categories

### Python Frameworks (6 repos)

**FastAPI (2 repos):**
- Repo 1: ✅ DocFlow (3,205 stars, document management, 23 endpoints)
- Repo 2: ✅ Polar (9,766 stars, payment platform, 332 endpoints)

**Flask (2 repos):**
- Repo 1: ✅ Mentorship Backend (645 stars, mentorship matching, 34 endpoints)
- Repo 2: ✅ Flask RealWorld (208 stars, blogging platform, 19 endpoints)

**Django REST Framework (2 repos):**
- Repo 1: ✅ NetBox (17,146 stars, IPAM/DCIM, 772 endpoints)
- Repo 2: ✅ wger (3,503 stars, fitness/nutrition, 186 endpoints)

### JavaScript/TypeScript Frameworks (8 repos)

**Express (2 repos):**
- Repo 1: ✅ RealWorld (3,790 stars, blogging platform, 20 endpoints)
- Repo 2: ✅ Hackathon Starter (35,216 stars, multi-service integration hub, 108 endpoints)

**NestJS (2 repos):**
- Repo 1: ✅ Ghostfolio (8,284 stars, wealth management platform, 113 endpoints)
- Repo 2: ✅ RealWorld (3,344 stars, blogging platform, 21 endpoints)

**Fastify (2 repos):**
- Repo 1: ✅ JWT Boilerplate (587 stars, auth/user management, 18 endpoints)
- Repo 2: ✅ daily-api (462 stars, content delivery platform, 153 endpoints)

**Next.js (2 repos):**
- Repo 1: TBD
- Repo 2: TBD

### Java Frameworks (2 repos)

**Spring Boot (2 repos):**
- Repo 1: ✅ eladmin (21,935 stars, enterprise admin/RBAC, 133 endpoints)
- Repo 2: ✅ mall (83,505 stars, e-commerce platform, 246 endpoints)

### C# Frameworks (2 repos)

**ASP.NET Core (2 repos):**
- Repo 1: TBD
- Repo 2: TBD

### Go Frameworks (2 repos)

**Gin (2 repos):**
- Repo 1: TBD
- Repo 2: TBD

---

## Existing Test Fixtures (11 total)

For reference, the current test coverage includes:

1. **Next.js** - cal.com (scheduling platform)
2. **Next.js** - dub (link management)
3. **FastAPI** - realworld-example (Conduit implementation)
4. **Django REST** - django-rest-framework-example
5. **Express** - express-example
6. **NestJS** - nestjs-realworld-example-app
7. **Fastify** - fastify-example
8. **Spring Boot** - spring-boot-realworld-example-app
9. **ASP.NET Core** - aspnetcore-realworld-example-app
10. **Gin** - golang-gin-realworld-example-app
11. **Flask** - TBD (check existing fixtures)

**New target:** 31 total fixtures (11 existing + 20 new)

---

## Directory Structure

```
docs/test-repos/
├── README.md                          # This file
├── selection-criteria.md              # Scoring rubric and methodology
├── python/
│   ├── fastapi/
│   │   ├── repo1-analysis.md
│   │   └── repo2-analysis.md
│   ├── flask/
│   │   ├── repo1-analysis.md
│   │   └── repo2-analysis.md
│   └── django/
│       ├── repo1-analysis.md
│       └── repo2-analysis.md
├── javascript/
│   ├── express/
│   │   ├── repo1-analysis.md
│   │   └── repo2-analysis.md
│   ├── nestjs/
│   │   ├── repo1-analysis.md
│   │   └── repo2-analysis.md
│   ├── fastify/
│   │   ├── repo1-analysis.md
│   │   └── repo2-analysis.md
│   └── nextjs/
│       ├── repo1-analysis.md
│       └── repo2-analysis.md
├── java/
│   └── spring-boot/
│       ├── repo1-analysis.md
│       └── repo2-analysis.md
├── csharp/
│   └── aspnetcore/
│       ├── repo1-analysis.md
│       └── repo2-analysis.md
└── go/
    └── gin/
        ├── repo1-analysis.md
        └── repo2-analysis.md
```

---

## Implementation Workflow

Each repository follows this process:

1. **Research & Selection** (30-45 min)
   - Search using framework-specific queries
   - Evaluate 3-5 candidates against criteria
   - Score and select best option

2. **Documentation** (30-45 min)
   - Create analysis document from template
   - Document endpoints, patterns, architecture
   - Define expected extraction results

3. **Add as Submodule** (5-10 min)
   - Run `git submodule add` command
   - Update `.gitmodules` and fixture README
   - Commit changes

4. **Trial Extraction** (15-20 min)
   - Clone and run extractor manually
   - Validate endpoint count and patterns
   - Document actual vs. expected results

5. **Create Integration Test** (30-45 min)
   - Create test file following existing patterns
   - Implement 4-5 test methods
   - Validate against actual extraction

6. **Validation** (10-15 min)
   - Run test suite
   - Fix any failures
   - Document known limitations

**Total:** ~2-3 hours per repository, 40-60 hours for all 20

---

## Success Metrics

**Per Repository:**
- ✅ Repository scored ≥35/60
- ✅ Analysis document complete
- ✅ Added as git submodule (or .gitignore if >100MB)
- ✅ Integration test created and passing
- ✅ Documentation updated

**Per Framework:**
- ✅ 2 diverse repositories selected
- ✅ Different domains and complexity levels
- ✅ All test tiers validated (extraction, HTTP semantics, patterns, domain)

**Overall Project:**
- ✅ 20 new repositories documented and tested
- ✅ 31 total real-world fixtures (11 + 20)
- ✅ All 10 frameworks have 3+ test repos
- ✅ All integration tests passing
- ✅ 600-1000 total endpoints tested

---

## Quality Metrics

- **Test Coverage:** 31 real-world fixtures total
- **Endpoint Coverage:** 600-1000 endpoints across all fixtures
- **Framework Coverage:** All 10 frameworks with 3+ repos each
- **Domain Diversity:** 15+ different domains (e-commerce, SaaS, social, CMS, etc.)
- **Pattern Diversity:** Auth, file upload, pagination, search, WebSockets, validation
- **Maintenance:** All repos with commits within 6-12 months

---

## Usage

### For Contributors

1. Select a framework to work on
2. Follow [selection criteria](selection-criteria.md)
3. Use analysis template (see any `*-analysis.md` file)
4. Create integration test following existing patterns in `tests/integration/`
5. Update this README status dashboard

### For Reviewers

1. Check analysis documents for completeness
2. Verify scoring against rubric
3. Validate diversity requirements met
4. Run integration tests to confirm passing
5. Review test assertions match documented expectations

---

## Related Documentation

- [Selection Criteria & Scoring Rubric](selection-criteria.md)
- [Test Fixtures README](../../tests/fixtures/real-world/README.md)
- [Integration Tests](../../tests/integration/)
- [Project README](../../README.md)

---

## Questions & Feedback

For questions about repository selection, scoring, or test implementation, please open an issue in the project repository.
