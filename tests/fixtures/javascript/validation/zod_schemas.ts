/**
 * Zod schema definitions file (simulating cross-file imports)
 */
import { z } from 'zod';

const createUser = {
  body: z.object({
    email: z.string().email(),
    password: z.string().min(8),
    name: z.string(),
    age: z.number().optional()
  })
};

const getUsers = {
  query: z.object({
    page: z.number().int().min(1).default(1),
    limit: z.number().int().min(1).max(100).default(10),
    search: z.string().optional()
  })
};

const updateUser = {
  body: z.object({
    email: z.string().email().optional(),
    name: z.string().optional()
  })
};

// CommonJS export with ES6 shorthand
module.exports = {
  createUser,
  getUsers,
  updateUser
};
