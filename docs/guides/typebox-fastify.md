# TypeBox Integration with Fastify

TypeBox is a JSON Schema Type Builder with static type resolution for TypeScript. It provides excellent integration with Fastify for building type-safe APIs with schema validation.

## Overview

TypeBox allows you to define schemas that:
1. Generate JSON Schema for runtime validation
2. Provide full TypeScript type inference
3. Work seamlessly with Fastify's schema validation
4. Enable IDE auto-completion for request/response types

## Installation

```bash
npm install @sinclair/typebox
npm install @fastify/type-provider-typebox
```

## Basic Usage

### Defining Schemas

```typescript
import { Type, Static } from '@sinclair/typebox';

// Basic types
const UserIdSchema = Type.Number({ minimum: 1 });
const EmailSchema = Type.String({ format: 'email' });
const UsernameSchema = Type.String({ minLength: 3, maxLength: 20 });

// Object schema
const UserSchema = Type.Object({
  id: Type.Number(),
  username: UsernameSchema,
  email: EmailSchema,
  createdAt: Type.String({ format: 'date-time' })
});

// Array schema
const UsersArraySchema = Type.Array(UserSchema);

// Optional properties
const UpdateUserSchema = Type.Object({
  username: Type.Optional(UsernameSchema),
  email: Type.Optional(EmailSchema)
});

// Extract TypeScript type from schema
type User = Static<typeof UserSchema>;
// Result: { id: number; username: string; email: string; createdAt: string }
```

### Using with Fastify Routes

```typescript
import Fastify from 'fastify';
import type { TypeBoxTypeProvider } from '@fastify/type-provider-typebox';
import { Type } from '@sinclair/typebox';

const fastify = Fastify();

// Simple route with TypeBox
fastify.withTypeProvider<TypeBoxTypeProvider>().route({
  method: 'GET',
  url: '/users/:id',
  schema: {
    params: Type.Object({
      id: Type.Number({ minimum: 1 })
    }),
    response: {
      200: Type.Object({
        id: Type.Number(),
        username: Type.String(),
        email: Type.String({ format: 'email' })
      })
    }
  },
  handler: async (req, res) => {
    // req.params.id is typed as number
    const userId = req.params.id;

    // Response must match schema
    return {
      id: userId,
      username: 'john_doe',
      email: 'john@example.com'
    };
  }
});
```

## Advanced Patterns

### Reusable Schemas

```typescript
// dtos/user.schema.ts
import { Type } from '@sinclair/typebox';

export const UserSchema = Type.Object({
  id: Type.Number(),
  username: Type.String({ minLength: 3, maxLength: 20 }),
  email: Type.String({ format: 'email' }),
  role: Type.Union([
    Type.Literal('admin'),
    Type.Literal('user'),
    Type.Literal('guest')
  ])
});

export const CreateUserSchema = Type.Object({
  username: Type.String({ minLength: 3, maxLength: 20 }),
  email: Type.String({ format: 'email' }),
  password: Type.String({ minLength: 8 })
});

export const UpdateUserSchema = Type.Partial(
  Type.Pick(CreateUserSchema, ['username', 'email'])
);

// Extract types
export type User = Static<typeof UserSchema>;
export type CreateUser = Static<typeof CreateUserSchema>;
export type UpdateUser = Static<typeof UpdateUserSchema>;
```

### Paginated Response

```typescript
import { Type, Static } from '@sinclair/typebox';

// Generic pagination schema
const PaginationSchema = Type.Object({
  page: Type.Number({ minimum: 1 }),
  limit: Type.Number({ minimum: 1, maximum: 100 }),
  total: Type.Number({ minimum: 0 })
});

// Generic paginated response factory
function PaginatedResponse<T extends TSchema>(itemSchema: T) {
  return Type.Object({
    data: Type.Array(itemSchema),
    pagination: PaginationSchema
  });
}

// Usage
const UserPaginatedResponseSchema = PaginatedResponse(UserSchema);

export const findUsersRequestSchema = Type.Object({
  page: Type.Optional(Type.Number({ minimum: 1, default: 1 })),
  limit: Type.Optional(Type.Number({ minimum: 1, maximum: 100, default: 10 })),
  search: Type.Optional(Type.String())
});

// Route with pagination
fastify.withTypeProvider<TypeBoxTypeProvider>().route({
  method: 'GET',
  url: '/v1/users',
  schema: {
    description: 'Find users with pagination',
    querystring: findUsersRequestSchema,
    response: {
      200: UserPaginatedResponseSchema
    },
    tags: ['users']
  },
  handler: async (req, res) => {
    const { page = 1, limit = 10, search } = req.query;

    // Full type safety
    return {
      data: [
        { id: 1, username: 'john_doe', email: 'john@example.com', role: 'user' }
      ],
      pagination: {
        page,
        limit,
        total: 1
      }
    };
  }
});
```

### Nested Objects and Arrays

```typescript
const AddressSchema = Type.Object({
  street: Type.String(),
  city: Type.String(),
  country: Type.String(),
  zipCode: Type.String()
});

const UserWithAddressSchema = Type.Object({
  id: Type.Number(),
  username: Type.String(),
  email: Type.String({ format: 'email' }),
  addresses: Type.Array(AddressSchema),
  primaryAddress: Type.Optional(AddressSchema)
});
```

### Union Types and Discriminated Unions

```typescript
// Simple union
const StringOrNumber = Type.Union([Type.String(), Type.Number()]);

// Discriminated union
const SuccessResponse = Type.Object({
  status: Type.Literal('success'),
  data: UserSchema
});

const ErrorResponse = Type.Object({
  status: Type.Literal('error'),
  message: Type.String(),
  code: Type.Number()
});

const ApiResponse = Type.Union([SuccessResponse, ErrorResponse]);

// Usage in route
fastify.withTypeProvider<TypeBoxTypeProvider>().route({
  method: 'GET',
  url: '/users/:id',
  schema: {
    params: Type.Object({ id: Type.Number() }),
    response: {
      200: SuccessResponse,
      404: ErrorResponse,
      500: ErrorResponse
    }
  },
  handler: async (req, res) => {
    try {
      const user = await findUser(req.params.id);

      if (!user) {
        return res.status(404).send({
          status: 'error',
          message: 'User not found',
          code: 404
        });
      }

      return { status: 'success', data: user };
    } catch (error) {
      return res.status(500).send({
        status: 'error',
        message: 'Internal server error',
        code: 500
      });
    }
  }
});
```

### Custom Formats and Validation

```typescript
import { Type, FormatRegistry } from '@sinclair/typebox';

// Register custom format
FormatRegistry.Set('phone', (value) => /^\+?[1-9]\d{1,14}$/.test(value));

const ContactSchema = Type.Object({
  name: Type.String(),
  email: Type.String({ format: 'email' }),
  phone: Type.String({ format: 'phone' }) // Custom format
});
```

### Composition with Type Utilities

```typescript
// Partial - all properties optional
const PartialUserSchema = Type.Partial(UserSchema);

// Pick - select specific properties
const UserCredentialsSchema = Type.Pick(UserSchema, ['username', 'email']);

// Omit - exclude specific properties
const UserWithoutIdSchema = Type.Omit(UserSchema, ['id']);

// Extend - add properties
const UserWithTimestampsSchema = Type.Composite([
  UserSchema,
  Type.Object({
    createdAt: Type.String({ format: 'date-time' }),
    updatedAt: Type.String({ format: 'date-time' })
  })
]);

// Intersect - combine types
const AdminUserSchema = Type.Intersect([
  UserSchema,
  Type.Object({
    permissions: Type.Array(Type.String())
  })
]);
```

## Real-World Example

Here's a complete example of a user management module:

```typescript
// modules/user/schemas/user.schema.ts
import { Type, Static } from '@sinclair/typebox';

export const UserRoleSchema = Type.Union([
  Type.Literal('admin'),
  Type.Literal('user'),
  Type.Literal('guest')
]);

export const UserSchema = Type.Object({
  id: Type.Number(),
  username: Type.String({ minLength: 3, maxLength: 20 }),
  email: Type.String({ format: 'email' }),
  role: UserRoleSchema,
  isActive: Type.Boolean(),
  createdAt: Type.String({ format: 'date-time' }),
  updatedAt: Type.String({ format: 'date-time' })
});

export const CreateUserSchema = Type.Object({
  username: Type.String({ minLength: 3, maxLength: 20 }),
  email: Type.String({ format: 'email' }),
  password: Type.String({ minLength: 8 }),
  role: Type.Optional(UserRoleSchema)
});

export const UpdateUserSchema = Type.Partial(
  Type.Pick(UserSchema, ['username', 'email', 'role', 'isActive'])
);

export const FindUsersQuerySchema = Type.Object({
  page: Type.Optional(Type.Number({ minimum: 1, default: 1 })),
  limit: Type.Optional(Type.Number({ minimum: 1, maximum: 100, default: 10 })),
  role: Type.Optional(UserRoleSchema),
  isActive: Type.Optional(Type.Boolean()),
  search: Type.Optional(Type.String())
});

export const UserPaginatedResponseSchema = Type.Object({
  data: Type.Array(UserSchema),
  pagination: Type.Object({
    page: Type.Number(),
    limit: Type.Number(),
    total: Type.Number()
  })
});

// Export types
export type User = Static<typeof UserSchema>;
export type CreateUser = Static<typeof CreateUserSchema>;
export type UpdateUser = Static<typeof UpdateUserSchema>;
export type FindUsersQuery = Static<typeof FindUsersQuerySchema>;
```

```typescript
// modules/user/routes/user.routes.ts
import type { FastifyInstance } from 'fastify';
import type { TypeBoxTypeProvider } from '@fastify/type-provider-typebox';
import { Type } from '@sinclair/typebox';
import {
  UserSchema,
  CreateUserSchema,
  UpdateUserSchema,
  FindUsersQuerySchema,
  UserPaginatedResponseSchema
} from '../schemas/user.schema';

export default async function userRoutes(fastify: FastifyInstance) {
  const server = fastify.withTypeProvider<TypeBoxTypeProvider>();

  // GET /v1/users - List users with pagination
  server.route({
    method: 'GET',
    url: '/v1/users',
    schema: {
      description: 'Find users with filtering and pagination',
      querystring: FindUsersQuerySchema,
      response: {
        200: UserPaginatedResponseSchema
      },
      tags: ['users']
    },
    handler: async (req, res) => {
      const { page = 1, limit = 10, role, isActive, search } = req.query;
      const result = await fastify.userService.findUsers({
        page,
        limit,
        role,
        isActive,
        search
      });

      return res.send(result);
    }
  });

  // GET /v1/users/:id - Get user by ID
  server.route({
    method: 'GET',
    url: '/v1/users/:id',
    schema: {
      description: 'Get user by ID',
      params: Type.Object({
        id: Type.Number({ minimum: 1 })
      }),
      response: {
        200: UserSchema,
        404: Type.Object({
          error: Type.String(),
          message: Type.String()
        })
      },
      tags: ['users']
    },
    handler: async (req, res) => {
      const user = await fastify.userService.findById(req.params.id);

      if (!user) {
        return res.status(404).send({
          error: 'Not Found',
          message: 'User not found'
        });
      }

      return res.send(user);
    }
  });

  // POST /v1/users - Create user
  server.route({
    method: 'POST',
    url: '/v1/users',
    schema: {
      description: 'Create a new user',
      body: CreateUserSchema,
      response: {
        201: UserSchema,
        400: Type.Object({
          error: Type.String(),
          message: Type.String()
        })
      },
      tags: ['users']
    },
    handler: async (req, res) => {
      try {
        const user = await fastify.userService.create(req.body);
        return res.status(201).send(user);
      } catch (error) {
        return res.status(400).send({
          error: 'Bad Request',
          message: error.message
        });
      }
    }
  });

  // PATCH /v1/users/:id - Update user
  server.route({
    method: 'PATCH',
    url: '/v1/users/:id',
    schema: {
      description: 'Update user',
      params: Type.Object({
        id: Type.Number({ minimum: 1 })
      }),
      body: UpdateUserSchema,
      response: {
        200: UserSchema,
        404: Type.Object({
          error: Type.String(),
          message: Type.String()
        })
      },
      tags: ['users']
    },
    handler: async (req, res) => {
      const user = await fastify.userService.update(req.params.id, req.body);

      if (!user) {
        return res.status(404).send({
          error: 'Not Found',
          message: 'User not found'
        });
      }

      return res.send(user);
    }
  });

  // DELETE /v1/users/:id - Delete user
  server.route({
    method: 'DELETE',
    url: '/v1/users/:id',
    schema: {
      description: 'Delete user',
      params: Type.Object({
        id: Type.Number({ minimum: 1 })
      }),
      response: {
        204: Type.Null(),
        404: Type.Object({
          error: Type.String(),
          message: Type.String()
        })
      },
      tags: ['users']
    },
    handler: async (req, res) => {
      const deleted = await fastify.userService.delete(req.params.id);

      if (!deleted) {
        return res.status(404).send({
          error: 'Not Found',
          message: 'User not found'
        });
      }

      return res.status(204).send();
    }
  });
}
```

## Benefits for API Extraction

When using TypeBox with Fastify, API Extractor can:

1. **Extract Schema Definitions**: Detect TypeBox schemas in your route definitions
2. **Type Information**: Extract parameter types, validation rules, and constraints
3. **Response Schemas**: Document expected response formats
4. **Generate OpenAPI**: Convert TypeBox schemas to OpenAPI specification

## Best Practices

### 1. Organize Schemas by Module

```
src/
├── modules/
│   ├── user/
│   │   ├── schemas/
│   │   │   ├── user.schema.ts
│   │   │   ├── create-user.schema.ts
│   │   │   └── update-user.schema.ts
│   │   ├── routes/
│   │   │   └── user.routes.ts
│   │   └── services/
│   │       └── user.service.ts
```

### 2. Export Types from Schemas

```typescript
export type User = Static<typeof UserSchema>;
export type CreateUser = Static<typeof CreateUserSchema>;
```

### 3. Use Schema Composition

```typescript
// Don't repeat yourself
const BaseUserSchema = Type.Object({
  username: Type.String(),
  email: Type.String({ format: 'email' })
});

const UserSchema = Type.Composite([
  BaseUserSchema,
  Type.Object({ id: Type.Number() })
]);

const CreateUserSchema = Type.Composite([
  BaseUserSchema,
  Type.Object({ password: Type.String({ minLength: 8 }) })
]);
```

### 4. Validate Early

```typescript
// Use preValidation hook for custom validation
fastify.route({
  method: 'POST',
  url: '/users',
  schema: { body: CreateUserSchema },
  preValidation: async (req, res) => {
    // Custom validation logic
    if (await userExists(req.body.email)) {
      throw new Error('Email already exists');
    }
  },
  handler: async (req, res) => {
    // Handler logic
  }
});
```

### 5. Document with OpenAPI Tags

```typescript
schema: {
  description: 'Create a new user',
  body: CreateUserSchema,
  response: { 201: UserSchema },
  tags: ['users'],
  summary: 'Create user',
  security: [{ bearerAuth: [] }]
}
```

## Resources

- [TypeBox GitHub](https://github.com/sinclairzx81/typebox)
- [TypeBox Documentation](https://github.com/sinclairzx81/typebox#readme)
- [Fastify Type Providers](https://fastify.dev/docs/latest/Reference/Type-Providers/)
- [@fastify/type-provider-typebox](https://github.com/fastify/fastify-type-provider-typebox)

## See Also

- [Fastify Framework Guide](../frameworks/javascript.md#fastify)
- [JavaScript/TypeScript Frameworks](../frameworks/javascript.md)
