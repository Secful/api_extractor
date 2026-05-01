import express from 'express';
import { z } from 'zod';

const app = express();

// Separate schema definition
const createUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(3).max(50),
  age: z.number().int().min(18).optional(),
  role: z.enum(['user', 'admin']).default('user')
});

// Custom validate middleware
function validateRequest(schema: z.ZodSchema) {
  return (req: any, res: any, next: any) => {
    try {
      schema.parse(req.body);
      next();
    } catch (error) {
      res.status(400).json({ error });
    }
  };
}

// Route with validate middleware
app.post('/users', validateRequest(createUserSchema), (req, res) => {
  res.status(201).json({ user: req.body });
});

// Inline schema
app.post('/products', validateRequest(z.object({
  name: z.string(),
  price: z.number().min(0),
  description: z.string().optional()
})), (req, res) => {
  res.json({ product: req.body });
});

// Query validation
const searchQuerySchema = z.object({
  q: z.string(),
  limit: z.number().int().min(1).max(100).default(10).optional(),
  page: z.number().int().min(1).default(1).optional()
});

function validateRequestQuery(schema: z.ZodSchema) {
  return (req: any, res: any, next: any) => {
    try {
      schema.parse(req.query);
      next();
    } catch (error) {
      res.status(400).json({ error });
    }
  };
}

app.get('/search', validateRequestQuery(searchQuerySchema), (req, res) => {
  res.json({ results: [] });
});

export default app;
