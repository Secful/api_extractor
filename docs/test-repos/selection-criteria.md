# Repository Selection Criteria

## Scoring Rubric

Each candidate repository is evaluated on a 60-point scale. **Minimum passing score: 35/60**

### Primary Criteria (40 points total)

#### 1. Active Maintenance (0-10 points)
- **10 points:** Commits within last 3 months
- **8-9 points:** Commits within last 6 months
- **6-7 points:** Commits within last 12 months
- **3-5 points:** Commits within last 24 months
- **0-2 points:** Older than 24 months

#### 2. Code Quality (0-10 points)
- **10 points:** Comprehensive tests + CI/CD + linting + excellent structure
- **8-9 points:** Tests + CI/CD + good structure
- **6-7 points:** Some tests + basic CI + reasonable structure
- **3-5 points:** Minimal tests or poor structure
- **0-2 points:** No tests, inconsistent structure

#### 3. API Endpoint Count (0-10 points)
- **10 points:** 15-50 endpoints (ideal range)
- **8-9 points:** 10-15 or 50-75 endpoints
- **6-7 points:** 5-10 or 75-100 endpoints
- **3-5 points:** <5 or >100 endpoints
- **0-2 points:** No clear API or >200 endpoints

#### 4. Framework Usage (0-10 points)
- **10 points:** Primary framework with idiomatic patterns
- **8-9 points:** Primary framework with mostly standard patterns
- **6-7 points:** Mixed frameworks but target is primary
- **3-5 points:** Target framework used minimally
- **0-2 points:** Framework barely present

### Secondary Criteria (20 points total)

#### 5. Pattern Diversity (0-10 points)
Score based on number of patterns present:
- Authentication (JWT, OAuth, sessions)
- Pagination (offset, cursor, page-based)
- File upload/download
- Search/filtering
- WebSockets/SSE
- Middleware/guards
- Validation
- Rate limiting

**Scoring:**
- **9-10 points:** 6+ patterns
- **7-8 points:** 4-5 patterns
- **5-6 points:** 2-3 patterns
- **3-4 points:** 1 pattern
- **0-2 points:** No notable patterns

#### 6. Production Usage (0-5 points)
- **5 points:** Deployed production application
- **3-4 points:** Production-ready demo or template
- **2 points:** Educational/tutorial with best practices
- **1 point:** Proof-of-concept or example
- **0 points:** Toy project or incomplete

#### 7. Documentation (0-5 points)
- **5 points:** Comprehensive API docs + architecture + setup
- **3-4 points:** Good API docs or solid README
- **2 points:** Basic README with setup instructions
- **1 point:** Minimal documentation
- **0 points:** No documentation

#### 8. Stars/Popularity (0-5 points)
- **5 points:** >5,000 stars
- **4 points:** 1,000-5,000 stars
- **3 points:** 500-1,000 stars
- **2 points:** 100-500 stars
- **1 point:** 10-100 stars
- **0 points:** <10 stars

---

## Diversity Requirements

For each framework, select 2 repositories that differ in:

### Architectural Patterns
- Monolithic vs. microservices
- Layered vs. modular vs. flat structure
- MVC vs. domain-driven vs. feature-based organization

### Domain/Industry
- E-commerce
- Social media
- SaaS/productivity
- CMS/blogging
- Healthcare
- Finance
- Project management
- Education
- Entertainment

Avoid: 2 similar domains per framework

### Complexity Levels
- **Simpler (10-25 endpoints):** Good for basic pattern validation
- **More complex (25-50 endpoints):** Tests scalability and advanced patterns

Aim for one of each per framework.

### Organizations
- Prefer different authors/organizations
- Avoid 2 repos from same company or developer

---

## Disqualification Criteria

Automatically reject repositories with:

1. **No clear REST API** - GraphQL-only, gRPC-only, or no HTTP endpoints
2. **Archived/deprecated** - No commits in 3+ years or marked archived
3. **Minimal code** - <100 lines of actual application code
4. **No license or restrictive license** - Cannot use as test fixture
5. **Known security issues** - Unpatched critical vulnerabilities
6. **Build failures** - Cannot install dependencies or run

---

## Search Strategy

### Primary Sources

1. **GitHub Advanced Search**
   - Use framework-specific queries
   - Filter by: language, stars, last push date
   - Sort by: stars, recently updated, relevance

2. **Awesome Lists**
   - Awesome FastAPI, Awesome Flask, etc.
   - Often curated for quality
   - Look in "Real-world applications" sections

3. **Framework Showcases**
   - Official "Built with X" galleries
   - Framework organization examples
   - Conference/workshop demos

4. **RealWorld.io**
   - Standardized "Conduit" implementations
   - Good for framework-to-framework comparison
   - May not have enough endpoint diversity

### Search Query Templates

**Python:**
```
"fastapi" language:Python stars:>500 pushed:>2024-01-01
"flask" "rest" "api" language:Python stars:>500
"djangorestframework" stars:>500
```

**JavaScript/TypeScript:**
```
"express" "router" language:TypeScript stars:>500
"@nestjs/core" language:TypeScript stars:>500
"fastify" language:TypeScript stars:>500
"next.js" "app" OR "pages" "api" stars:>1000
```

**Java:**
```
"spring-boot" "rest" language:Java stars:>500
"@RestController" language:Java stars:>500
```

**C#:**
```
"aspnetcore" "api" language:C# stars:>500
"[ApiController]" language:C# stars:>500
```

**Go:**
```
"gin-gonic" language:Go stars:>500
"gin.Engine" language:Go stars:>500
```

---

## Evaluation Process

### Step 1: Initial Screening
- Check last commit date
- Check star count and activity
- Scan README for purpose and features
- Verify framework is primary technology

### Step 2: Deep Analysis
- Clone repository
- Review code structure
- Count approximate endpoints
- Identify patterns used
- Check test coverage
- Review documentation

### Step 3: Scoring
- Fill out scoring rubric
- Calculate total score
- Document rationale for each score

### Step 4: Comparative Selection
- Compare top candidates per framework
- Ensure diversity criteria met
- Select final 2 per framework

---

## Documentation Requirements

For each selected repository, create analysis document with:

1. **Repository Information** - URL, stars, last update, license
2. **Selection Rationale** - Why chosen over alternatives
3. **Scoring Breakdown** - Complete rubric with notes
4. **Application Overview** - Domain, features, architecture
5. **API Structure** - Expected endpoints, patterns, parameters
6. **Notable Patterns** - Auth, pagination, file upload, etc.
7. **Expected Extraction Results** - Success criteria, edge cases
8. **Special Considerations** - Dependencies, excluded files, challenges
9. **Integration Test Plan** - Specific assertions to validate

---

## Review Checklist

Before finalizing selection:

- [ ] Score ≥35/60
- [ ] Different domain than other repo for same framework
- [ ] Different complexity level (simpler/more complex)
- [ ] Different organization/author
- [ ] Different architectural pattern
- [ ] License allows use as test fixture
- [ ] Repository is buildable/runnable
- [ ] Clear API endpoints present
- [ ] Framework is primary technology
- [ ] Documentation created following template
