# Fastify Extractor

Extracts REST API routes from Fastify applications.

## How It Works

### Detection Pattern

Fastify routes are similar to Express:

```javascript
const fastify = require('fastify')();

fastify.get('/users/:userId', async (request, reply) => {
  return { id: request.params.userId };
});

fastify.post('/products', {
  schema: {
    body: {
      type: 'object',
      required: ['name'],
      properties: {
        name: { type: 'string' }
      }
    }
  }
}, async (request, reply) => {
  return request.body;
});
```

### Tree-sitter AST Structure

**Simple Route:**
```
expression_statement
  call_expression
    function: member_expression
      object: identifier (fastify)
      property: identifier (get, post, etc.)
    arguments
      string (path)
      arrow_function | function (handler)
```

**Route with Schema:**
```
expression_statement
  call_expression
    function: member_expression
      object: identifier (fastify)
      property: identifier (get, post, etc.)
    arguments
      string (path)
      object (options with schema)
      arrow_function (handler)
```

### Extraction Process

1. **Find Method Calls**
   - Pattern: `fastify.(get|post|put|delete|patch)(...)`
   - HTTP method from property name

2. **Extract Path**
   - First argument must be string
   - Path syntax: `/users/:userId`

3. **Parse Arguments**
   - **2 args**: path + handler
   - **3 args**: path + options/schema + handler
   - Options object may contain route schema (not extracted yet)

4. **Normalize Path**
   - Convert `:param` to `{param}`

### Path Parameter Syntax

Fastify uses colon syntax like Express:

| Fastify | OpenAPI | Type |
|---------|---------|------|
| `:userId` | `{userId}` | string |
| `:id` | `{id}` | string |
| `:productId` | `{productId}` | string |

All parameters default to `string` type.

### Example Extraction

**Input:**
```javascript
fastify.get('/products/:productId', async (request, reply) => {
  return { id: request.params.productId };
});

fastify.put('/products/:productId', async (request, reply) => {
  return { id: request.params.productId, ...request.body };
});
```

**Extracted Routes:**
```json
[
  {
    "path": "/products/{productId}",
    "method": "GET",
    "parameters": [
      {
        "name": "productId",
        "in": "path",
        "type": "string",
        "required": true
      }
    ]
  },
  {
    "path": "/products/{productId}",
    "method": "PUT",
    "parameters": [
      {
        "name": "productId",
        "in": "path",
        "type": "string",
        "required": true
      }
    ]
  }
]
```

## Features

### ✅ Supported

- **HTTP Methods**: `get`, `post`, `put`, `delete`, `patch`, `head`, `options`
- **Path Parameters**: `:paramName` syntax
- **Path Normalization**: `:param` → `{param}`
- **Async Handlers**: Both `async` and regular functions

### ⚠️ Partial Support

- **Route Schemas**: Detected but not extracted
- **Options Object**: Recognized but not parsed

### ❌ Not Supported

- **fastify.register()**: Plugin routes
- **Route Prefixes**: From `prefix` option
- **Schema Extraction**: Request/response schemas
- **Validation**: From schema definitions
- **Hooks**: `preHandler`, `onRequest`, etc.
- **Route Groups**: Via `register()`

## Route Registration

### Simple Route

```javascript
fastify.get('/users', async (request, reply) => {
  return [];
});
```

**Extracted:** GET `/users` ✅

### Route with Schema

```javascript
fastify.post('/users', {
  schema: {
    body: {
      type: 'object',
      required: ['username', 'email'],
      properties: {
        username: { type: 'string' },
        email: { type: 'string', format: 'email' }
      }
    }
  }
}, async (request, reply) => {
  return request.body;
});
```

**Extracted:** POST `/users` (schema not extracted) ⚠️

### Route with Options

```javascript
fastify.get('/products', {
  onRequest: authenticate,
  schema: { ... }
}, async (request, reply) => {
  return [];
});
```

**Extracted:** GET `/products` (options not extracted) ⚠️

## Plugin Routes

Fastify plugins using `register()`:

```javascript
async function userRoutes(fastify, options) {
  fastify.get('/users', async (request, reply) => {
    return [];
  });
}

fastify.register(userRoutes, { prefix: '/api' });
```

**Not detected** - plugin routes require runtime analysis

## Path Normalization

Fastify `:param` → OpenAPI `{param}`:

| Fastify Path | OpenAPI Path |
|--------------|--------------|
| `/users/:id` | `/users/{id}` |
| `/posts/:postId/comments/:commentId` | `/posts/{postId}/comments/{commentId}` |

## Code Coverage

Working extraction confirmed via CLI tests.

## Testing

Run tests:
```bash
api-extractor extract tests/fixtures/javascript --framework fastify
```

Sample fixture: `tests/fixtures/javascript/sample_fastify.js`

## Limitations

1. **Plugin Routes**: Routes in `register()` not detected
2. **Route Prefixes**: Plugin-level prefixes not extracted
3. **Schema Validation**: Request/response schemas not parsed
4. **Hooks**: Pre/post handlers not detected
5. **Encapsulation**: Routes in separate plugins not found
6. **Dynamic Routes**: Routes added conditionally not detected

## Schema Support (Future)

Fastify's built-in schema support could provide rich OpenAPI generation:

```javascript
fastify.post('/users', {
  schema: {
    body: {
      type: 'object',
      required: ['username'],
      properties: {
        username: { type: 'string', minLength: 3 },
        email: { type: 'string', format: 'email' }
      }
    },
    response: {
      200: {
        type: 'object',
        properties: {
          id: { type: 'integer' },
          username: { type: 'string' }
        }
      }
    }
  }
}, handler);
```

This schema is already JSON Schema compatible - perfect for OpenAPI!

## Future Enhancements

1. Extract JSON Schema from route options
2. Parse plugin routes from `register()`
3. Handle route prefixes
4. Extract hooks (preHandler, onRequest, etc.)
5. Support encapsulated routes
6. Parse response schemas
