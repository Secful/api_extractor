# API Extractor Test Suite

This directory contains the test suite for the API Extractor project, organized into minimal fixtures for fast unit tests and real-world fixtures for comprehensive integration testing.

## Test Structure

```
tests/
├── fixtures/
│   ├── minimal/          # Minimal single-file examples for unit tests
│   │   ├── python/       # Python framework fixtures (Flask, FastAPI, Django)
│   │   └── javascript/   # JavaScript/TypeScript fixtures (Express, Fastify, NestJS)
│   └── real-world/       # Real-world applications as git submodules
│       ├── fastify-demo/
│       ├── fastapi-fullstack/
│       ├── django-rest-tutorial/
│       ├── flask-realworld/
│       ├── express-examples/
│       └── nestjs-realworld/
├── unit/                 # Fast unit tests using minimal fixtures
├── integration/          # Integration tests using real-world fixtures
└── README.md            # This file
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)

Fast, focused tests that verify individual extractors work correctly with minimal code examples.

**Characteristics:**
- Fast execution (< 1 second)
- Single-file fixtures
- Test specific extraction patterns
- No external dependencies

**Examples:**
- `test_fastify_extractor.py` - Tests Fastify route extraction
- `test_fastapi_extractor.py` - Tests FastAPI route extraction
- `test_django_extractor.py` - Tests Django REST Framework extraction
- `test_flask_extractor.py` - Tests Flask route extraction
- `test_express_extractor.py` - Tests Express.js route extraction
- `test_nestjs_extractor.py` - Tests NestJS controller extraction

**Run unit tests only:**
```bash
pytest tests/unit/
```

### 2. Integration Tests (`tests/integration/`)

Comprehensive tests that verify extractors work with real-world, production-quality codebases.

**Characteristics:**
- Test against actual GitHub repositories
- Verify complex project structures
- Test multi-file applications
- Validate production patterns

**Examples:**
- `test_realworld_fastify.py` - Tests against official Fastify demo (14+ endpoints)
- `test_realworld_fastapi.py` - Tests against FastAPI fullstack template (23+ endpoints)
- `test_full_pipeline.py` - End-to-end pipeline tests

**Run integration tests only:**
```bash
pytest tests/integration/
```

## Fixtures

### Minimal Fixtures (`tests/fixtures/minimal/`)

Simple, single-file examples created specifically for testing. Each fixture is a minimal but complete example of a framework's API patterns.

**Benefits:**
- Fast to parse and test
- Clear, focused examples
- No external dependencies
- Easy to understand and modify

**When to use:**
- Testing specific extraction patterns
- Verifying edge cases
- Quick feedback during development

### Real-World Fixtures (`tests/fixtures/real-world/`)

Production-quality applications from GitHub, added as git submodules. See [fixtures/real-world/README.md](fixtures/real-world/README.md) for detailed documentation.

**Benefits:**
- Test against actual production code
- Verify complex patterns and structures
- Catch real-world edge cases
- Ensure compatibility with popular projects

**When to use:**
- Verifying extractor robustness
- Testing against production patterns
- Validating multi-file projects
- Integration testing

## Running Tests

### All Tests

```bash
# Run all tests with coverage
pytest

# Run all tests with verbose output
pytest -v

# Run all tests with coverage report
pytest --cov=api_extractor --cov-report=html
```

### Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific framework tests
pytest tests/unit/test_fastify_extractor.py -v
pytest tests/integration/test_realworld_fastify.py -v
```

### Specific Tests

```bash
# Run a specific test function
pytest tests/unit/test_fastify_extractor.py::test_fastify_extractor -v

# Run tests matching a pattern
pytest -k "fastify" -v
```

### With Coverage

```bash
# Terminal coverage report
pytest --cov=api_extractor --cov-report=term-missing

# HTML coverage report
pytest --cov=api_extractor --cov-report=html
open htmlcov/index.html  # View in browser
```

## Test Requirements

### Unit Tests

No special setup required. Unit tests use minimal fixtures that are committed to the repository.

### Integration Tests

Integration tests require git submodules to be initialized:

```bash
# Initial setup
git submodule update --init --recursive

# Update submodules to latest
git submodule update --remote
```

## CI/CD Integration

For continuous integration, ensure submodules are initialized:

```yaml
# GitHub Actions example
- name: Checkout code with submodules
  uses: actions/checkout@v4
  with:
    submodules: recursive

- name: Run tests
  run: pytest --cov=api_extractor --cov-report=xml
```

## Writing New Tests

### Adding Unit Tests

1. Create or update a test file in `tests/unit/`
2. Use minimal fixtures from `tests/fixtures/minimal/`
3. Follow the naming convention: `test_<framework>_<feature>.py`
4. Test specific patterns and edge cases

**Example:**
```python
def test_fastify_route_extraction():
    """Test that Fastify routes are extracted correctly."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "minimal",
        "javascript",
        "sample_fastify.js"
    )

    extractor = FastifyExtractor()
    result = extractor.extract(os.path.dirname(fixture_path))

    assert result.success
    assert len(result.endpoints) > 0
```

### Adding Integration Tests

1. Ensure a real-world fixture exists (or add one as a git submodule)
2. Create a test file in `tests/integration/`
3. Name it `test_realworld_<framework>.py`
4. Test against the full application structure
5. Document expected endpoint counts

**Example:**
```python
def test_fastify_demo_extraction():
    """Test extraction from official Fastify demo."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fixtures",
        "real-world",
        "fastify-demo",
        "src",
        "routes"
    )

    extractor = FastifyExtractor()
    result = extractor.extract(fixture_path)

    assert result.success
    assert len(result.endpoints) >= 14  # Known endpoint count
```

### Adding New Fixtures

#### Minimal Fixtures

1. Create a new file in `tests/fixtures/minimal/python/` or `tests/fixtures/minimal/javascript/`
2. Write a minimal but complete example
3. Add corresponding tests in `tests/unit/`

#### Real-World Fixtures

See [fixtures/real-world/README.md](fixtures/real-world/README.md) for detailed instructions on adding new real-world fixtures.

## Test Coverage Goals

- **Overall**: > 80%
- **Core modules**: > 90%
- **Extractors**: > 85%
- **Critical paths**: 100%

Current coverage can be viewed by running:
```bash
pytest --cov=api_extractor --cov-report=term-missing
```

## Troubleshooting

### Tests fail after git clone

**Problem**: Integration tests fail with "file not found" errors.

**Solution**: Initialize git submodules:
```bash
git submodule update --init --recursive
```

### Tests collect from submodule directories

**Problem**: pytest tries to run tests from within submodules.

**Solution**: This is already configured in `pyproject.toml`. If you see this issue, check that `norecursedirs` includes the real-world fixtures:
```toml
[tool.pytest.ini_options]
norecursedirs = ["tests/fixtures/real-world/*", ".git", ".venv"]
```

### Slow test execution

**Problem**: Tests take too long to run during development.

**Solution**: Run only unit tests during development:
```bash
pytest tests/unit/  # Fast unit tests only
```

Run integration tests before committing:
```bash
pytest tests/integration/  # Comprehensive tests
```

## Test Naming Conventions

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`
- Fixtures: `@pytest.fixture` decorated functions

## Maintenance

- **Weekly**: Review test failures and flaky tests
- **Monthly**: Update submodule versions
- **Quarterly**: Review and update test coverage goals
- **On breaking changes**: Update both unit and integration tests

## Contributing

When contributing new extractors or features:

1. Add unit tests with minimal fixtures
2. Add integration tests with real-world fixtures (if applicable)
3. Ensure tests pass: `pytest`
4. Ensure coverage meets goals: `pytest --cov=api_extractor`
5. Update this README if adding new test categories or patterns
