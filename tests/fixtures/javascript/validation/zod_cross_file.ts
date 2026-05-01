/**
 * Express routes with Zod cross-file imports
 */
import express from 'express';
const userSchemas = require('./zod_schemas');

const router = express.Router();

// Mock validation middleware
function validateRequest(schema: any) {
  return (req: any, res: any, next: any) => next();
}

// Routes using imported schemas
router.post('/users', validateRequest(userSchemas.createUser), (req, res) => {
  res.json({ message: 'User created' });
});

router.get('/users', validateRequest(userSchemas.getUsers), (req, res) => {
  res.json({ users: [] });
});

router.put('/users/:id', validateRequest(userSchemas.updateUser), (req, res) => {
  res.json({ message: 'User updated' });
});

export default router;
