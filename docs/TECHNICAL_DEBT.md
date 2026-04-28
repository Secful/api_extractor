# Technical Debt & Known Limitations

This document tracks known issues, limitations, and future enhancements discovered during integration testing with 20 real-world repositories.

---

## Priority Legend

- 🔴 **High** - Affects core functionality, impacts many users
- 🟡 **Medium** - Affects specific scenarios, has workarounds
- 🟢 **Low** - Nice to have, minimal impact

## Status Legend

- ⏳ **Pending** - Not started
- 🔄 **In Progress** - Currently being worked on
- ✅ **Fixed** - Completed and verified

---

## Active Issues

### 1. FastAPI Router Prefix Composition ⏳ 🔴

**Discovered:** 2026-04-28 during Polar repository analysis
**Status:** ⏳ Pending
**Priority:** 🔴 High

#### Description
FastAPI extractor does not detect or apply `APIRouter(prefix="...")` parameters. Extracted paths are relative to their router definition instead of absolute paths.

#### Example
```python
# polar/customer/endpoints.py
router = APIRouter(prefix="/customers")

@router.get("/{id}")  # ← Route definition
async def get_customer(...): ...
```

**Expected:** `/v1/customers/{id}` (with full prefix chain)
**Actual:** `/{id}` (missing router prefix)

#### Impact
- **Affected repos:** Polar (332 endpoints), DocFlow (23 endpoints), any FastAPI app using router prefixes
- **User impact:** Extracted paths are incomplete and not usable for API documentation or client generation
- **Test workarounds:** Tests validate relative paths instead of absolute paths

#### Root Cause
The FastAPI extractor (`api_extractor/extractors/python/fastapi.py`):
1. ✅ Extracts route decorators (`@router.get(...)`)
2. ❌ Does not extract `APIRouter(prefix=...)` parameters
3. ❌ Does not track router inclusion hierarchy (`parent.include_router(child)`)
4. ❌ Does not compose full path from prefix chain

#### Proposed Solution

**Phase 1: Extract router definitions**
```python
def _extract_router_definitions(self, file_path: str) -> Dict[str, str]:
    """
    Extract APIRouter definitions and their prefixes.

    Parses: router = APIRouter(prefix="/customers")
    Returns: {"router": "/customers"}
    """
    # Tree-sitter query for APIRouter instantiation
    # Extract prefix parameter value
    # Store mapping of variable name to prefix
```

**Phase 2: Track router includes**
```python
def _extract_router_includes(self, file_path: str) -> Dict[str, List[str]]:
    """
    Extract router inclusion hierarchy.

    Parses: app.include_router(customer_router)
    Builds: {"/v1": ["/customers", "/products"]}
    """
    # Tree-sitter query for include_router() calls
    # Build parent-child relationships
    # Create prefix chain map
```

**Phase 3: Apply prefix composition**
```python
def extract_routes_from_file(self, file_path: str) -> List[Route]:
    """Extract routes with full prefix chain applied."""
    # Get router variable for this file
    # Look up prefix chain
    # Compose: /v1 + /customers + /{id} = /v1/customers/{id}
```

#### Effort Estimate
- **Time:** 4-6 hours
- **Complexity:** Medium-High (multi-level router nesting, variable tracking)
- **Files affected:** `api_extractor/extractors/python/fastapi.py`
- **Test updates:** Update 14+ FastAPI integration tests

#### Similar Work (Reference)
Django REST extractor already implements similar logic:
- ✅ `_extract_url_includes()` - Parses `path('api/', include('module.urls'))`
- ✅ `_extract_router_registrations()` - Tracks router.register() with prefixes
- ✅ `_get_url_prefix_for_file()` - Maps files to URL prefixes
- See: `api_extractor/extractors/python/django_rest.py` lines 116-280

#### Workarounds (Current)
- Document limitation in test docstrings
- Test relative paths instead of absolute paths
- Validate endpoint count, methods, and parameters (all work correctly)

#### Related Issues
- None yet

---

## Future Enhancements

### 2. Flask Blueprint Prefix Detection ⏳ 🟡

**Status:** ⏳ Pending
**Priority:** 🟡 Medium

#### Description
Similar to FastAPI routers, Flask Blueprints can be registered with URL prefixes that aren't always applied to extracted paths.

#### Example
```python
app.register_blueprint(api_bp, url_prefix='/api/v1')
```

Current extractor may miss the `/api/v1` prefix depending on how routes are defined.

#### Impact
- Lower priority than FastAPI (fewer repos affected in test set)
- Mentorship Backend and Flask RealWorld don't exhibit this issue
- May affect future Flask repos

#### Effort Estimate
- **Time:** 2-3 hours
- **Complexity:** Medium

---

### 3. Next.js Wrapper Function Patterns ⏳ 🔴

**Discovered:** 2026-04-28 during Formbricks repository analysis
**Status:** ⏳ Pending
**Priority:** 🔴 High

#### Description
Next.js extractor does not detect HTTP method exports when they are assigned to wrapper function calls. Only supports direct function declarations or arrow functions.

#### Example
```typescript
// ✅ WORKS - Direct async function
export const GET = async () => {
  return Response.json({ data: "..." });
};

// ❌ DOESN'T WORK - Wrapper function pattern
export const GET = withV1ApiWrapper({
  handler: async ({ req, authentication }) => {
    // handler logic
  }
});

// ❌ DOESN'T WORK - HOC/middleware wrapper
export const POST = withAuth(async (req) => {
  // handler logic
});
```

**Supported:** `export const GET = async () => {...}` or `export function GET() {...}`
**Not Supported:** `export const GET = wrapperFunction({...})` or any HOC/middleware pattern

#### Impact
- **Affected repos:** Formbricks (5 endpoints extracted vs 97 route files)
- **User impact:** Most production Next.js apps use wrapper patterns for auth, logging, error handling
- **Test workarounds:** Only extracted 5.2% of actual endpoints (5 out of 97)

#### Root Cause
The Next.js extractor (`api_extractor/extractors/javascript/nextjs.py`):
1. ✅ Detects file-system routing (`app/api/*/route.ts` → URL paths)
2. ✅ Extracts direct async functions: `export const GET = async () => {...}`
3. ✅ Extracts function declarations: `export function GET() {...}`
4. ❌ Does not extract wrapper function calls: `export const GET = withWrapper({...})`
5. ❌ Does not handle higher-order component (HOC) patterns
6. ❌ Does not follow function composition chains

#### Proposed Solution

**Phase 1: Detect wrapper patterns**
```python
def _extract_app_router_routes(self, ...):
    """Extract routes including wrapper function patterns."""

    # Current queries for direct functions
    export_query = """
    (export_statement
      (function_declaration name: (identifier) @func_name))
    """

    export_arrow_query = """
    (export_statement
      (lexical_declaration
        (variable_declarator
          name: (identifier) @func_name
          value: (arrow_function))))
    """

    # NEW: Query for wrapper function calls
    export_wrapper_query = """
    (export_statement
      (lexical_declaration
        (variable_declarator
          name: (identifier) @func_name
          value: (call_expression
            function: (identifier) @wrapper_name
            arguments: (arguments)))))
    """
    # Extract @func_name if it's an HTTP method (GET, POST, etc.)
    # Don't need to parse wrapper logic - just recognize the pattern
```

**Phase 2: Extended pattern detection**
```python
# Handle chained wrappers: withAuth(withLogging(handler))
# Handle object-based config: withWrapper({ handler: async () => {} })
# Identify HTTP method name from exported constant
```

#### Effort Estimate
- **Time:** 4-6 hours
- **Complexity:** Medium-High (Tree-sitter pattern matching, multiple wrapper syntaxes)
- **Files affected:** `api_extractor/extractors/javascript/nextjs.py`
- **Test updates:** Update existing Next.js integration tests

#### Similar Patterns in Other Frameworks
- **Express:** `app.use(middleware(handler))` - handled by middleware detection
- **Fastify:** `fastify.route({ handler: wrapper(fn) })` - object-based config
- **NestJS:** Decorators naturally handled by decorator extraction

#### Workarounds (Current)
- Document limitation in test docstrings
- Only test repositories with simple export patterns
- Note extraction percentage in analysis documents
- Formbricks extracted 5/97 routes (5.2%)

#### Related Issues
- Similar to FastAPI router prefix issue (#1) - both involve composition patterns

---

### 4. Spring Boot Path Variable Patterns ⏳ 🟢

**Status:** ⏳ Pending
**Priority:** 🟢 Low

#### Description
Verify Spring Boot extractor handles all path variable patterns:
- `{id}` - Simple
- `{id:[0-9]+}` - With regex
- `{*path}` - Wildcard
- `{id:.*}` - Greedy

#### Impact
- Low priority (likely already works)
- Validation only

#### Effort Estimate
- **Time:** 1 hour
- **Complexity:** Low

---

## Fixed Issues

### ✅ Flask-RESTX Namespace Support

**Fixed:** 2026-04-28
**Original Priority:** 🔴 High

#### Description
Flask extractor did not support Flask-RESTX Namespace and Resource class patterns.

#### Solution Implemented
Added comprehensive Flask-RESTX support in `api_extractor/extractors/python/flask.py`:
- `_extract_namespaces_query()` - Namespace definitions
- `_extract_restx_resources()` - Resource class extraction
- Decorated method support in Resource classes

#### Verified By
- Mentorship Backend (34 endpoints, 10 tests passing)

---

### ✅ Django REST URL Include() Patterns

**Fixed:** 2026-04-28
**Original Priority:** 🔴 High

#### Description
Django REST extractor did not handle two URL inclusion patterns:
1. Module-based: `path('api/circuits/', include('circuits.api.urls'))`
2. Router-based: `path('api/v2/', include(router.urls))`

#### Solution Implemented
Enhanced `api_extractor/extractors/python/django_rest.py`:
- `_extract_url_includes()` - Parse include() patterns
- `_get_url_prefix_for_file()` - Map files to prefixes
- `router_prefixes` tracking for `include(router.urls)` pattern

#### Verified By
- NetBox (772 endpoints, 10 tests passing)
- wger (186 endpoints, 12 tests passing)

---

### ✅ Flask Tuple Methods Parameter

**Fixed:** 2026-04-28
**Original Priority:** 🟡 Medium

#### Description
Flask extractor only supported `methods=['GET']` (list syntax) but not `methods=('GET',)` (tuple syntax).

#### Solution Implemented
Updated `_extract_methods_from_arguments()` in `api_extractor/extractors/python/flask.py`:
```python
# Before: if value_node.type == "list"
# After: if value_node.type in ("list", "tuple")
```

#### Verified By
- Flask RealWorld (19 endpoints, 10 tests passing)

---

## Issue Reporting Guidelines

When adding new issues to this document:

1. **Title:** Brief, descriptive name
2. **Status:** ⏳ Pending | 🔄 In Progress | ✅ Fixed
3. **Priority:** 🔴 High | 🟡 Medium | 🟢 Low
4. **Discovered:** Date and context (which repo)
5. **Description:** What's the issue? Include code examples
6. **Impact:** Which repos/users are affected? What's broken?
7. **Root Cause:** Why does this happen? (technical explanation)
8. **Proposed Solution:** How to fix it? Include code sketches
9. **Effort Estimate:** Time and complexity
10. **Related Issues:** Links to similar problems

---

## Maintenance

**Last Updated:** 2026-04-28
**Next Review:** After completing all 20 repository integrations

**Review Triggers:**
- New repository analysis reveals extractor limitation
- User reports issue with extraction accuracy
- Framework releases breaking changes
- New framework pattern discovered
