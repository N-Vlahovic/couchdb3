---
name: couchdb3-refactor
description: Use when working on the couchdb3 refactoring: httpx migration, async client implementation, or any changes to src/couchdb3/base.py, server.py, database.py, utils.py. Covers the two-phase plan (Step 1: requests→httpx done; Step 2: async client planned).
---

# couchdb3 Refactor Reference

## Project Overview

`couchdb3` is a synchronous Python wrapper around the CouchDB 3.x HTTP API.

**Class hierarchy:**
```
Base (base.py)
├── Server (server.py)       — server-level operations (all_dbs, create, delete, replicate, up)
└── Database (database.py)   — document/view/index operations
    └── Partition (database.py) — partitioned-database wrapper, delegates to Database
```

**Request flow:**
```
Server/Database method
  → Base._get/_post/_put/_delete/_head
  → Base._request                         # single HTTP dispatcher
  → httpx.Client.request                  # one shared client per Server instance
  → utils.check_response                  # maps status codes → CouchDBError subclasses
```

**Session sharing:** `Server.get()` and `Database.get_partition()` pass `session=self.session` to child
objects. The child sets `_owns_session = False` and therefore never closes the shared client.
Only the owning object (the one that created the `httpx.Client`) closes it in `__del__`/`__exit__`.

---

## Step 1 — requests → httpx (COMPLETED)

### Symbol mapping

| `requests` | `httpx` | Notes |
|---|---|---|
| `requests.Session()` | `httpx.Client()` | |
| `requests.auth.HTTPBasicAuth(u, p)` | `httpx.BasicAuth(u, p)` | |
| `session.verify = bool` | `httpx.Client(verify=bool)` | **verify is constructor-only in httpx** |
| `session.headers.update(h)` | `httpx.Client(headers=h)` | **headers are constructor-only in httpx** |
| `session.request(method, url, json=, timeout=)` | `client.request(...)` | identical signature |
| `session.cookies` (iterates strings) | `client.cookies.jar` (iterates `http.cookiejar.Cookie`) | **must use `.jar` for `.name`/`.expires`** |
| `response.raise_for_status()` | `response.raise_for_status()` | raises `httpx.HTTPStatusError`, not `requests.exceptions.HTTPError` |
| `response.json()/.content/.headers/.status_code/.text` | identical | |
| `requests.exceptions.ConnectionError` | `httpx.ConnectError` | |
| `requests.exceptions.HTTPError` | `httpx.HTTPStatusError` | |
| `requests.exceptions.RequestException` | `httpx.RequestError` | broad base class |
| `requests.Response` (type hint) | `httpx.Response` | |
| `requests.get(url, timeout=)` | `httpx.get(url, timeout=)` | top-level convenience fn |

### Files changed in Step 1

| File | What changed |
|---|---|
| `src/couchdb3/utils.py` | `requests`→`httpx`; `urllib3`→stdlib `urlparse`; `build_url` returns `str`; `check_response` catches `httpx` exceptions |
| `src/couchdb3/base.py` | `requests.Session`→`httpx.Client`; `HTTPBasicAuth`→`httpx.BasicAuth`; `verify`/`headers` moved to Client constructor; `_owns_session` flag prevents double-close; `cookies.jar` for token expiry; `_request` drops `.url` call |
| `src/couchdb3/server.py` | type hints updated; `requests.exceptions.RequestException`→`httpx.RequestError`; `session.verify`→`self.disable_ssl_verification` |
| `src/couchdb3/database.py` | same as server.py; `data=`→`content=` in `put_attachment` (httpx deprecation) |
| `tests/credentials.py` | `requests.get`→`httpx.get`; `requests.exceptions.ConnectionError`→`httpx.ConnectError` |
| `tests/test_utils.py` | removed `.url` call on `build_url` result (now returns `str`) |
| `pyproject.toml` | `requests (>=2.32.4,<3.0.0)` → `httpx>=0.27,<1.0` |
| `setup.py` | `install_requires=["requests"]` → `["httpx>=0.27,<1.0"]` |

### Known behavioural differences / risk points

1. **`verify` is immutable post-construction in httpx.** `Base.__init__` stores
   `self.disable_ssl_verification` so child objects can read it without touching
   `session.verify` (which does not exist on `httpx.Client`).

2. **`httpx.Client.cookies` iterates `(name, value)` string pairs**, not cookie objects.
   Use `client.cookies.jar` to get `http.cookiejar.Cookie` objects with `.name`/`.expires`.
   This is done in `Base._is_auth_token_expired`.

3. **Session ownership.** `httpx.Client` raises `RuntimeError: Cannot send a request,
   as the client has been closed` if used after `.close()`. The `_owns_session` flag
   on `Base` ensures only the creating object closes the client.

4. **`put_attachment` uses `content=` not `data=`.** httpx 0.27+ deprecates `data=`
   for raw bytes; use `content=` instead.

5. **`pyproject.toml` has misplaced dev dependencies** (`build`, `pdoc3`, `pdoc`,
   `setuptools`, `twine`) listed under `[project] dependencies` instead of a dev
   extras group. These are build/publish tools, not runtime deps. Fix separately.

---

## Step 2 — Async client (PLANNED, not yet implemented)

### Target API

```python
from couchdb3 import AsyncServer, AsyncDatabase, AsyncPartition

async with AsyncServer("http://user:pass@127.0.0.1:5984") as client:
    db = await client.get("mydb")
    doc = await db.get("mydoc-id")
```

### Architecture

- New files: `src/couchdb3/async_base.py`, `async_server.py`, `async_database.py`
- `AsyncBase` mirrors `Base` but uses `httpx.AsyncClient` and `async def` methods
- `__aenter__` / `__aexit__` / `aclose()` on `AsyncBase` (no `__del__` — not supported for async)
- `_owns_session` pattern carries over to `AsyncBase`
- All shared logic (URL building, response checking, constants, validators) stays in `utils.py` —
  `check_response` works on both `httpx.Response` and `httpx.AsyncClient` responses identically
- Exports added to `src/couchdb3/__init__.py`:
  ```python
  from .async_server import AsyncServer as AsyncServer
  from .async_database import AsyncDatabase as AsyncDatabase, AsyncPartition as AsyncPartition
  ```

### httpx.AsyncClient vs httpx.Client differences

| Sync | Async |
|---|---|
| `httpx.Client(...)` | `httpx.AsyncClient(...)` |
| `client.request(...)` | `await client.request(...)` |
| `client.close()` | `await client.aclose()` |
| `with client:` | `async with client:` |
| `__enter__`/`__exit__` | `__aenter__`/`__aexit__` |

### Cookie auth in async context

`AsyncClient.cookies.jar` is the same `http.cookiejar.CookieJar` — the same
`.jar` access pattern for `_is_auth_token_expired` applies unchanged.

---

## Testing

```bash
make test
# Requires: COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB_URL (or COUCHDB0_URL) in .env or env
# Credentials in project .env: COUCHDB_USER=niko, COUCHDB_PASSWORD=superman, COUCHDB0_URL=127.0.0.1:59840
# Docker CouchDB must be running before test run

# Run a single test file:
uv run python3 -m unittest tests.test_server
```

**Test isolation note:** `tests/test_server.py` uses hardcoded `TEST_DB_NAME = "test-db"`.
If a prior run crashed before cleanup, delete it manually:
```python
from couchdb3 import Server
s = Server("http://niko:superman@127.0.0.1:59840")
if "test-db" in s: s.delete("test-db")
```

---

## Code conventions

- **Docstrings:** numpydoc format
- **Type annotations:** always use them; `from __future__ import annotations` at top of files where needed
- **Typing imports:** use `from typing import Dict, List, Optional, Tuple, Union` (not `dict`, `list` etc. — Python 3.11 compat)
- **`__all__`:** every public module defines it
