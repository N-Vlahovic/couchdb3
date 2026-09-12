---
name: couchdb3-refactor
description: Use when working on the couchdb3 HTTP layer, sync client, or core base classes (sync/base.py, sync/server.py, sync/database.py, utils.py). Documents the completed requests→httpx migration and library restructuring (v3.2.0). For the async client implementation see the couchdb3-async skill.
---

# couchdb3 Refactor Reference

## Project Overview

`couchdb3` is a sync and async Python wrapper around the CouchDB 3.x HTTP API.

**Sync Class hierarchy:**
```
Base (sync/base.py)
├── Server (sync/server.py)       — server-level operations (all_dbs, create, delete, replicate, up)
└── Database (sync/database.py)   — document/view/index operations
    └── Partition (sync/database.py) — partitioned-database wrapper, delegates to Database
```

**Request flow (sync):**
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

**Lifetime anchoring (v3.3.1, issue #39):** Children also store a strong back-reference to their
parent — `Database._server` (set by `Server.get()`) and `Partition._database` (set by
`Database.get_partition()`). This prevents CPython's reference-counting GC from destroying the
session-owning parent while a child is still in use — which caused `RuntimeError: Cannot send a
request, as the client has been closed.` when a `Server` was constructed inline and immediately
chained (`Server(...)['db'].method()`). The back-references are exposed as read-only public
properties `Database.server` and `Partition.database` (returns `None` for standalone objects).

---

## Migration History (v3.2.0 complete)

### Symbol mapping (requests → httpx)

| `requests` | `httpx` | Notes |
|---|---|---|
| `requests.Session()` | `httpx.Client()` | |
| `requests.auth.HTTPBasicAuth(u, p)` | `httpx.BasicAuth(u, p)` | |
| `session.verify = bool` | `httpx.Client(verify=bool)` | **verify is constructor-only in httpx** |
| `session.headers.update(h)` | `httpx.Client(headers=h)` | **headers are constructor-only in httpx** |
| `session.request(method, url, json=, timeout=)` | `client.request(...)` | identical signature |
| `session.cookies` (iterates strings) | `client.cookies.jar` (iterates `http.cookiejar.Cookie`) | **must use `.jar` for `.name`/`.expires`** |
| `response.raise_for_status()` | `response.raise_for_status()` | raises `httpx.HTTPStatusError` |
| `response.json()/.content/.headers/.status_code/.text` | identical | |
| `requests.exceptions.ConnectionError` | `httpx.ConnectError` | |
| `requests.exceptions.HTTPError` | `httpx.HTTPStatusError` | |
| `requests.exceptions.RequestException` | `httpx.RequestError` | broad base class |

---

## Async client (v3.2.0 complete)

See `.opencode/skills/couchdb3-async/SKILL.md` for the full async implementation reference.

---

## Testing

```bash
make test
# Requires: COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB0_URL in .env
# Docker CouchDB must be running

# Run a single test file:
uv run python3 -m unittest tests.test_server
```

**Test isolation note:** `tests/test_server.py` uses hardcoded `TEST_DB_NAME = "test-db"`.
If a prior run crashed before cleanup, delete it manually:
```python
from couchdb3 import Server

s = Server("http://...:...")  # credentials
if "test-db" in s:
    s.delete("test-db")
```

---

## Code conventions

- **Docstrings:** numpydoc format
- **Type annotations:** use modern built-in generics (`dict`, `list`, `tuple`, `set`) — ruff-enforced
- **`from __future__ import annotations`** at top of files where forward references are needed
- **`__all__`:** defined in every public module
