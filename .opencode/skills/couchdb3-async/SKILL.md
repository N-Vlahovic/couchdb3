# couchdb3 Async Client — Implementation Reference

## Status
Step 1 (requests → httpx) is **complete and merged** (PR #32, v3.1.0).
Step 2 (async client) is **complete and merged** (PR #34, v3.2.0).

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
├── sync/                ← Base, Server, Database, Partition
├── aio/                 ← AsyncBase, AsyncServer, AsyncDatabase, AsyncPartition
├── document.py          ← shared (DictBase, Document, etc.)
├── exceptions.py        ← shared
├── utils.py             ← shared
└── view.py              ← shared
```

`utils.py`, `exceptions.py`, `document.py`, `view.py` — **shared, unchanged**.
`check_response` works identically on `httpx.Response` from both sync and async clients.

---

## Class hierarchy

```
AsyncBase (aio/async_base.py)
├── AsyncServer (aio/async_server.py)
└── AsyncDatabase (aio/async_database.py)
    └── AsyncPartition (aio/async_database.py)
```

Mirrors the sync hierarchy exactly.

---

## AsyncBase

### Key differences from sync Base

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
- `self.disable_ssl_verification` stored
- `_owns_session` flag

```python
import asyncio
import httpx

# ... in __init__ ...
self.session = httpx.AsyncClient(...)
self._auth_lock = asyncio.Lock()
```

### Cookie auth — double-checked locking

`_renew_auth_token()` is **async**, guarded by double-checked locking:

```python
async def _renew_auth_token(self) -> None:
    async with self._auth_lock:
        # Re-check inside the lock: another coroutine may have renewed already
        if self._is_auth_token_expired():
            await self._post(...)
```

---

## AsyncServer / AsyncDatabase / AsyncPartition

Mirror their sync counterparts exactly. All public methods are `async def`.

### `__getitem__` — not supported
`db = client["mydb"]` is **not available** on async classes.
Use `db = await client.get("mydb")` instead.

---

## `__init__.py` exports

```python
from .aio import AsyncServer as AsyncServer
from .aio import AsyncDatabase as AsyncDatabase, AsyncPartition as AsyncPartition
```

---

## Testing

Use `unittest.IsolatedAsyncioTestCase`:

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
`make test` picks up `IsolatedAsyncioTestCase` automatically.

