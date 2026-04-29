"""Tests for Express schema extraction (TypeScript and JavaScript support)."""

import os
import pytest
import tempfile
from pathlib import Path
from api_extractor.extractors.javascript.express import ExpressExtractor
from api_extractor.core.models import HTTPMethod


def test_express_typescript_interfaces():
    """Test TypeScript interface extraction."""
    code = """
import express, { Request, Response } from 'express';

interface User {
  id: string;
  name: string;
  email: string;
}

interface CreateUserDto {
  name: string;
  email: string;
}

type TypedRequest<B = void> = Request<{}, any, B>;
type TypedResponse<T> = Response;

const router = express.Router();

router.post(
  '/users',
  async (
    req: TypedRequest<CreateUserDto>,
    res: TypedResponse<User>
  ) => {
    const user: User = { id: '1', name: req.body.name, email: req.body.email };
    res.json(user);
  }
);

export default router;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = ExpressExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) >= 1

        # Find POST /users endpoint
        endpoint = None
        for ep in result.endpoints:
            if ep.path == "/users" and ep.method == HTTPMethod.POST:
                endpoint = ep
                break

        assert endpoint is not None, "POST /users endpoint not found"

        # Verify request body schema (CreateUserDto)
        assert endpoint.request_body is not None
        assert endpoint.request_body.type == "object"
        assert "name" in endpoint.request_body.properties
        assert "email" in endpoint.request_body.properties
        assert "name" in endpoint.request_body.required
        assert "email" in endpoint.request_body.required


def test_express_typescript_query_params():
    """Test TypeScript typed query parameters."""
    code = """
import express, { Request, Response } from 'express';

interface User {
  id: string;
  name: string;
}

type TypedRequest<B = void, P = {}, Q = {}> = Request<P, any, B, Q>;
type TypedResponse<T> = Response;

const router = express.Router();

router.get(
  '/users',
  async (
    req: TypedRequest<void, {}, { page?: string; limit?: string }>,
    res: TypedResponse<User[]>
  ) => {
    const page = Number(req.query.page ?? 1);
    const limit = Number(req.query.limit ?? 10);
    res.json([]);
  }
);

export default router;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = ExpressExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) >= 1

        endpoint = result.endpoints[0]

        # Verify query parameters
        query_params = [p for p in endpoint.parameters if p.location.value == "query"]
        assert len(query_params) >= 2

        param_names = {p.name for p in query_params}
        assert "page" in param_names
        assert "limit" in param_names

        # All should be optional
        for param in query_params:
            assert not param.required


def test_express_typescript_response_array():
    """Test TypeScript array response type."""
    code = """
import express, { Request, Response } from 'express';

interface Product {
  id: string;
  name: string;
  price: number;
}

type TypedResponse<T> = Response;

const router = express.Router();

router.get(
  '/products',
  async (req: Request, res: TypedResponse<Product[]>) => {
    res.json([]);
  }
);

export default router;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = ExpressExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]

        # Verify response is array
        assert len(endpoint.responses) > 0
        response_schema = endpoint.responses[0].response_schema
        assert response_schema is not None
        assert response_schema.type == "array"
        assert response_schema.items is not None


def test_express_typescript_type_mapping():
    """Test TypeScript type to OpenAPI type mapping."""
    code = """
import express, { Request, Response } from 'express';

interface TestDto {
  str_field: string;
  num_field: number;
  bool_field: boolean;
  arr_field: string[];
}

type TypedRequest<B = void> = Request<{}, any, B>;

const router = express.Router();

router.post(
  '/test',
  async (req: TypedRequest<TestDto>, res: Response) => {
    res.json(req.body);
  }
);

export default router;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = ExpressExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert endpoint.request_body is not None

        props = endpoint.request_body.properties
        assert props["str_field"]["type"] == "string"
        assert props["num_field"]["type"] == "number"
        assert props["bool_field"]["type"] == "boolean"
        assert props["arr_field"]["type"] == "array"


def test_express_javascript_query_params():
    """Test JavaScript minimal extraction - query parameters."""
    code = """
const express = require('express');
const router = express.Router();

router.get('/items', (req, res) => {
  const skip = req.query.skip || 0;
  const limit = req.query.limit || 10;
  res.json({ skip, limit });
});

module.exports = router;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.js")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = ExpressExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]

        # Verify query parameters extracted
        query_params = [p for p in endpoint.parameters if p.location.value == "query"]
        assert len(query_params) >= 2

        param_names = {p.name for p in query_params}
        assert "skip" in param_names
        assert "limit" in param_names


def test_express_javascript_no_types():
    """Test JavaScript endpoints without types still work."""
    fixture_path = str(Path(__file__).parent.parent / "fixtures" / "minimal" / "javascript" / "sample_express.js")

    extractor = ExpressExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success
    assert len(result.endpoints) > 0

    # Find GET /items endpoint (has req.query access)
    endpoint = None
    for ep in result.endpoints:
        if ep.path == "/items" and ep.method == HTTPMethod.GET:
            endpoint = ep
            break

    assert endpoint is not None, "GET /items endpoint not found"

    # Should have extracted query parameters
    query_params = [p for p in endpoint.parameters if p.location.value == "query"]
    assert len(query_params) >= 2


def test_express_typescript_optional_fields():
    """Test TypeScript interface with optional fields."""
    code = """
import express, { Request, Response } from 'express';

interface UpdateUserDto {
  name?: string;
  email?: string;
}

type TypedRequest<B = void> = Request<{}, any, B>;

const router = express.Router();

router.put(
  '/users/:id',
  async (req: TypedRequest<UpdateUserDto>, res: Response) => {
    res.json(req.body);
  }
);

export default router;
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.ts")
        with open(test_file, "w") as f:
            f.write(code)

        extractor = ExpressExtractor()
        result = extractor.extract(tmpdir)

        assert result.success
        assert len(result.endpoints) == 1

        endpoint = result.endpoints[0]
        assert endpoint.request_body is not None

        # All fields are optional
        assert len(endpoint.request_body.required) == 0
        assert "name" in endpoint.request_body.properties
        assert "email" in endpoint.request_body.properties
