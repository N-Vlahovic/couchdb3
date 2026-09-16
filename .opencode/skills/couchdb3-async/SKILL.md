# couchdb3 Async Client — Implementation Reference

## Status
Step 1 (requests → httpx) is **complete and merged** (PR #32, v3.1.0).
Step 2 (async client) is **complete and merged** (PR #34, v3.2.0).
v3.3.0–v3.4.1 additions are **complete and merged** — see changelog below.

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

Test files:
```
tests/
├── test_async_server.py
└── test_async_database.py
```
`make test` picks up `IsolatedAsyncioTestCase` automatically.
**Current test count: 152 tests, 2 skipped** (as of v3.4.2).

---

## Known issues / open work

### Blocking file I/O in `AsyncDatabase.put_attachment` (fixed in v3.4.3, streamed in v3.4.x)

**File:** `aio/async_database.py`

When `path=` is passed to `put_attachment`, the file is streamed to CouchDB in chunks without
ever loading the full contents into memory. A `_stream_file_content` async generator yields
64 KiB chunks, offloading each `read` to a worker thread via `asyncio.to_thread`. `Content-Length`
is set explicitly from `os.fstat(file.fileno()).st_size` so CouchDB is not sent
`Transfer-Encoding: chunked` (which it does not support on the request side):

```python
if path:
    with open(path, "rb") as file:
        content_length = os.fstat(file.fileno()).st_size
        response = await self._put(
            ...,
            content=_stream_file_content(file),
            headers={"content-type": content_type, "content-length": str(content_length)},
        )
else:
    response = await self._put(..., content=content, headers={"content-type": content_type})
```

`httpx.AsyncClient` rejects a plain (sync) file object passed as `content=`, so the async path
cannot simply pass the open handle the way the sync client does. The `_stream_file_content`
async generator bridges the gap.

The previous `asyncio.to_thread(_read_bytes, path)` whole-file read was removed along with the
module-level `_read_bytes` helper.

---

## Changelog

### v3.4.4 (PR #47)
- `AsyncDatabase.put_attachment()` (and `AsyncPartition.put_attachment()`) now stream the file to
  CouchDB in chunks instead of reading it fully into memory. A `_stream_file_content` async
  generator yields 64 KiB chunks, offloading each `read` via `asyncio.to_thread`, with an explicit
  `Content-Length` from `os.fstat(file.fileno()).st_size`.

### v3.4.3 (PR #45)
- `AsyncDatabase.put_attachment()` no longer blocks the event loop when `path=` is supplied: the
  file read is offloaded via `asyncio.to_thread`.  `AsyncPartition.put_attachment()` inherits the fix.

### v3.3.0 (PR #37)
Added to `AsyncServer` (sync + async):
- `membership()`, `cluster_setup()`, `setup_cluster()`
- `node_config()`, `set_node_config()`, `delete_node_config()`, `reload_node_config()`
- `node_stats()`, `node_system()`

Added to `AsyncDatabase` (sync + async):
- `changes()` — polling / longpoll; `feed=continuous|eventsource` raises `ValueError`.

### v3.3.1 (PR #38, issue #39)
- `AsyncDatabase.server` and `AsyncPartition.database` read-only back-reference properties to anchor
  parent lifetime and prevent `RuntimeError: Cannot send a request, as the client has been closed.`

### v3.4.0 (PR #40)
**Bug fixes:**
- `AsyncDatabase.put_design()` — `options = (options or {}).update(...)` always set options to `None`;
  fixed to `{**(options or {}), "partitioned": partitioned}`.
- `AsyncServer.replicate()` — was posting to `_replicator` DB; now posts to `/_replicate`.
  Body: dropped invalid `_id` field, mapped `filter_func` → `filter` key. `replication_id` param
  kept but deprecated (silently ignored).
- `AsyncBase._is_auth_token_expired()` — now handles `None` `.expires` (session cookie)
  without raising `TypeError`.
- `AsyncPartition.add_partition_to_str()` — guard tightened to `startswith(f"{partition_id}:")`
  to avoid false matches on IDs that share a prefix.
- `AsyncPartition.bulk_get()` — was calling `add_partition_to_doc` (looks for `_id` key only);
  now calls `add_partition_to_bulk_get_doc` which handles both `id` and `_id` keys.

**New API:**
- `AsyncServer.has_db(name) -> bool` — async equivalent of sync `name in server`
  (Python disallows async `__contains__`).
- `AsyncDatabase.delete_index(ddoc, name, index_type="json") -> bool`
  — `DELETE /{db}/_index/{ddoc}/{type}/{name}`; strips a `_design/` prefix automatically.
- `AsyncDatabase.design_docs(...) -> ViewResult`
  — `GET /{db}/_design_docs` with explicit signature.

**New helpers on `AsyncPartition`:**
- `add_partition_to_bulk_get_doc(doc)` — prefixes the `id` (or `_id`) key; public method.

### v3.4.1 (PR #41)
- Package metadata only: corrected author email in `pyproject.toml` / `setup.py`.

### v3.4.2 (PR #43)
- `AsyncServer.replicate()` (and sync `Server.replicate()`) now emits `DeprecationWarning` when
  `replication_id` is passed — previously silently ignored since v3.4.0 switched to `/_replicate`.
- 2 new tests: `test_replicate_deprecation_warning` (sync + async); test count: 152.

