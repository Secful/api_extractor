const express = require('express');
const Joi = require('joi');
const { celebrate } = require('celebrate');

const app = express();

// Separate schema definition
const createUserSchema = Joi.object({
  email: Joi.string().email().required(),
  name: Joi.string().min(3).max(50).required(),
  age: Joi.number().integer().min(18),
  role: Joi.string().valid('user', 'admin').default('user')
});

// Custom validate middleware
function validate(schema) {
  return (req, res, next) => {
    const { error } = schema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }
    next();
  };
}

// Route with celebrate middleware - body validation
app.post('/users', celebrate({ body: createUserSchema }), (req, res) => {
  res.status(201).json({ user: req.body });
});

// Route with custom validate middleware
app.post('/api/users', validate(createUserSchema), (req, res) => {
  res.status(201).json({ user: req.body });
});

// Inline schema with celebrate
app.post('/products', celebrate({
  body: Joi.object({
    name: Joi.string().required(),
    price: Joi.number().min(0).required(),
    description: Joi.string()
  })
}), (req, res) => {
  res.json({ product: req.body });
});

// Query validation
const searchSchema = Joi.object({
  q: Joi.string().required(),
  limit: Joi.number().integer().min(1).max(100).default(10),
  page: Joi.number().integer().min(1).default(1)
});

app.get('/search', celebrate({ query: searchSchema }), (req, res) => {
  res.json({ results: [] });
});

module.exports = app;
