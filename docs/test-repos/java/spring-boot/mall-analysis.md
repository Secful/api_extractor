# mall - Spring Boot Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/macrozheng/mall
- **Stars:** 83,505
- **Last Updated:** 2026-03-06
- **Language:** Java (98.7%)
- **License:** Apache-2.0

## Selection Rationale
Production-grade complete e-commerce platform (front store + backend management) with 83K+ stars, demonstrating Spring Boot + MyBatis patterns across shopping cart, order processing, member management, promotions, and content management - providing maximum diversity from RealWorld's simple blogging and eladmin's admin system with complex e-commerce workflows, Elasticsearch integration, and multi-module architecture for comprehensive pattern testing.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 8/10 | Last commit March 6, 2026 (2 months ago), active but slower |
| Code Quality | 7/10 | Good structure, minimal tests (4 test files), extensive documentation |
| Endpoint Count | 10/10 | 90-100 endpoints (upper ideal range, complex domain) |
| Framework Usage | 10/10 | Spring Boot, @Controller+@ResponseBody, comprehensive REST APIs |
| Pattern Diversity | 10/10 | Exceptional - auth, cart, orders, payments, search, uploads, CMS, reports |
| Production Usage | 5/5 | Live demo at macrozheng.com, production deployment examples |
| Documentation | 5/5 | Comprehensive tutorial site (macrozheng.com), detailed docs folder |
| Stars/Popularity | 5/5 | 83,505 stars - most popular Java project on GitHub |
| **TOTAL** | **60/60** | **PASS (Perfect Score)** |

## Application Overview

- **Domain:** E-commerce Platform (Front Store + Backend Management)
- **Description:** Complete e-commerce system with frontend shopping mall and backend management system, featuring product catalog, shopping cart, order workflows, member management, promotion engine, and content management.
- **Key Features:**
  - Product catalog management (categories, brands, attributes)
  - Shopping cart and checkout
  - Order management (creation, payment, shipment, delivery)
  - Member/user system with levels and integration points
  - Promotion and coupon system
  - Product search with Elasticsearch
  - Content management system (CMS)
  - Statistical reports and analytics
  - File upload (OSS/MinIO)
  - Message queue (RabbitMQ)
  - Multi-level caching (Redis)
  - MongoDB for content storage

## API Structure

### Expected Endpoint Count
**Estimated:** 90-100 endpoints

### Key Endpoint Categories

**Admin Backend (mall-admin - 191 endpoints):**
- Product management (SKU, attributes, categories)
- Brand management
- Order management (list, detail, update, ship, close)
- Return/refund management
- Member management
- Promotion/coupon management
- Content management (subjects, advertising)
- Statistical reports

**Front Store (mall-portal - 78 endpoints):**
- Product browsing and search
- Shopping cart operations
- Order creation and payment
- Member operations (register, login, info)
- Product collection/favorites
- Receive address management
- Member integration points
- Product reviews/ratings

**Search Service (mall-search - 9 endpoints):**
- Product search with Elasticsearch
- Search suggestions
- Related products

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| POST | /admin/login | Admin login | username, password | JWT auth |
| GET | /admin/info | Admin info | - | Current admin |
| POST | /admin/register | Admin register | body: AdminParam | Registration |
| GET | /product/list | List products | page, size, filters | Product catalog |
| POST | /product/create | Create product | body: Product | Product creation |
| PUT | /product/update/{id} | Update product | id (path), body | Product update |
| DELETE | /product/delete/{id} | Delete product | id (path) | Product deletion |
| GET | /productCategory/list/{parentId} | Category children | parentId (path) | Category tree |
| GET | /brand/list | List brands | page, size | Brand management |
| GET | /order/list | List orders | page, size, status | Order management |
| GET | /order/{id} | Get order detail | id (path) | Order details |
| POST | /order/update/note | Update order note | body: NoteParam | Order notes |
| POST | /order/delivery | Deliver order | body: DeliveryParam | Ship order |
| POST | /order/close | Close order | ids | Cancel order |
| GET | /returnApply/list | List return requests | page, size | Return management |
| POST | /coupon/create | Create coupon | body: Coupon | Promotion creation |
| GET | /home/contentSubject/list | Content subjects | page, size | CMS content |
| POST | /sso/register | Member register | body: Member | User registration |
| POST | /sso/login | Member login | username, password | User login |
| GET | /member/info | Member info | - | Current member |
| GET | /cart/list | Shopping cart | - | Cart items |
| POST | /cart/add | Add to cart | body: CartItem | Add item |
| PUT | /cart/update/{id} | Update cart item | id (path), body | Update quantity |
| DELETE | /cart/delete | Remove from cart | ids | Remove items |
| POST | /order/generateOrder | Create order | body: OrderParam | Order creation |
| POST | /order/paySuccess | Payment callback | orderId | Payment processing |
| GET | /order/list | Member orders | page, size | Order history |
| POST | /order/cancelOrder | Cancel order | orderId | Order cancellation |
| POST | /memberAttention/add | Follow product | productId | Favorites |
| GET | /memberReceiveAddress/list | Receive addresses | - | Shipping addresses |
| GET | /search/simple | Simple search | keyword | Basic search |
| GET | /search/suggest | Search suggestions | keyword | Autocomplete |
| POST | /search/recommend | Recommend products | page, size | Related products |

## Notable Patterns

### 1. Multi-Module Architecture
- mall-admin: Backend management system
- mall-portal: Frontend shopping mall
- mall-search: Search service with Elasticsearch
- mall-common: Common utilities and models
- mall-security: Security and JWT handling
- mall-mbg: MyBatis Generator
- Files: Root Maven modules

### 2. Spring Boot + MyBatis
- MyBatis ORM for data access
- XML-based SQL mappings
- PageHelper for pagination
- Multi-datasource support
- Files: `/mall-admin/src/main/resources/mapper/`, `/dao/`

### 3. Elasticsearch Integration
- Product search functionality
- Full-text search with scoring
- Search suggestions and autocomplete
- Faceted search (filters)
- Files: `/mall-search/`

### 4. Shopping Cart
- Session-based cart (guest users)
- Database-backed cart (members)
- Cart item management (add, update, remove)
- Cart calculation (subtotal, discounts)
- Files: `/mall-portal/src/main/java/com/macro/mall/portal/controller/CartController.java`

### 5. Order Workflow
- Order creation from cart
- Payment processing
- Order status transitions (pending → paid → shipped → delivered)
- Order cancellation and timeout handling
- Return/refund management
- Files: `/mall-admin/src/main/java/com/macro/mall/controller/OmsOrderController.java`

### 6. Promotion Engine
- Coupon system (fixed amount, percentage off)
- Flash sales/limited-time offers
- Member-specific promotions
- Coupon codes and validation
- Files: `/mall-admin/src/main/java/com/macro/mall/controller/SmsCouponController.java`

### 7. Member System
- Member registration and login
- Member levels and points
- Integration points (rewards)
- Member growth system
- Files: `/mall-portal/src/main/java/com/macro/mall/portal/controller/UmsMemberController.java`

### 8. Content Management
- CMS for homepage content
- Advertising management
- Product recommendations
- Subject/topic management
- Files: `/mall-admin/src/main/java/com/macro/mall/controller/CmsSubjectController.java`

### 9. File Upload
- OSS (Object Storage Service) integration
- MinIO support
- Image upload for products
- File management
- Files: `/mall-admin/src/main/java/com/macro/mall/controller/OssController.java`

### 10. RabbitMQ Integration
- Order timeout handling (delayed messages)
- Order cancellation events
- Inventory deduction messaging
- Async order processing
- Files: `/mall-portal/src/main/java/com/macro/mall/portal/component/`

### 11. Multi-Level Caching
- Redis caching layer
- Product cache
- Member cache
- Cart cache
- Cache invalidation strategies
- Files: Redis configuration in common module

### 12. Security & JWT
- JWT-based authentication
- Role-based access control (admin roles)
- Spring Security integration
- Custom authentication filters
- Files: `/mall-security/`

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `70 <= len(result.endpoints) <= 110` (90-100 expected)
- HTTP methods: GET, POST, PUT, DELETE present
- Path parameters extracted correctly (`{id}`, `{parentId}`, etc.)
- @Controller + @ResponseBody or @RestController patterns detected
- Multiple modules detected (mall-admin, mall-portal, mall-search)
- Source tracking present

**Known Edge Cases:**
1. @Controller with @ResponseBody vs @RestController
2. Multi-module Maven project structure
3. Class-level @RequestMapping prefixes
4. @PathVariable and @RequestParam parameters
5. Some endpoints may be in mall-demo or other auxiliary modules
6. Security annotations (@PreAuthorize)

## Special Considerations

### Dependencies
- Database: MySQL 5.7+
- Cache: Redis 5.0+
- Search: Elasticsearch 7.x
- Message Queue: RabbitMQ 3.7+
- Storage: MongoDB 4.2+
- Runtime: Java 8+
- Spring Boot 2.3.0
- MyBatis 3.4.6
- PageHelper for pagination
- OSS/MinIO for file storage

### Excluded Files/Directories
- Tests: `src/test/`, `*Test.java` (only 4 test files)
- Build: `target/`, `.idea/`, `*.iml`
- Dependencies: Maven artifacts
- Config: `application.yml`, `application-*.yml`
- Frontend: `mall-admin-web/`, `mall-app-web/` (Vue.js frontends)
- Generator: `mall-mbg/` (MyBatis generator, may not have REST endpoints)
- Logs: `logs/`
- Documents: `document/`

### Extractor Challenges
1. **Multi-module project** - mall-admin, mall-portal, mall-search have different API surfaces
2. **@Controller pattern** - Uses @Controller + @ResponseBody, not @RestController
3. **Class-level paths** - @RequestMapping on controller class
4. **Large codebase** - 90-100+ endpoints across multiple services
5. **Path variables** - Complex parameter extraction
6. **API versioning** - May have versioned endpoints

## Integration Test Plan

### Test File
`tests/integration/test_realworld_spring_boot_mall.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert 70 <= len(result.endpoints) <= 110

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.DELETE in methods

# Admin endpoints
paths = {ep.path for ep in result.endpoints}
assert any("product" in p for p in paths), "Should find product endpoints"
assert any("order" in p for p in paths), "Should find order endpoints"
assert any("brand" in p for p in paths), "Should find brand endpoints"

# Portal endpoints
assert any("cart" in p for p in paths), "Should find cart endpoints"
assert any("member" in p for p in paths), "Should find member endpoints"

# Search endpoints
assert any("search" in p for p in paths), "Should find search endpoints"

# Authentication
assert any("login" in p for p in paths), "Should find login endpoint"

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 20, "Should find many parameterized endpoints"

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".java")
    assert ep.source_line is not None
    assert ep.source_line > 0
```

### Key Validations
1. Multi-module extraction (admin, portal, search)
2. E-commerce specific endpoints
3. Shopping cart operations
4. Order management workflows
5. Product catalog endpoints
6. Search functionality
7. Member system endpoints
8. Promotion/coupon endpoints
9. CMS content endpoints
10. Path parameter extraction

## Notes

### Production Scale
- **83,505 GitHub stars** - Most popular Java project
- **Live demo** at macrozheng.com
- **Tutorial series** with comprehensive documentation
- **Production deployment** examples and guides

### Architecture Highlights
- Multi-module Maven project
- Spring Boot 2.3.0 with MyBatis
- Elasticsearch for search
- RabbitMQ for async processing
- Redis for caching
- MongoDB for content storage
- Complete e-commerce workflow implementation

### Diversity from Existing Fixtures
This repository provides maximum contrast with existing Spring Boot fixtures:
- **Domain:** E-commerce vs blogging (RealWorld) vs admin/RBAC (eladmin)
- **Endpoints:** 90-100 vs 20-30 (RealWorld) vs 60-70 (eladmin)
- **Complexity:** High with shopping cart, orders, payments, search vs simple/medium
- **Patterns:** E-commerce workflows, cart, checkout, promotions vs social features vs admin features
- **Architecture:** Multi-service (admin/portal/search) vs single module
- **Technology:** Elasticsearch, RabbitMQ, MongoDB vs simpler stacks
- **ORM:** MyBatis (same as RealWorld) vs JPA (eladmin)
