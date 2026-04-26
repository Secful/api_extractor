# NestJS Extractor

Extracts REST API routes from NestJS applications with full decorator support and versioning.

## How It Works

### Detection Pattern

NestJS uses TypeScript decorators at two levels:

```typescript
import { Controller, Get, Post, Param, Body } from '@nestjs/common';

@Controller('users')
export class UserController {
  @Get()
  findAll() { return []; }

  @Get(':id')
  findOne(@Param('id') id: string) { return {}; }

  @Post()
  create(@Body() dto: any) { return dto; }
}
```

### Tree-sitter AST Structure

**Controller Pattern:**
```
export_statement
  decorator (@Controller)
    call_expression
      arguments
        string | object (path or config)
  class_declaration
    body
      method_definition
        decorator (@Get, @Post, etc.)
```

### Extraction Process

#### Phase 1: Find Controllers

1. **Locate Controller Classes**
   - Search for classes with `@Controller` decorator
   - Handle both exported and non-exported classes

2. **Parse @Controller Decorator**
   - **String syntax**: `@Controller('users')` → path: `/users`
   - **Object syntax**: `@Controller({ path: 'users', version: '1' })`
     - Extract `path` property
     - Extract `version` property
     - Compose: `/v{version}{path}`

#### Phase 2: Extract Methods

1. **Find Method Decorators**
   - Look for: `@Get()`, `@Post()`, `@Put()`, `@Delete()`, `@Patch()`
   - Parse decorator argument for sub-path

2. **Parse Method Paths**
   - `@Get()` → empty string (root)
   - `@Get('profile')` → `profile`
   - `@Get(':id')` → `:id`

3. **Compose Full Path**
   - Controller path + method path
   - Examples:
     - `/users` + `` → `/users`
     - `/users` + `:id` → `/users/:id`
     - `/v1/products` + `search` → `/v1/products/search`

### Controller Decorator Formats

#### Simple String

```typescript
@Controller('users')
```
**Result:** `/users`

#### Object with Version

```typescript
@Controller({ path: 'products', version: '1' })
```
**Result:** `/v1/products`

#### Nested Path

```typescript
@Controller('api/orders')
```
**Result:** `/api/orders`

### Method Decorator Examples

```typescript
@Controller('users')
export class UserController {
  @Get()                    // → GET /users
  findAll() {}

  @Get(':id')               // → GET /users/:id
  findOne(@Param('id') id: string) {}

  @Post()                   // → POST /users
  create(@Body() dto: any) {}

  @Put(':id')               // → PUT /users/:id
  update(@Param('id') id: string) {}

  @Delete(':id')            // → DELETE /users/:id
  remove(@Param('id') id: string) {}

  @Get('profile')           // → GET /users/profile
  getProfile() {}
}
```

### Versioning

NestJS controller-level versioning is fully supported:

```typescript
@Controller({ path: 'users', version: '1' })
export class UsersV1Controller {
  @Get()  // → GET /v1/users
  findAll() {}
}

@Controller({ path: 'users', version: '2' })
export class UsersV2Controller {
  @Get()  // → GET /v2/users
  findAll() {}
}
```

**Extracted Paths:**
- `/v1/users`
- `/v2/users`

### Example Extraction

**Input:**
```typescript
@Controller({ path: 'products', version: '1' })
export class ProductController {
  @Get()
  list() { return []; }

  @Get(':productId')
  getOne(@Param('productId') productId: string) {
    return { id: productId };
  }

  @Post()
  create(@Body() product: any) {
    return product;
  }
}
```

**Extracted Routes:**
```json
[
  {
    "path": "/v1/products",
    "method": "GET",
    "handler_name": "list"
  },
  {
    "path": "/v1/products/{productId}",
    "method": "GET",
    "handler_name": "getOne",
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
    "path": "/v1/products",
    "method": "POST",
    "handler_name": "create"
  }
]
```

## Features

### ✅ Supported

- **@Controller Decorator**: Both string and object syntax
- **Versioning**: Controller-level versioning
- **HTTP Method Decorators**: Get, Post, Put, Delete, Patch, Head, Options
- **Path Parameters**: `:paramName` syntax
- **Path Composition**: Controller + method path
- **Empty Decorators**: `@Get()` creates root route
- **Nested Paths**: `@Controller('api/orders')`

### ⚠️ Limitations

- **Global Prefix**: Not extracted from `main.ts`
- **RouterModule**: Module-level paths not followed
- **Array Versioning**: `version: ['1', '2']` not supported

### ❌ Not Supported

- **Cross-File Resolution**: Can't follow imports
- **Query Parameters**: `@Query()` decorator not analyzed
- **Body Schemas**: DTO classes not extracted
- **Guards/Interceptors**: Metadata not extracted
- **Custom Decorators**: Only standard HTTP decorators

## Path Composition Layers

NestJS paths can have multiple layers:

```
[Global Prefix] + [Router Module] + [@Controller] + [@Method]
```

### Extracted Layers

✅ **@Controller path**: `@Controller('users')` → `/users`
✅ **@Controller version**: `{ version: '1' }` → `/v1`
✅ **@Method path**: `@Get(':id')` → `/:id`

### Not Extracted (Cross-File)

❌ **Global Prefix**: `app.setGlobalPrefix('api')` in `main.ts`
❌ **Router Module**: `RouterModule.register([{ path: 'v1', ... }])`

These require cross-file analysis which is outside Tree-sitter's scope.

## Workarounds for Limitations

### For Global Prefix

**Don't do this:**
```typescript
// main.ts
app.setGlobalPrefix('api');  // ❌ Not extracted

// user.controller.ts
@Controller('users')  // → /users (missing /api)
```

**Do this instead:**
```typescript
// user.controller.ts
@Controller('api/users')  // → /api/users ✅
```

### For Router Module Paths

**Don't do this:**
```typescript
// app.module.ts
RouterModule.register([
  { path: 'v1', module: UsersModule }  // ❌ Not extracted
])

// user.controller.ts
@Controller('users')  // → /users (missing /v1)
```

**Do this instead:**
```typescript
// user.controller.ts
@Controller('v1/users')  // → /v1/users ✅
// OR
@Controller({ path: 'users', version: '1' })  // → /v1/users ✅
```

## Code Coverage

Significantly improved from 0% → working extraction of 30+ endpoints.

## Testing

Run tests:
```bash
api-extractor extract tests/fixtures/javascript --framework nestjs
```

Sample fixture: `tests/fixtures/javascript/sample_nestjs.ts`

**Test Results:**
- ✅ Simple controllers
- ✅ Versioned controllers
- ✅ Path parameters
- ✅ Empty decorators
- ✅ Nested paths

## Path Normalization

NestJS `:param` → OpenAPI `{param}`:

| NestJS Path | OpenAPI Path |
|-------------|--------------|
| `/users/:id` | `/users/{id}` |
| `/orders/:orderId/items/:itemId` | `/orders/{orderId}/items/{itemId}` |

## Future Enhancements

1. Parse `main.ts` for global prefix
2. Follow `RouterModule.register()` calls
3. Support array versioning: `version: ['1', '2']`
4. Extract `@Query()` parameters
5. Extract DTO class schemas
6. Parse `@ApiProperty()` decorators from swagger
7. Extract guards and interceptors
