/**
 * Sample Fastify application for testing.
 */

const fastify = require('fastify')();

// Root endpoint
fastify.get('/', async (request, reply) => {
  return { message: 'Hello World' };
});

// User endpoints
fastify.get('/users/:userId', async (request, reply) => {
  return { id: request.params.userId };
});

fastify.post('/users', async (request, reply) => {
  return request.body;
});

// Items with query parameters
fastify.get('/items', async (request, reply) => {
  const { skip = 0, limit = 10 } = request.query;
  return { skip, limit };
});

// Products with schema
fastify.post('/products', {
  schema: {
    body: {
      type: 'object',
      required: ['name', 'price'],
      properties: {
        name: { type: 'string' },
        price: { type: 'number' }
      }
    }
  }
}, async (request, reply) => {
  return request.body;
});

fastify.get('/products/:productId', async (request, reply) => {
  return { id: request.params.productId };
});

fastify.put('/products/:productId', async (request, reply) => {
  return { id: request.params.productId, ...request.body };
});

fastify.delete('/products/:productId', async (request, reply) => {
  return { deleted: request.params.productId };
});

module.exports = fastify;
