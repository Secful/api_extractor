# JavaScript/TypeScript Framework Support

API Extractor supports four major JavaScript/TypeScript web frameworks with comprehensive route extraction capabilities.

## Supported Frameworks

| Framework | Version | Detection Method | Real-World Tested |
|-----------|---------|------------------|-------------------|
| **Express** | 4.x+ | `package.json`, imports | ✅ Express Examples |
| **NestJS** | 8.x+ | `package.json`, `@nestjs/*` imports | ✅ NestJS RealWorld |
| **Fastify** | 3.x+ | `package.json`, imports | ✅ Fastify Demo |
| **Next.js** | 13.x+ | `package.json`, directory structure, imports | ✅ Cal.com, Dub |

## Key Features

- Router and controller detection
- Decorator-based routing (NestJS: `@Get()`, `@Post()`)
- File-system routing (Next.js)
- Dynamic routes and path parameters
- Middleware and plugin patterns
- TypeScript type extraction

## Express

Minimal and flexible Node.js web application framework.

### Example

```javascript
const express = require('express');
const app = express();
const router = express.Router();

router.get('/users', (req, res) => {
  res.json({ users: [] });
});

router.get('/users/:id', (req, res) => {
  res.json({ id: req.params.id });
});

router.post('/users', (req, res) => {
  res.status(201).json({ user: req.body });
});

app.use('/api', router);
```

**Detection:** `express` in `package.json`
**Validated on:** Express Examples, Postman Tutorial Patterns

### Supported Features

- ✅ Router mounting with `app.use()`
- ✅ Route methods (`router.get()`, `router.post()`, etc.)
- ✅ Path parameters (`:param`)
- ✅ Middleware detection
- ✅ Multiple routers with prefixes
- ✅ API versioning patterns

### Validation

Tested against **Postman's "How to Create a REST API with Node.js and Express" tutorial**:
- ✅ Basic CRUD operations
- ✅ Router mounting with `app.use()`
- ✅ Multiple routers with different prefixes
- ✅ Middleware in routes
- ✅ Nested path parameters
- ✅ API versioning patterns

## NestJS

Progressive Node.js framework for building efficient and scalable server-side applications.

### Example

```typescript
@Controller('users')
export class UsersController {
  @Get()
  findAll(): Promise<User[]> {
    return this.usersService.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string): Promise<User> {
    return this.usersService.findOne(id);
  }

  @Post()
  create(@Body() user: CreateUserDto): Promise<User> {
    return this.usersService.create(user);
  }
}
```

**Detection:** `@nestjs/*` packages in `package.json`
**Validated on:** NestJS RealWorld, truthy production app

### Supported Features

- ✅ `@Controller()` decorator with path prefixes
- ✅ HTTP method decorators (`@Get()`, `@Post()`, `@Put()`, `@Delete()`, `@Patch()`)
- ✅ Path parameters (`:param`)
- ✅ Multiple decorators per method
- ✅ Guard and interceptor decorators (correctly ignored)
- ✅ TypeScript type extraction

### Validation

Tested against **truthy** (https://github.com/gobeam/truthy), a production NestJS application:
- ✅ 39 endpoints successfully extracted
- ✅ Controller path prefixes
- ✅ HTTP method decorators with and without paths
- ✅ Multiple decorators per method (`@Get()` + `@ApiQuery()`)
- ✅ Path parameter extraction and normalization
- ✅ Guard and interceptor decorators (correctly ignored)

## Fastify

Fast and low overhead web framework for Node.js.

### Example

```javascript
const fastify = require('fastify')();

fastify.get('/users', async (request, reply) => {
  return { users: [] };
});

fastify.get('/users/:id', async (request, reply) => {
  return { id: request.params.id };
});

fastify.post('/users', async (request, reply) => {
  return { user: request.body };
});
```

**Detection:** `fastify` in `package.json`
**Validated on:** Fastify Demo

### Supported Features

- ✅ Route registration (`fastify.get()`, `fastify.post()`, etc.)
- ✅ Path parameters (`:param`)
- ✅ Schema validation
- ✅ Plugin patterns

## Next.js

React framework with API Routes support (App Router & Pages Router).

### App Router (Next.js 13+)

```typescript
// app/api/users/route.ts
export async function GET() {
  return Response.json({ users: [] })
}

export async function POST(request: Request) {
  const body = await request.json()
  return Response.json({ user: body })
}

// app/api/users/[id]/route.ts → /api/users/:id
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  return Response.json({ user: { id } })
}
```

### Pages Router (Legacy)

```typescript
// pages/api/users.ts
export default function handler(req, res) {
  if (req.method === 'GET') {
    res.status(200).json({ users: [] })
  }
  if (req.method === 'POST') {
    res.status(201).json({ user: req.body })
  }
}

// pages/api/users/[id].ts → /api/users/:id
export default function handler(req, res) {
  const { id } = req.query
  res.status(200).json({ user: { id } })
}
```

**Detection:** Package dependency, directory structure (`app/api/`, `pages/api/`), or imports
**Validated on:** Cal.com (11 endpoints), Dub (31 endpoints)

### Supported Features

- ✅ File-system based routing
- ✅ Dynamic routes with brackets (`[id]`)
- ✅ App Router (route.ts files with exported functions)
- ✅ Pages Router (api files with default handler)
- ✅ Catch-all routes (`[...slug]`)
- ✅ TypeScript support

## Usage

### Basic Extraction

```bash
# Detect and extract from Node.js project
api-extractor extract /path/to/node/project
```

### Framework-Specific Extraction

```bash
# Express project
api-extractor extract /path/to/express-app --output api.json

# NestJS project
api-extractor extract /path/to/nestjs-app --output nestjs-api.yaml --format yaml

# Next.js project
api-extractor extract /path/to/nextjs-app --output nextjs-api.json
# Detects: app/api/ or pages/api/ directories

# Fastify project
api-extractor extract /path/to/fastify-app --output fastify-api.json
```

## Pattern Support

### Path Parameters

All JavaScript/TypeScript frameworks support path parameters:

- **Express/NestJS/Fastify**: `/users/:id` → `/users/{id}`
- **Next.js**: `/users/[id]` → `/users/{id}`

### Router/Controller Mounting

- **Express**: `app.use('/api', router)` - Correctly applies prefix to all routes
- **NestJS**: `@Controller('users')` - Path composition with controller decorators
- **Fastify**: `fastify.register(routes, { prefix: '/api' })` - Plugin prefixes

### Middleware & Guards

- **Express**: Detects middleware in route chains (e.g., `app.get('/path', auth, handler)`)
- **NestJS**: Recognizes guards (`@UseGuards()`) and other decorators without treating them as routes

## Validation Library Support

API Extractor can extract validation schemas from common JavaScript/TypeScript libraries:

| Framework | Validation Libraries |
|-----------|---------------------|
| Express | Joi, Zod, AJV |
| NestJS | class-validator, class-transformer, TypeScript Types |
| Fastify | Fastify JSON Schema |
| Next.js | Zod |

## Known Limitations

1. **Cross-file module resolution**: Extractors work best with single-file or same-directory patterns. Express routers defined in separate files and imported via `require()` may not have their mount paths correctly applied
2. **Dynamic routes**: Routes defined programmatically (e.g., generated in loops, loaded from config) cannot be extracted
3. **Type inference**: For untyped JavaScript code, parameter types default to `string`

## Troubleshooting

### No endpoints found

- Ensure you're running the extractor on the source directory (not `dist`, `build`, or `node_modules`)
- Check that the framework is correctly detected with `--verbose` flag
- For Next.js: Verify `app/api/` or `pages/api/` directories exist

### Routes missing from output

- **Express**: Ensure routers are defined and mounted in the same file
- **NestJS**: Verify controllers are decorated with `@Controller()` and methods with HTTP decorators
- **Next.js**: Check that route files follow naming conventions (`route.ts` for App Router, `[id].ts` for dynamic routes)

### Path parameters not extracted

- Check that parameter syntax matches the framework:
  - Express/NestJS/Fastify: `:paramName`
  - Next.js: `[paramName]`

## Docker Image Extraction

When extracting from Docker images:

| Status | Notes |
|--------|-------|
| ⚠️ **Varies** | Depends on build configuration |

- **Development images**: Source available as-is
- **Production images**: May be transpiled/minified - source maps needed for TypeScript
- **Next.js**: Apps may be optimized/bundled

For production Docker images, consider using development images or including source maps in your build process.
