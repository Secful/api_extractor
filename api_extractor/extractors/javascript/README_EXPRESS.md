# Express Extractor

Extracts REST API routes from Express.js applications including Router support.

## How It Works

### Detection Pattern

Express routes are defined as method calls:

```javascript
const express = require('express');
const app = express();
const router = express.Router();

app.get('/users/:userId', (req, res) => {
  res.json({ id: req.params.userId });
});

router.post('/products', (req, res) => {
  res.json(req.body);
});

app.use('/api', router);
```

### Tree-sitter AST Structure

**Route Definition:**
```
expression_statement
  call_expression
    function: member_expression
      object: identifier (app or router)
      property: identifier (get, post, etc.)
    arguments
      string (path)
      [identifiers (middleware)]
      arrow_function | function (handler)
```

**Router Mounting:**
```
expression_statement
  call_expression
    function: member_expression
      object: identifier (app)
      property: identifier ("use")
    arguments
      string (mount_path)
      identifier (router)
```

### Extraction Process

#### Phase 1: Router Discovery

1. **Find Router Creation**
   - Look for `express.Router()` calls
   - Track variable name: `const router = express.Router()`

2. **Find Router Mounting**
   - Look for `app.use(path, router)` calls
   - Map router variable to mount path
   - Example: `app.use('/api', apiRouter)` → `apiRouter` maps to `/api`

#### Phase 2: Route Extraction

1. **Find Method Calls**
   - Pattern: `(app|router).(get|post|put|delete|patch)(...)`
   - HTTP method from property name

2. **Extract Path**
   - First argument must be string
   - Path syntax: `/users/:userId`

3. **Parse Arguments**
   - Path string (required)
   - Middleware functions (optional, in middle)
   - Handler function (last argument)

4. **Compose Full Path**
   - If route on router: mount_path + route_path
   - Example: `/api` + `/users` → `/api/users`

### Path Parameter Syntax

Express uses colon syntax:

| Express | OpenAPI | Type |
|---------|---------|------|
| `:userId` | `{userId}` | string |
| `:id` | `{id}` | string |
| `:productId` | `{productId}` | string |

All parameters default to `string` type.

### Example Extraction

**Input:**
```javascript
const apiRouter = express.Router();

apiRouter.get('/products/:productId', (req, res) => {
  res.json({ id: req.params.productId });
});

app.use('/api/v1', apiRouter);
```

**Extracted Route:**
```json
{
  "path": "/api/v1/products/{productId}",
  "method": "GET",
  "parameters": [
    {
      "name": "productId",
      "location": "path",
      "type": "string",
      "required": true
    }
  ]
}
```

**Generated OpenAPI:**
```yaml
/api/v1/products/{productId}:
  get:
    tags: [express]
    parameters:
      - name: productId
        in: path
        required: true
        schema:
          type: string
```

## Features

### ✅ Supported

- **HTTP Methods**: `get`, `post`, `put`, `delete`, `patch`, `head`, `options`
- **Express.Router()**: Router instances
- **Router Mounting**: `app.use(path, router)`
- **Path Parameters**: `:paramName` syntax
- **Middleware Detection**: Identifies middleware in route chain
- **Path Composition**: Router mount path + route path

### ⚠️ Partial Support

- **Middleware**: Detected but not analyzed
- **Query Parameters**: Not extracted from `req.query`
- **Request Body**: Not extracted

### ❌ Not Supported

- **Route Arrays**: `app.route('/users').get(...).post(...)`
- **Router-Level Middleware**: `router.use(middleware)`
- **Regex Paths**: `/users/:id(\\d+)/`
- **Optional Parameters**: `/users/:id?`
- **Wildcard Routes**: `/files/*`
- **Parameter Validation**: From middleware

## Router Composition

### Single Router

```javascript
const router = express.Router();
router.get('/users', handler);
app.use('/api', router);
```

**Extracted:** `/api/users` ✅

### Multiple Routers

```javascript
const usersRouter = express.Router();
const productsRouter = express.Router();

usersRouter.get('/', handler);
productsRouter.get('/', handler);

app.use('/users', usersRouter);
app.use('/products', productsRouter);
```

**Extracted:**
- `/users` from usersRouter
- `/products` from productsRouter ✅

### Nested Routers

```javascript
const apiRouter = express.Router();
const v1Router = express.Router();

v1Router.get('/users', handler);
apiRouter.use('/v1', v1Router);
app.use('/api', apiRouter);
```

**Extracted:** `/v1/users` (missing `/api` prefix) ⚠️

Only one level of router mounting is tracked.

## Middleware Handling

### Route-Level Middleware

```javascript
app.post('/orders', validateOrder, authenticate, (req, res) => {
  res.json(req.body);
});
```

**Detection:** Middleware functions identified (validateOrder, authenticate)
**Extraction:** Not included in OpenAPI spec (future enhancement)

### Router-Level Middleware

```javascript
router.use(authenticate);
router.get('/profile', (req, res) => {});
```

**Not detected** - router-level middleware not tracked

## Path Normalization

Express `:param` → OpenAPI `{param}`:

| Express Path | OpenAPI Path |
|--------------|--------------|
| `/users/:id` | `/users/{id}` |
| `/posts/:postId/comments/:commentId` | `/posts/{postId}/comments/{commentId}` |

## Code Coverage

Tests confirm working extraction of routes with proper path composition.

## Testing

Run tests:
```bash
api-extractor extract tests/fixtures/javascript --framework express
```

Sample fixture: `tests/fixtures/javascript/sample_express.js`

## Limitations

1. **Single Router Level**: Only one level of `app.use()` mounting
2. **Nested Routers**: Multi-level router composition not supported
3. **Route Arrays**: `.route()` method chaining not parsed
4. **Dynamic Routes**: Routes added in loops not detected
5. **Regex Patterns**: Regex paths not parsed
6. **Optional Params**: `:param?` not handled
7. **Middleware Analysis**: Not extracted to OpenAPI

## Future Enhancements

1. Multi-level router composition
2. `.route()` method chaining
3. Middleware extraction (auth, validation)
4. Query parameter detection from `req.query` usage
5. Request body schema from `req.body` usage
6. Optional and regex parameters
