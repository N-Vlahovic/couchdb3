---
name: couchdb3-refactor
description: Use when working on the couchdb3 HTTP layer, sync client, or core base classes: base.py, server.py, database.py, utils.py. Documents the completed requests→httpx migration (Step 1, merged PR #32, v3.1.0). For the async client implementation see the couchdb3-async skill.
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

## Step 1 — requests → httpx (COMPLETE — PR #32, v3.1.0)

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

### Files changed

| File | What changed |
|---|---|
| `src/couchdb3/utils.py` | `requests`→`httpx`; `urllib3`→stdlib `urlparse`; `build_url` returns `str`; `check_response` catches `httpx` exceptions |
| `src/couchdb3/base.py` | `requests.Session`→`httpx.Client`; `HTTPBasicAuth`→`httpx.BasicAuth`; `verify`/`headers` at Client constructor; `_owns_session` flag; `cookies.jar` for token expiry |
| `src/couchdb3/server.py` | type hints updated; `httpx.RequestError`; reads `self.disable_ssl_verification` |
| `src/couchdb3/database.py` | same as server.py; `content=` instead of `data=` in `put_attachment` |
| `tests/credentials.py` | `httpx.get`; `httpx.ConnectError` |
| `tests/test_utils.py` | removed `.url` call — `build_url` now returns `str` |
| `pyproject.toml` | `requests` → `httpx>=0.27,<1.0`; dev tools moved to `[project.optional-dependencies] dev` |
| `setup.py` | `install_requires` → `["httpx>=0.27,<1.0"]` |
| `scripts/build.sh`, `deploy.sh`, `deploy-test.sh` | removed `uv add` calls; safe `dist` folder check; `uv run python3 -m build/twine` |

### Key behavioural differences

1. **`verify` is immutable post-construction in httpx.** `Base.__init__` stores
   `self.disable_ssl_verification` so child objects can read it without touching
   `session.verify` (which does not exist on `httpx.Client`).

2. **`httpx.Client.cookies` iterates `(name, value)` string pairs**, not cookie objects.
   Use `client.cookies.jar` to get `http.cookiejar.Cookie` objects with `.name`/`.expires`.
   This is done in `Base._is_auth_token_expired`.

3. **Session ownership.** `httpx.Client` raises `RuntimeError` if used after `.close()`.
   The `_owns_session` flag on `Base` ensures only the creating object closes the client.

4. **`put_attachment` uses `content=` not `data=`.** httpx 0.27+ deprecates `data=`
   for raw bytes.

---

## Step 2 — Async client

See `.opencode/skills/couchdb3-async/SKILL.md` for the full async implementation reference.

---

## Testing

```bash
make test
# Requires: COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB0_URL in .env or environment
# Docker CouchDB must be running

# Run a single test file:
uv run python3 -m unittest tests.test_server
```

**Test isolation note:** `tests/test_server.py` uses hardcoded `TEST_DB_NAME = "test-db"`.
If a prior run crashed before cleanup, delete it manually before re-running.

---

## Code conventions

- **Docstrings:** numpydoc format
- **Type annotations:** use modern built-in generics (`dict`, `list`, `tuple`, `set`) — ruff-enforced
- **`from __future__ import annotations`** at top of files where forward references are needed
- **`__all__`:** defined in every public module
