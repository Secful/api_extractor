"""
Test Express extractor against common patterns from Express REST API tutorials.

This validates that our extractor handles typical patterns taught in tutorials like:
- Postman's "How to Create a REST API with Node.js and Express"
- Express.js official guide
- Common REST API patterns
"""

import os
import tempfile
import pytest
from api_extractor.extractors.javascript.express import ExpressExtractor
from api_extractor.core.models import HTTPMethod


def test_basic_crud_operations():
    """Test basic CRUD operation patterns."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

// CREATE
app.post('/books', (req, res) => {
  res.json({ id: 1, title: req.body.title });
});

// READ all
app.get('/books', (req, res) => {
  res.json([]);
});

// READ one
app.get('/books/:id', (req, res) => {
  res.json({ id: req.params.id });
});

// UPDATE
app.put('/books/:id', (req, res) => {
  res.json({ id: req.params.id, ...req.body });
});

// DELETE
app.delete('/books/:id', (req, res) => {
  res.status(204).send();
});
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Verify all CRUD operations
        assert ("/books", HTTPMethod.POST) in paths
        assert ("/books", HTTPMethod.GET) in paths
        assert ("/books/{id}", HTTPMethod.GET) in paths
        assert ("/books/{id}", HTTPMethod.PUT) in paths
        assert ("/books/{id}", HTTPMethod.DELETE) in paths


def test_router_with_mounting():
    """Test express.Router() with app.use() mounting."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

const userRouter = express.Router();

userRouter.get('/', (req, res) => {
  res.json([]);
});

userRouter.get('/:id', (req, res) => {
  res.json({ id: req.params.id });
});

userRouter.post('/', (req, res) => {
  res.status(201).json(req.body);
});

// Mount router at /users
app.use('/users', userRouter);
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Verify router mounting applies prefix
        # Note: router.get('/') creates '/users/' (trailing slash is preserved)
        assert ("/users/", HTTPMethod.GET) in paths or ("/users", HTTPMethod.GET) in paths
        assert ("/users/{id}", HTTPMethod.GET) in paths
        assert ("/users/", HTTPMethod.POST) in paths or ("/users", HTTPMethod.POST) in paths


def test_multiple_routers():
    """Test multiple routers with different prefixes."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

const authRouter = express.Router();
authRouter.post('/login', (req, res) => {
  res.json({ token: 'abc123' });
});

const adminRouter = express.Router();
adminRouter.get('/dashboard', (req, res) => {
  res.json({ stats: {} });
});

app.use('/auth', authRouter);
app.use('/admin', adminRouter);
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Verify both routers work with their prefixes
        assert ("/auth/login", HTTPMethod.POST) in paths
        assert ("/admin/dashboard", HTTPMethod.GET) in paths


def test_middleware_in_routes():
    """Test routes with middleware functions."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

const authenticate = (req, res, next) => {
  next();
};

const validateBody = (req, res, next) => {
  next();
};

// Single middleware
app.get('/profile', authenticate, (req, res) => {
  res.json({ user: 'john' });
});

// Multiple middleware
app.post('/items', authenticate, validateBody, (req, res) => {
  res.status(201).json(req.body);
});
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Should extract routes even with middleware
        assert ("/profile", HTTPMethod.GET) in paths
        assert ("/items", HTTPMethod.POST) in paths


def test_nested_path_parameters():
    """Test nested resources with multiple path parameters."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

// Nested resource pattern
app.get('/users/:userId/posts/:postId', (req, res) => {
  res.json({
    userId: req.params.userId,
    postId: req.params.postId
  });
});

app.get('/users/:userId/posts', (req, res) => {
  res.json([]);
});
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Verify nested paths with multiple parameters
        assert ("/users/{userId}/posts/{postId}", HTTPMethod.GET) in paths
        assert ("/users/{userId}/posts", HTTPMethod.GET) in paths

        # Check parameters are extracted
        nested_ep = paths[("/users/{userId}/posts/{postId}", HTTPMethod.GET)]
        assert len(nested_ep.parameters) == 2
        param_names = {p.name for p in nested_ep.parameters}
        assert "userId" in param_names
        assert "postId" in param_names


def test_api_versioning_pattern():
    """Test API versioning with routers."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

const v1Router = express.Router();
v1Router.get('/users', (req, res) => {
  res.json({ version: 1 });
});

const v2Router = express.Router();
v2Router.get('/users', (req, res) => {
  res.json({ version: 2 });
});

app.use('/api/v1', v1Router);
app.use('/api/v2', v2Router);
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Verify versioned endpoints
        assert ("/api/v1/users", HTTPMethod.GET) in paths
        assert ("/api/v2/users", HTTPMethod.GET) in paths


def test_rest_api_best_practices():
    """Test common REST API best practices patterns."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

// Collection endpoints
app.get('/articles', (req, res) => {
  res.json([]);
});

app.post('/articles', (req, res) => {
  res.status(201).json(req.body);
});

// Individual resource endpoints
app.get('/articles/:id', (req, res) => {
  res.json({ id: req.params.id });
});

app.patch('/articles/:id', (req, res) => {
  res.json({ id: req.params.id, ...req.body });
});

app.delete('/articles/:id', (req, res) => {
  res.status(204).send();
});
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Verify RESTful patterns
        assert ("/articles", HTTPMethod.GET) in paths
        assert ("/articles", HTTPMethod.POST) in paths
        assert ("/articles/{id}", HTTPMethod.GET) in paths
        assert ("/articles/{id}", HTTPMethod.PATCH) in paths
        assert ("/articles/{id}", HTTPMethod.DELETE) in paths


def test_complex_path_patterns():
    """Test various path pattern combinations."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

// Root path
app.get('/', (req, res) => {
  res.json({ message: 'API Root' });
});

// Simple path
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Path with single parameter
app.get('/products/:id', (req, res) => {
  res.json({ id: req.params.id });
});

// Path with multiple segments
app.get('/api/catalog/products', (req, res) => {
  res.json([]);
});

// Path ending with parameter
app.get('/categories/:category', (req, res) => {
  res.json({ category: req.params.category });
});
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Verify all path patterns are extracted
        assert ("/", HTTPMethod.GET) in paths
        assert ("/health", HTTPMethod.GET) in paths
        assert ("/products/{id}", HTTPMethod.GET) in paths
        assert ("/api/catalog/products", HTTPMethod.GET) in paths
        assert ("/categories/{category}", HTTPMethod.GET) in paths
