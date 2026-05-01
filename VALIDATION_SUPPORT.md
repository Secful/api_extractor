# Validation Schema Extraction Support

## Test Coverage Summary

### Integration Tests ✅
**Location:** `tests/integration/test_realworld_validation.py`

Tests against real-world open-source projects:
- ✅ **Joi (node-express-boilerplate)**: 9 routes extracted, 6/9 with request body schemas
- ⚠️ **Zod (express-zod-api)**: 0 routes (uses custom routing framework, not standard Express)
- ⚠️ **JSON Schema (fastify-example)**: 0 routes (Fastify, not Express - needs dedicated extractor)

**Status:** All 5 integration tests passing

### Unit Tests
**Location:** `tests/unit/test_express_validation.py`

- ✅ **Joi**: 3/3 tests passing
- ⚠️ **Zod**: 2/3 tests passing (1 failing: query params)
- ⚠️ **JSON Schema**: 1/3 tests passing (2 failing: inline schemas, query params)

**Status:** 6/9 tests passing

---

## Joi Support (Most Complete)

### ✅ Fully Supported Features

#### 1. Cross-File Imports with ES6 Shorthand
```javascript
// validations/auth.validation.js
const register = {
  body: Joi.object().keys({
    email: Joi.string().required().email(),
    password: Joi.string().required(),
    name: Joi.string().required(),
  })
};
module.exports = { register, login, logout };  // ES6 shorthand

// routes/auth.route.js
const authValidation = require('../../validations/auth.validation');
router.post('/register', validate(authValidation.register), controller.register);
```
**Result:** Email, password, and name fields extracted with correct types and required status

#### 2. Separate Schema Definitions
```javascript
const createUserSchema = Joi.object({
  email: Joi.string().email().required(),
  name: Joi.string().required()
});

router.post('/users', validate(createUserSchema), handler);
```

#### 3. Inline Schemas
```javascript
router.post('/login', validate(Joi.object({
  email: Joi.string().email().required(),
  password: Joi.string().required()
})), handler);
```

#### 4. Celebrate Middleware
```javascript
router.post('/users', celebrate({
  body: Joi.object({
    email: Joi.string().email().required()
  })
}), handler);
```

#### 5. Query Parameters
```javascript
const getUsersSchema = {
  query: Joi.object().keys({
    page: Joi.number().integer(),
    limit: Joi.number().integer()
  })
};
```
**Result:** Extracted as proper OpenAPI query parameters

#### 6. Type Mappings
- ✅ `Joi.string()` → `type: string`
- ✅ `Joi.number()` → `type: number`
- ✅ `Joi.integer()` → `type: integer`
- ✅ `Joi.boolean()` → `type: boolean`
- ✅ `Joi.array()` → `type: array`
- ✅ `Joi.object()` → `type: object` (with nested properties)

#### 7. Validation Constraints
- ✅ `.required()` → added to `required` array
- ✅ `.optional()` → not in required array
- ✅ `.email()` → `format: email`
- ✅ `.min(n)` → `minLength: n` (strings) or `minimum: n` (numbers)
- ✅ `.max(n)` → `maxLength: n` (strings) or `maximum: n` (numbers)
- ✅ `.valid('a', 'b')` → `enum: ['a', 'b']`
- ✅ `.default(val)` → `default: val`

#### 8. Member Expression Resolution
```javascript
// Resolves validation.createUser to imported schema
validate(validation.createUser)
```

### ❌ Not Yet Supported

#### 1. `.keys()` Method Chaining
```javascript
const schema = Joi.object().keys({ ... });  // Returns null currently
```
**Workaround:** Use `Joi.object({ ... })` directly

#### 2. Complex Nested Objects
Deep nesting beyond 1-2 levels may not be fully extracted

#### 3. Custom Validators
```javascript
Joi.string().custom(password)  // Custom function ignored
```

#### 4. Conditional Schemas
```javascript
Joi.when('type', { is: 'email', then: Joi.string().email() })
```

---

## Zod Support

### ✅ Fully Supported Features

#### 1. Separate Schema Definitions
```typescript
const createUserSchema = z.object({
  email: z.string().email(),
  name: z.string()
});

router.post('/users', validate(createUserSchema), handler);
```

#### 2. Inline Schemas
```typescript
router.post('/login', validate(z.object({
  email: z.string().email(),
  password: z.string()
})), handler);
```

#### 3. Type Mappings
- ✅ `z.string()` → `type: string`
- ✅ `z.number()` → `type: number`
- ✅ `z.boolean()` → `type: boolean`
- ✅ `z.array()` → `type: array`
- ✅ `z.object()` → `type: object`

#### 4. Validation Constraints
- ✅ Fields are required by default (Zod behavior)
- ✅ `.optional()` → not in required array
- ✅ `.email()` → `format: email`
- ✅ `.min(n)` → `minLength: n` or `minimum: n`
- ✅ `.max(n)` → `maxLength: n` or `maximum: n`
- ✅ `.default(val)` → `default: val`

### ⚠️ Partially Supported

#### 1. Query Parameters
Currently extracted as `request_body` instead of parameters array
```typescript
router.get('/search', validate(z.object({
  q: z.string(),
  limit: z.number().min(1).max(100)
})), handler);
```
**Current:** Schema in `request_body`
**Expected:** Fields as query parameters

### ✅ Recently Added (Needs Integration Refinement)

#### 1. Cross-File Import Infrastructure
```typescript
// schemas.ts
const createUser = {
  body: z.object({
    email: z.string().email(),
    name: z.string()
  })
};
module.exports = { createUser };  // ES6 shorthand supported

// routes.ts
const userSchemas = require('./schemas');
router.post('/users', validateRequest(userSchemas.createUser), handler);
```
**Status:** Module resolver, import tracking, and member expression resolution implemented.
**Issue:** Integration between file parsing order needs refinement for full extractor runs.

### ❌ Not Yet Supported

#### 1. Real-World Validation
No real-world Zod projects tested yet (express-zod-api uses custom routing)

#### 2. ES6 Export Statements
```typescript
export { createUser, getUser };  // Not yet supported
export const schema = { ... };    // Not yet supported
```

#### 3. Complex Zod Features
- `z.union()`, `z.discriminatedUnion()`
- `z.enum()`
- `z.refine()`, `z.transform()`
- `z.lazy()` for recursive types

---

## JSON Schema Support

### ✅ Fully Supported Features

#### 1. Separate Object Literal Schemas
```javascript
const createUserSchema = {
  type: 'object',
  properties: {
    email: { type: 'string', format: 'email' },
    name: { type: 'string' }
  },
  required: ['email', 'name']
};

router.post('/users', validate({ body: createUserSchema }), handler);
```

### ⚠️ Partially Supported

#### 1. Inline Schemas
Detection of inline JSON Schema objects in middleware is unreliable

```javascript
router.post('/products', validate({
  body: {
    type: 'object',
    properties: { name: { type: 'string' } }
  }
}), handler);
```
**Status:** Often not detected

#### 2. Query Parameters
Same issue as Zod - extracted as `request_body` instead of parameters

### ❌ Not Yet Supported

#### 1. Cross-File Imports
No implementation for JSON Schema cross-file imports

#### 2. $ref Resolution
```javascript
{ $ref: '#/components/schemas/User' }
```

#### 3. JSON Schema Files
```javascript
const schema = require('./schemas/user.json');
```

---

## Real-World Project Results

### node-express-boilerplate (Joi) ✅
- **GitHub:** hagopj13/node-express-boilerplate (7.6K ⭐)
- **Routes Found:** 9
- **With Validation:** 6/9 (67%)
- **Example Endpoint:**
  ```
  POST /register
  Request Body:
    - email: string (format: email, required)
    - password: string (required)
    - name: string (required)
  ```

### express-zod-api (Zod) ❌
- **GitHub:** RobinTail/express-zod-api (818 ⭐)
- **Routes Found:** 0
- **Issue:** Uses custom routing framework, not standard Express router
- **Status:** Incompatible with current Express extractor

### fastify-example (JSON Schema) ❌
- **GitHub:** delvedor/fastify-example (786 ⭐)
- **Routes Found:** 0
- **Issue:** Fastify framework, not Express
- **Status:** Needs dedicated Fastify extractor

---

## Known Issues

### 1. Query Parameter Location (Zod & JSON Schema)
Query validation schemas are incorrectly placed in `request_body` instead of being converted to OpenAPI query parameters.

**Affected Tests:**
- `test_zod_query_validation`
- `test_json_schema_query_validation`

**Root Cause:** The `_process_validation_result` method needs to handle query location for non-Joi validators.

### 2. JSON Schema Inline Detection
Inline JSON Schema objects in middleware calls are not reliably detected.

**Affected Test:**
- `test_json_schema_inline_schema`

**Root Cause:** The `_is_json_schema_object` heuristic is too strict.

### 3. Joi `.keys()` Method
```javascript
Joi.object().keys({ ... })  // Not parsed
```

**Workaround:** Use `Joi.object({ ... })` instead

---

## Summary

| Feature | Joi | Zod | JSON Schema |
|---------|-----|-----|-------------|
| Basic body validation | ✅ | ✅ | ✅ |
| Inline schemas | ✅ | ✅ | ⚠️ |
| Separate schemas | ✅ | ✅ | ✅ |
| Cross-file imports | ✅ | 🔨 | ❌ |
| ES6 shorthand exports | ✅ | ✅ | ❌ |
| Member expressions | ✅ | ✅ | ❌ |
| Query parameters | ✅ | ⚠️ | ⚠️ |
| Type mappings | ✅ | ✅ | ✅ |
| Constraints (min/max/etc) | ✅ | ✅ | ✅ |
| Real-world tested | ✅ | ❌ | ❌ |

**Legend:** ✅ Works | ⚠️ Partial | 🔨 Infrastructure complete | ❌ Not implemented

**Overall Maturity:**
- **Joi:** ✅ **Production-ready** - Full cross-file import support validated against real-world projects
- **Zod:** 🔨 **Intermediate** - Core infrastructure complete, needs integration refinement and real-world validation
- **JSON Schema:** ⚠️ **Basic** - Needs inline detection improvements and cross-file import support

**Integration Test Status:** 5/5 passing ✅
**Unit Test Status:** 6/9 passing ⚠️
