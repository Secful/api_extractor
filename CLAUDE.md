# CLAUDE.md — Python Project Guidelines

## Language & Runtime

- Python 3.11+ required
- Use `pyproject.toml` for project metadata and dependencies (no `setup.py`)
- Dependency management: `uv` preferred, `pip` acceptable

---

## Type Annotations

- All function signatures must be fully annotated — parameters and return types
- Use `from __future__ import annotations` for forward references
- Prefer `X | Y` union syntax over `Optional[X]` / `Union[X, Y]`
- Use `TypeAlias` for complex type aliases
- Use `TypedDict` for structured dicts, `dataclass` or `pydantic.BaseModel` for domain objects
- Never use `Any` unless interfacing with untyped third-party code — add a comment explaining why

```python
# good
def find_user(user_id: str) -> User | None: ...

# bad
def find_user(user_id, user=None): ...
```

---

## Code Style

- Formatter: `ruff format` (replaces black)
- Linter: `ruff check` — all rules enabled, exceptions documented in `pyproject.toml`
- Max line length: 100
- Imports: stdlib → third-party → internal, separated by blank lines, sorted by `ruff`
- No wildcard imports (`from module import *`)
- No mutable default arguments

```python
# bad
def append(item, lst=[]):
    lst.append(item)
    return lst

# good
def append(item: str, lst: list[str] | None = None) -> list[str]:
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

---

## Naming Conventions

| Construct | Convention | Example |
|---|---|---|
| Module | `snake_case` | `user_service.py` |
| Class | `PascalCase` | `UserService` |
| Function / method | `snake_case` | `get_user_by_id` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Private | leading `_` | `_internal_helper` |
| Type alias | `PascalCase` | `UserId = str` |

---

## Error Handling

- Define domain-specific exceptions in `exceptions.py`, inheriting from a base `AppError`
- Never silence exceptions with bare `except:` or `except Exception: pass`
- Use `logging` not `print` for errors — always include context
- Prefer returning `result | None` or a `Result` type over raising for expected failures
- Always re-raise with `raise ... from err` to preserve traceback chain

```python
# good
try:
    response = client.get(url)
except httpx.TimeoutException as err:
    raise ServiceUnavailableError(f"Timeout fetching {url}") from err
```

---

## Project Structure

```
src/
  mypackage/
    __init__.py
    models/          # domain models (dataclasses / pydantic)
    services/        # business logic
    repositories/    # data access layer
    api/             # HTTP layer (routes, schemas)
    exceptions.py    # domain exceptions
    config.py        # settings (pydantic-settings)
tests/
  unit/
  integration/
pyproject.toml
CLAUDE.md
```

- All source under `src/` layout
- No business logic in `api/` layer — thin controllers only
- `config.py` uses `pydantic-settings` — all config from env vars, never hardcoded

---

## Dependencies & I/O

- HTTP client: `httpx` (async-first), not `requests`
- Async framework: `asyncio` — prefer `async/await` throughout
- Database: use async drivers (`asyncpg`, `motor`, etc.)
- Never do blocking I/O in async context — use `asyncio.to_thread()` if unavoidable
- AWS SDK: `aioboto3` for async, `boto3` for sync scripts

---

## Testing

- Framework: `pytest` + `pytest-asyncio`
- Coverage target: 80% minimum, 100% on `services/`
- Use `pytest.fixture` for shared state — no global test state
- Mock external I/O with `pytest-mock` / `respx` (for httpx)
- Test file mirrors source: `src/mypackage/services/user.py` → `tests/unit/services/test_user.py`
- Test naming: `test_<function>_<scenario>_<expected>`

```python
async def test_get_user_not_found_returns_none():
    ...

async def test_create_user_duplicate_email_raises_conflict():
    ...
```

---

## Documentation

- Docstrings on all public functions, classes, and modules
- Style: Google format
- Include `Args`, `Returns`, `Raises` sections where non-obvious
- No docstrings on private helpers unless complex

```python
def normalize_path(path: str, base_url: str) -> str:
    """Resolve a relative API path against a base URL.

    Args:
        path: Relative path, e.g. '/users/:id'.
        base_url: Base URL including scheme and host.

    Returns:
        Absolute URL string.

    Raises:
        ValueError: If path is not a valid relative path.
    """
```

---

## Security

- Never log secrets, tokens, or PII
- Never hardcode credentials — use env vars via `config.py`
- Validate and sanitize all external input at the API boundary
- Use `secrets` module for token generation, not `random`

---

## Claude-Specific Instructions

- When adding a new module, follow the `src/` layout and register it in `__init__.py` if public
- When fixing a bug, add a regression test
- When touching async code, verify no blocking calls exist in the call chain
- Run `ruff check` and `ruff format` before considering any task complete
- Prefer editing existing abstractions over adding new ones