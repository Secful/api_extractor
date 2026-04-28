/**
 * Sample Express application for testing.
 */

const express = require('express');
const app = express();

// API router with prefix
const apiRouter = express.Router();

// Root endpoint
app.get('/', (req, res) => {
  res.json({ message: 'Hello World' });
});

// User endpoints
app.get('/users/:userId', (req, res) => {
  res.json({ id: req.params.userId });
});

app.post('/users', (req, res) => {
  const user = req.body;
  res.json(user);
});

// Items with query parameters
app.get('/items', (req, res) => {
  const skip = req.query.skip || 0;
  const limit = req.query.limit || 10;
  res.json({ skip, limit });
});

// API router endpoints
apiRouter.get('/products', (req, res) => {
  res.json([]);
});

apiRouter.get('/products/:productId', (req, res) => {
  res.json({ id: req.params.productId });
});

apiRouter.post('/products', (req, res) => {
  res.json(req.body);
});

apiRouter.put('/products/:productId', (req, res) => {
  res.json({ id: req.params.productId, ...req.body });
});

apiRouter.delete('/products/:productId', (req, res) => {
  res.json({ deleted: req.params.productId });
});

// Mount router
app.use('/api', apiRouter);

// Middleware example
const validateItem = (req, res, next) => {
  next();
};

app.post('/orders', validateItem, (req, res) => {
  res.json(req.body);
});

module.exports = app;
