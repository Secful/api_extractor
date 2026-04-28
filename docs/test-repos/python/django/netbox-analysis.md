# NetBox - Django REST Framework Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/netbox-community/netbox
- **Stars:** 20,400+
- **Last Updated:** 2026-04-14 (v4.5.8)
- **Language:** Python
- **License:** Apache 2.0

## Selection Rationale
NetBox was selected as the top Django REST Framework repository, demonstrating enterprise-grade infrastructure management with comprehensive REST API coverage, production deployment at scale, and extensive use of DRF patterns including token authentication, pagination, filtering, bulk operations, and webhooks.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Latest release April 2026 (v4.5.8), 356 releases, continuous commits |
| Code Quality | 10/10 | Comprehensive CI/CD, Ruff linting, pre-commit hooks, Codecov integration |
| Endpoint Count | 10/10 | 50-100+ endpoints across devices, racks, cables, IP addresses, circuits |
| Framework Usage | 10/10 | DRF v3.16.1 as primary, idiomatic Django patterns |
| Pattern Diversity | 9/10 | Token auth (v1 & v2), pagination, filtering, bulk ops, webhooks, field selection |
| Production Usage | 5/5 | Widely deployed production app, "single source of truth" for networks |
| Documentation | 5/5 | Comprehensive ReadTheDocs, API reference, architecture guides |
| Stars/Popularity | 5/5 | 20,400+ stars, 16 language translations |
| **TOTAL** | **54/60** | **PASS (Highest Django Score)** |

## Application Overview

- **Domain:** Network Infrastructure Management
- **Description:** Web application for managing and documenting network infrastructure, serving as the "single source of truth" for network engineers.
- **Key Features:**
  - IP address management (IPAM)
  - Equipment racks and devices
  - Network connections and cabling
  - Virtualization resources
  - Data circuits and providers
  - Power tracking
  - Configuration templates
  - REST API for all resources

## API Structure

### Expected Endpoint Count
**Estimated:** 700-800+ endpoints (NetBox is a comprehensive infrastructure management platform with extensive API coverage)

### Key Endpoint Categories

**IPAM (IP Address Management):**
- IP addresses, prefixes, VLANs, VRFs
- Aggregates, RIRs, ASNs
- Services

**DCIM (Data Center Infrastructure):**
- Sites, locations, racks
- Devices, device types, modules
- Cables, connections
- Power feeds, panels, outlets

**Circuits:**
- Providers, circuits, circuit types
- Circuit terminations

**Virtualization:**
- Virtual machines, clusters
- Interfaces

**Tenancy:**
- Tenants, tenant groups

**Core:**
- Jobs, background tasks
- Data sources

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| GET | /api/dcim/devices/ | List devices | limit, offset, q | Pagination, filtering |
| POST | /api/dcim/devices/ | Create device | device data | Bulk create supported |
| GET | /api/dcim/devices/{id}/ | Get device | id (path) | Single device |
| PUT | /api/dcim/devices/{id}/ | Update device | id, device data | Full update |
| PATCH | /api/dcim/devices/{id}/ | Partial update | id, partial data | Partial update |
| DELETE | /api/dcim/devices/{id}/ | Delete device | id (path) | Delete |
| GET | /api/ipam/ip-addresses/ | List IP addresses | filtering params | Complex filtering |
| POST | /api/ipam/ip-addresses/ | Create IP | IP data | Bulk create |
| GET | /api/ipam/prefixes/ | List prefixes | filtering | Network prefixes |
| GET | /api/dcim/cables/ | List cables | filtering | Cable connections |

## Notable Patterns

### 1. Authentication
- Token-based (v1 legacy and v2 bearer tokens)
- IP-based access restrictions
- Write permission controls
- Files: `/netbox/api/authentication.py`

### 2. Pagination
- Automatic pagination (default 50, configurable)
- Returns `count`, `next`, `previous`, `results`
- Files: DRF default pagination

### 3. Filtering & Ordering
- Complex query parameter filtering
- Custom filter backends
- Multiple field filtering
- Files: `/netbox/api/filters.py`

### 4. Bulk Operations
- Create, update, delete multiple objects in single request
- Batch processing for performance
- Files: `/netbox/api/views.py`

### 5. Field Selection
- `fields` parameter for response customization
- `omit` parameter to exclude fields
- Brief format for minimal responses
- Files: `/netbox/api/serializers.py`

### 6. Webhooks
- Event notifications for object changes
- Customizable webhook endpoints
- Files: `/netbox/webhooks/`

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `600 <= len(result.endpoints) <= 900`
- HTTP methods: GET, POST, PUT, PATCH, DELETE present
- Path parameters extracted correctly (`{pk}`)
- DRF ViewSet patterns detected
- Router-based URL generation
- URL prefixes from include() properly applied (`/api/circuits/`, `/api/dcim/`, etc.)

**Known Edge Cases:**
1. ViewSet-based routes - DRF Router generates multiple endpoints per ViewSet
2. Nested routes - Some resources nested under others
3. Custom actions - `@action` decorators on ViewSets
4. OpenAPI schema endpoint - May be included in extraction
5. Large codebase - Many apps and models

## Special Considerations

### Dependencies
- Database: PostgreSQL (required)
- Cache: Redis
- Python 3.11+
- Django 5.1+, DRF 3.16+

### Excluded Files/Directories
- Tests: `*/tests/`, `*_test.py`
- Migrations: `*/migrations/`
- Scripts: `scripts/`
- Static: `netbox/static/`
- Templates: `netbox/templates/`
- Docs: `docs/`

### Extractor Challenges
1. **ViewSet routes** - DRF Router auto-generates URLs from ViewSets
2. **Multiple apps** - Many Django apps (dcim, ipam, circuits, etc.)
3. **Custom actions** - `@action` decorators create additional endpoints
4. **Nested viewsets** - Some routes nested under parents
5. **Large codebase** - 15k+ commits, complex structure

## Integration Test Plan

### Test File
`tests/integration/test_realworld_django_netbox.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert 600 <= len(result.endpoints) <= 900

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.PATCH in methods
assert HTTPMethod.DELETE in methods

# Specific paths (with /api prefix)
paths = {ep.path for ep in result.endpoints}
assert any("/api/dcim/devices" in p for p in paths)
assert any("/api/ipam/ip-addresses" in p for p in paths)

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) > 20

# ViewSet patterns
# Should have both list and detail endpoints
list_endpoints = [ep for ep in result.endpoints if not "{" in ep.path and ep.method == HTTPMethod.GET]
detail_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(list_endpoints) > 10
assert len(detail_endpoints) > 20

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".py")
    assert ep.source_line > 0
```

### Key Validations
1. DRF ViewSet endpoint generation
2. Router-based URL patterns
3. Multiple Django apps (dcim, ipam, circuits, etc.)
4. Custom actions with `@action` decorator
5. Nested routes
6. All CRUD methods (GET, POST, PUT, PATCH, DELETE)
7. Bulk operation endpoints
