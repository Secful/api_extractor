const createUser = {
  body: {
    type: 'object',
    properties: {
      email: { type: 'string', format: 'email' },
      password: { type: 'string', minLength: 8 },
      name: { type: 'string' },
      age: { type: 'integer', minimum: 18 }
    },
    required: ['email', 'password', 'name']
  }
};

const getUsers = {
  query: {
    type: 'object',
    properties: {
      page: { type: 'integer', minimum: 1, default: 1 },
      limit: { type: 'integer', minimum: 1, maximum: 100, default: 20 },
      role: { type: 'string', enum: ['user', 'admin'] }
    },
    required: ['page']
  }
};

const updateUser = {
  params: {
    type: 'object',
    properties: {
      id: { type: 'string' }
    },
    required: ['id']
  },
  body: {
    type: 'object',
    properties: {
      name: { type: 'string' },
      email: { type: 'string', format: 'email' }
    }
  }
};

module.exports = { createUser, getUsers, updateUser };
