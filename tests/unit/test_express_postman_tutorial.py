"""
Test Express extractor against patterns from Postman's "How to Create a REST API with Node.js and Express" tutorial.

This validates the exact patterns taught in:
https://blog.postman.com/how-to-create-a-rest-api-with-node-js-and-express/
"""

import os
import tempfile
import pytest
from api_extractor.extractors.javascript.express import ExpressExtractor
from api_extractor.core.models import HTTPMethod


def test_basic_status_endpoint():
    """Test basic app.get() pattern from Step 3."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "app.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

app.use(express.json());

app.get('/status', (req, res) => {
  res.json({
    status: 'Running',
    timestamp: new Date().toISOString()
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}
        assert ("/status", HTTPMethod.GET) in paths


def test_authorization_routes_pattern():
    """Test router pattern from Step 6 - single file version."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Single file version (current limitation: cross-file router mounting not supported)
        app_file = os.path.join(tmpdir, "app.js")
        with open(app_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

const authRouter = express.Router();

authRouter.post('/signup', (req, res) => {
  res.status(201).json({ success: true });
});

authRouter.post('/login', (req, res) => {
  res.json({ success: true, token: 'abc123' });
});

app.use('/', authRouter);
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Routes mounted at '/' so paths are just the route paths
        assert ("/signup", HTTPMethod.POST) in paths
        assert ("/login", HTTPMethod.POST) in paths


def test_user_routes_with_middleware():
    """Test router with middleware pattern from Step 8 - single file version."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Single file version (current limitation: cross-file router mounting not supported)
        app_file = os.path.join(tmpdir, "app.js")
        with open(app_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

const userRouter = express.Router();

// Simulated middleware
const check = (req, res, next) => next();

userRouter.get('/', check, (req, res) => {
  res.json({ user: req.user });
});

userRouter.get('/all', check, (req, res) => {
  res.json({ users: [] });
});

app.use('/user', userRouter);
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Routes mounted at /user
        assert ("/user/", HTTPMethod.GET) in paths or ("/user", HTTPMethod.GET) in paths
        assert ("/user/all", HTTPMethod.GET) in paths


def test_complete_tutorial_structure():
    """Test the complete structure from the tutorial - single file version."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Single file version (current limitation: cross-file router mounting not supported)
        with open(os.path.join(tmpdir, "app.js"), "w") as f:
            f.write("""
const express = require('express');
const app = express();

app.use(express.json());

// Basic status endpoint
app.get('/status', (req, res) => {
  res.json({ status: 'Running' });
});

// Auth router
const authRouter = express.Router();
authRouter.post('/signup', (req, res) => {
  res.json({ success: true });
});
authRouter.post('/login', (req, res) => {
  res.json({ success: true, token: 'abc123' });
});

// User router
const userRouter = express.Router();
const check = (req, res, next) => next();
userRouter.get('/', check, (req, res) => {
  res.json({ user: req.user });
});
userRouter.get('/all', check, (req, res) => {
  res.json({ users: [] });
});

// Mount routers
app.use('/', authRouter);
app.use('/user', userRouter);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Should find all endpoints
        assert ("/status", HTTPMethod.GET) in paths
        assert ("/signup", HTTPMethod.POST) in paths
        assert ("/login", HTTPMethod.POST) in paths
        assert ("/user/", HTTPMethod.GET) in paths or ("/user", HTTPMethod.GET) in paths
        assert ("/user/all", HTTPMethod.GET) in paths

        # Should have at least 5 endpoints total
        assert len(result.endpoints) >= 5


def test_error_handler_middleware():
    """Test that error handler middleware doesn't get picked up as a route."""
    extractor = ExpressExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "app.js")
        with open(test_file, "w") as f:
            f.write("""
const express = require('express');
const app = express();

app.get('/api/data', (req, res) => {
  res.json({ data: [] });
});

// Error handler - not a route
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    error: 'Something went wrong'
  });
});
""")

        result = extractor.extract(tmpdir)
        assert result.success

        paths = {(ep.path, ep.method): ep for ep in result.endpoints}

        # Should only find the data endpoint, not the error handler
        assert ("/api/data", HTTPMethod.GET) in paths
        assert len(result.endpoints) == 1
