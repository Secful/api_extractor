const express = require('express');
const Ajv = require('ajv');

const app = express();
const ajv = new Ajv();

// Separate JSON Schema definition
const createUserSchema = {
  type: 'object',
  properties: {
    email: { type: 'string', format: 'email' },
    name: { type: 'string', minLength: 3, maxLength: 50 },
    age: { type: 'integer', minimum: 18 },
    role: { type: 'string', enum: ['user', 'admin'], default: 'user' }
  },
  required: ['email', 'name']
};

// Custom validate middleware
function validate(schema) {
  const validateFn = ajv.compile(schema);
  return (req, res, next) => {
    if (!validateFn(req.body)) {
      return res.status(400).json({ errors: validateFn.errors });
    }
    next();
  };
}

// Route with validate middleware
app.post('/users', validate(createUserSchema), (req, res) => {
  res.status(201).json({ user: req.body });
});

// Inline JSON Schema
app.post('/products', validate({
  type: 'object',
  properties: {
    name: { type: 'string' },
    price: { type: 'number', minimum: 0 },
    description: { type: 'string' }
  },
  required: ['name', 'price']
}), (req, res) => {
  res.json({ product: req.body });
});

// Query validation
const searchQuerySchema = {
  type: 'object',
  properties: {
    q: { type: 'string' },
    limit: { type: 'integer', minimum: 1, maximum: 100, default: 10 },
    page: { type: 'integer', minimum: 1, default: 1 }
  },
  required: ['q']
};

function validateQuery(schema) {
  const validateFn = ajv.compile(schema);
  return (req, res, next) => {
    if (!validateFn(req.query)) {
      return res.status(400).json({ errors: validateFn.errors });
    }
    next();
  };
}

app.get('/search', validateQuery(searchQuerySchema), (req, res) => {
  res.json({ results: [] });
});

module.exports = app;
