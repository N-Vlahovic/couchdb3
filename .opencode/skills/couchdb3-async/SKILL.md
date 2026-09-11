---
name: couchdb3-async
description: Use when implementing or modifying the async couchdb3 client: AsyncServer, AsyncDatabase, AsyncPartition, async_base.py, async_server.py, async_database.py. Covers the full design, asyncio.Lock auth renewal, _owns_session ownership pattern, and test strategy using IsolatedAsyncioTestCase.
---

# couchdb3 Async Client — Implementation Reference

## Status
Step 1 (requests → httpx) is **complete and merged** (PR #32, v3.1.0).
Step 2 (async client) is **in progress**.

---

## Target public API

```python
from couchdb3 import AsyncServer, AsyncDatabase, AsyncPartition

# Context manager (recommended)
async with AsyncServer("http://user:pass@127.0.0.1:5984") as client:
    db: AsyncDatabase = await client.get("mydb")
    doc = await db.get("mydoc-id")
    await db.save({"_id": "new-doc", "type": "example"})

# Manual lifecycle
client = AsyncServer("http://user:pass@127.0.0.1:5984")
db = await client.get("mydb")
await client.aclose()
```

---

## File layout

```
src/couchdb3/
├── base.py              ← sync (unchanged)
├── server.py            ← sync (unchanged)
├── database.py          ← sync (unchanged)
├── async_base.py        ← AsyncBase
├── async_server.py      ← AsyncServer(AsyncBase)
└── async_database.py    ← AsyncDatabase(AsyncBase), AsyncPartition(AsyncDatabase)
```

`utils.py`, `exceptions.py`, `document.py`, `view.py` — **shared, unchanged**.
`check_response` works identically on `httpx.Response` from both sync and async clients.

---

## Class hierarchy

```
AsyncBase (async_base.py)
├── AsyncServer (async_server.py)
└── AsyncDatabase (async_database.py)
    └── AsyncPartition (async_database.py)
```

Mirrors the sync hierarchy exactly (Option A — parallel trees, no shared base class between sync and async).

---

## AsyncBase

### Key differences from Base

| Sync (`Base`) | Async (`AsyncBase`) |
|---|---|
| `httpx.Client` | `httpx.AsyncClient` |
| `__enter__` / `__exit__` | `__aenter__` / `__aexit__` |
| `session.close()` | `await session.aclose()` |
| `__del__` closes session | No `__del__` — cannot `await` in `__del__` |
| `_request(...)` | `async def _request(...)` |
| `_get/_post/_put/_delete/_head` | all `async def` |
| `_renew_auth_token()` | `async def _renew_auth_token()` guarded by `asyncio.Lock` |

### Constructor

Identical signature to `Base.__init__`. Additions:
- `httpx.AsyncClient` instead of `httpx.Client`
- `self._auth_lock = asyncio.Lock()` for cookie token renewal
- `self.disable_ssl_verification` stored (same as sync — no `session.verify` attribute on httpx clients)
- `_owns_session` flag (identical pattern to sync)

```python
import asyncio
import httpx

if session is not None:
    self.session = session
    self._owns_session = False
else:
    self.session = httpx.AsyncClient(
        verify=disable_ssl_verification is False,
        headers={"Accept": "application/json", "Content-type": "application/json"},
    )
    self._owns_session = True
self._auth_lock = asyncio.Lock()
```

### Lifecycle — no `__del__`

`__del__` is not implemented — `await` is not valid inside it.
Users must use `async with` or call `await obj.aclose()` explicitly.

```python
async def __aenter__(self):
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    await self.aclose()

async def aclose(self) -> None:
    if self._owns_session:
        await self.session.aclose()
```

### `_owns_session` — identical to sync

Child objects (`AsyncDatabase`, `AsyncPartition`) receive a session from their
parent (`AsyncServer.get()`, `AsyncDatabase.get_partition()`) and set
`_owns_session = False`. They never call `aclose()`.

Only the object that created the `httpx.AsyncClient` owns and closes it.

### Cookie auth — double-checked locking with `asyncio.Lock`

`_is_auth_token_expired()` stays **synchronous** — it only reads a timestamp, no I/O:

```python
def _is_auth_token_expired(self) -> bool:
    try:
        return (
            next(
                _.expires
                for _ in self.session.cookies.jar
                if _.name == "AuthSession"
            )
            <= datetime.now(timezone.utc).timestamp()
        )
    except StopIteration:
        return True
```

`_renew_auth_token()` is **async**, guarded by double-checked locking:

```python
async def _renew_auth_token(self) -> None:
    async with self._auth_lock:
        # Re-check inside the lock: another coroutine may have renewed already
        # while this one was waiting to acquire the lock.
        if self._is_auth_token_expired():
            await self._post(
                resource="_session",
                body={"name": self._user, "password": self._password},
                auth_method="basic",
                root="",
            )
```

In `_request`, the outer check avoids acquiring the lock on every call (happy path has zero contention).
The inner check inside the lock handles the race window.

`asyncio.Lock` coordinates coroutines within the same event loop only — consistent
with `httpx.AsyncClient`'s own contract (not thread-safe by design).

### `_request` dispatcher

```python
async def _request(self, *, method, resource=None, body=None,
                   query_kwargs=None, auth_method=None, root=None,
                   timeout=None, **req_kwargs) -> httpx.Response:
    auth_method = auth_method or self.auth_method
    root = root if isinstance(root, str) else self.root
    path = ""
    if root:
        path += root
    if body and isinstance(body, dict):
        for k in utils.COUCH_DB_RESERVED_DOC_FIELDS:
            if k in body and body.get(k) is None:
                del body[k]
    if resource:
        path += f"/{resource}"
    if auth_method == "basic":
        req_kwargs.update({"auth": self._auth})
    elif auth_method == "cookie":
        if self._is_auth_token_expired():
            await self._renew_auth_token()
    response = await self.session.request(
        method=method,
        url=utils.build_url(
            scheme=self.scheme,
            host=self.host,
            path=path,
            port=self.port,
            **(query_kwargs or {}),
        ),
        json=body,
        timeout=timeout or self.timeout,
        **req_kwargs,
    )
    utils.check_response(response=response)
    return response
```

---

## AsyncServer

Mirrors `Server` exactly. All public methods are `async def`.

### `__getitem__` — not supported
Python does not allow `__getitem__` to be a coroutine.
`db = client["mydb"]` is **not available** on async classes.
Use `db = await client.get("mydb")` instead.

### `get()` returns `AsyncDatabase`

Passes `session=self.session` to `AsyncDatabase` — child sets `_owns_session=False`.

---

## AsyncDatabase / AsyncPartition

Mirrors `Database` and `Partition` exactly. All public methods are `async def`.

`get_partition()` returns `AsyncPartition`.

`__getitem__` — not supported (same as `AsyncServer`). Use `await db.get(docid)`.

---

## `__init__.py` exports

```python
from .async_server import AsyncServer as AsyncServer
from .async_database import AsyncDatabase as AsyncDatabase, AsyncPartition as AsyncPartition
```

---

## Testing

Use `unittest.IsolatedAsyncioTestCase` (stdlib, Python ≥ 3.8 — zero new dependencies):

```python
import unittest
from couchdb3 import AsyncServer

class TestAsyncServer(unittest.IsolatedAsyncioTestCase):
    async def test_up(self):
        async with AsyncServer("http://user:pass@127.0.0.1:59840") as client:
            self.assertTrue(await client.up())
```

New test files:
```
tests/
├── test_async_server.py
└── test_async_database.py
```

Mirror `test_server.py` and `test_database.py` respectively.
Credentials from `.env` via `tests/credentials.py` (unchanged).
`make test` picks up `IsolatedAsyncioTestCase` automatically via `unittest discover`.

---

## Implementation checklist

- [ ] `src/couchdb3/async_base.py` — `AsyncBase`
- [ ] `src/couchdb3/async_server.py` — `AsyncServer`
- [ ] `src/couchdb3/async_database.py` — `AsyncDatabase`, `AsyncPartition`
- [ ] `src/couchdb3/__init__.py` — export async classes
- [ ] `tests/test_async_server.py`
- [ ] `tests/test_async_database.py`
- [ ] `make test` — all tests pass (sync + async)
