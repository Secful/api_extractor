const express = require('express');
const Ajv = require('ajv');
const schemas = require('./json_schema_schemas');

const app = express();
const ajv = new Ajv();

function validate(schema) {
  const validateFn = ajv.compile(schema);
  return (req, res, next) => {
    const data = req.body || req.query || req.params;
    if (!validateFn(data)) {
      return res.status(400).json({ errors: validateFn.errors });
    }
    next();
  };
}

function validateBody(schema) {
  const validateFn = ajv.compile(schema);
  return (req, res, next) => {
    if (!validateFn(req.body)) {
      return res.status(400).json({ errors: validateFn.errors });
    }
    next();
  };
}

function validateQuery(schema) {
  const validateFn = ajv.compile(schema);
  return (req, res, next) => {
    if (!validateFn(req.query)) {
      return res.status(400).json({ errors: validateFn.errors });
    }
    next();
  };
}

// Use imported schemas
app.post('/users', validateBody(schemas.createUser.body), (req, res) => {
  res.status(201).json({ user: req.body });
});

app.get('/users', validateQuery(schemas.getUsers.query), (req, res) => {
  res.json({ users: [] });
});

app.put('/users/:id', validateBody(schemas.updateUser.body), (req, res) => {
  res.json({ user: req.body });
});

module.exports = app;
