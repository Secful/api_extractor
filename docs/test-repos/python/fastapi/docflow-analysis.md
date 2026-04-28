# DocFlow - FastAPI Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/jiisanda/docflow
- **Stars:** 267
- **Last Updated:** 2026-04-19
- **Language:** Python
- **License:** MIT

## Selection Rationale
DocFlow was selected as a FastAPI integration test repository because it demonstrates comprehensive document management patterns, provides real-world file handling, and represents enterprise document lifecycle management - a different domain from typical CRUD or AI applications.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Last commit April 2026, 284 commits |
| Code Quality | 8/10 | Docker, migrations, good structure, API docs |
| Endpoint Count | 9/10 | 26 endpoints - good range |
| Framework Usage | 10/10 | FastAPI primary, clean REST patterns |
| Pattern Diversity | 8/10 | Auth, file upload, search, versioning, ACL, email, storage backends |
| Production Usage | 3/5 | Production patterns but maintenance concerns addressed |
| Documentation | 4/5 | Good README, Docker setup, API docs |
| Stars/Popularity | 2/5 | 267 stars |
| **TOTAL** | **39/60** | **PASS** |

## Application Overview

- **Domain:** Document Management System
- **Description:** Comprehensive document management API handling complete document lifecycle from ingestion through archival.
- **Key Features:**
  - Document upload, download, preview
  - Version control and tracking
  - Document sharing and permissions
  - Search and categorization
  - Email integration (send files via email)
  - Storage backends (AWS S3, MinIO)
  - Access control lists (ACL)
  - Document metadata management

## API Structure

### Expected Endpoint Count
**Estimated:** 26 endpoints

### Key Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| POST | /api/auth/register | User registration | username, email, password | Authentication |
| POST | /api/auth/login | User login | username, password | JWT auth |
| POST | /api/auth/2fa | Two-factor auth | code | 2FA planned |
| GET | /api/documents | List documents | page, limit | Pagination |
| POST | /api/documents | Upload document | file (multipart) | File upload |
| GET | /api/documents/{id} | Get document | id (path) | Path param |
| PUT | /api/documents/{id} | Update document | id (path), metadata | Update |
| DELETE | /api/documents/{id} | Delete document | id (path) | Delete |
| GET | /api/documents/{id}/download | Download document | id (path) | File download |
| GET | /api/documents/{id}/preview | Preview document | id (path) | Preview |
| GET | /api/documents/{id}/versions | Get versions | id (path) | Version history |
| POST | /api/documents/{id}/share | Share document | id, user_id, permissions | Sharing |
| DELETE | /api/documents/{id}/share/{share_id} | Revoke share | id, share_id | Revoke access |
| GET | /api/documents/search | Search documents | query, filters | Search |
| POST | /api/documents/{id}/categorize | Categorize | id, category | Organization |
| GET | /api/documents/categories | List categories | - | Categories |
| POST | /api/documents/{id}/email | Send via email | id, recipient | Email integration |
| GET | /api/documents/{id}/metadata | Get metadata | id (path) | Metadata |
| PUT | /api/documents/{id}/metadata | Update metadata | id (path), metadata | Metadata update |
| GET | /api/notifications | List notifications | - | Notifications |
| POST | /api/notifications/mark-read | Mark as read | notification_id | Mark read |
| GET | /api/storage/stats | Storage stats | - | Statistics |

## Notable Patterns

### 1. Authentication
- JWT with planned 2FA support
- Role-based access control (RBAC)
- Files: `/app/auth/`

### 2. File Upload/Download
- Multipart form-data for upload
- Binary streaming for download
- Storage abstraction (S3, MinIO)

### 3. Versioning
- Document version tracking
- Version history retrieval
- Rollback capability (implied)

### 4. Search & Categorization
- Document search with filters
- Category-based organization
- Metadata-driven search

### 5. Access Control
- Document sharing with permissions
- ACL management
- Permission revocation

### 6. Storage Backends
- AWS S3 integration
- MinIO support (S3-compatible)
- Storage abstraction layer

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `22 <= len(result.endpoints) <= 30`
- HTTP methods: GET, POST, PUT, DELETE present
- Path parameters extracted correctly (`{id}`)
- Source file tracking present

**Known Edge Cases:**
1. File upload/download endpoints - should extract correctly
2. Multiple path parameters (`{id}/share/{share_id}`)
3. Query parameters in search - should extract path only
4. Storage backend configuration - not API endpoints

## Special Considerations

### Dependencies
- Database: PostgreSQL
- Cache: Redis
- Storage: AWS S3 or MinIO
- Python 3.11+
- Nginx reverse proxy

### Excluded Files/Directories
- Tests: `tests/`, `*_test.py`, `test_*.py`
- Docs: `docs/`
- Build: `.github/`, `docker/`, `nginx/`
- Dependencies: `venv/`, `.venv/`, `__pycache__/`
- Migrations: `alembic/versions/`

### Extractor Challenges
1. **Storage backend routes** - Configuration vs. API endpoints
2. **File streaming** - Binary response endpoints
3. **Complex path params** - Nested resources (`{id}/share/{share_id}`)

## Integration Test Plan

### Test File
`tests/integration/test_realworld_fastapi_docflow.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert 22 <= len(result.endpoints) <= 30

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods
assert HTTPMethod.PUT in methods
assert HTTPMethod.DELETE in methods

# Specific paths
paths = {ep.path for ep in result.endpoints}
assert "/api/documents" in paths
assert any("/documents/{id}" in path for path in paths)
assert any("/share" in path for path in paths)
assert any("/search" in path for path in paths)

# Path parameters
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) > 5
for ep in param_endpoints:
    assert "{" in ep.path and "}" in ep.path

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".py")
    assert ep.source_line > 0

# Domain-specific patterns
document_paths = [p for p in paths if "/documents" in p]
assert len(document_paths) >= 10
```

### Key Validations
1. Document CRUD operations
2. File upload/download endpoints
3. Sharing and permission endpoints
4. Search functionality
5. Version management
6. Nested resource paths
7. Multiple path parameters
