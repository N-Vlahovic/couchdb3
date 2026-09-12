---
name: couchdb3-api-coverage
description: Use when implementing or tracking missing CouchDB API endpoint coverage in couchdb3. Documents which endpoints are implemented, which are pending, and the implementation patterns specific to each endpoint group (node-level paths, POST vs GET dispatch for _changes, etc.).
---

# couchdb3 API Coverage Tracker

## Status legend
- ✅ Implemented (sync + async)
- 🔲 Pending

---

## Batch 1 — Server & Database endpoints (v3.3.0)

| Endpoint | Method(s) | Class | Status |
|---|---|---|---|
| `GET /{db}/_changes` | `Database.changes()` | Database / AsyncDatabase | ✅ |
| `POST /{db}/_changes` | `Database.changes(doc_ids=...)` or `changes(selector=...)` | Database / AsyncDatabase | ✅ |
| `GET /_membership` | `Server.membership()` | Server / AsyncServer | ✅ |
| `GET /_cluster_setup` | `Server.cluster_setup()` | Server / AsyncServer | ✅ |
| `POST /_cluster_setup` | `Server.setup_cluster()` | Server / AsyncServer | ✅ |
| `GET /_node/{node}/_config` | `Server.node_config()` | Server / AsyncServer | ✅ |
| `GET /_node/{node}/_config/{section}` | `Server.node_config(section=...)` | Server / AsyncServer | ✅ |
| `GET /_node/{node}/_config/{section}/{key}` | `Server.node_config(section=..., key=...)` | Server / AsyncServer | ✅ |
| `PUT /_node/{node}/_config/{section}/{key}` | `Server.set_node_config()` | Server / AsyncServer | ✅ |
| `DELETE /_node/{node}/_config/{section}/{key}` | `Server.delete_node_config()` | Server / AsyncServer | ✅ |
| `POST /_node/{node}/_config/_reload` | `Server.reload_node_config()` | Server / AsyncServer | ✅ |
| `GET /_node/{node}/_stats` | `Server.node_stats()` | Server / AsyncServer | ✅ |
| `GET /_node/{node}/_system` | `Server.node_system()` | Server / AsyncServer | ✅ |

---

## Still pending (from TODO.md)

| Endpoint | Notes |
|---|---|
| `DELETE /{db}/_index/{ddoc}/json/{name}` | Delete a Mango index |
| `GET /{db}/_design_docs` | List design documents |
| `GET /{db}/_local_docs` / `GET\|PUT\|DELETE /{db}/_local/{docid}` | Local documents |
| `GET /_membership` | ✅ done in Batch 1 |
| `POST /_cluster_setup` / `GET /_cluster_setup` | ✅ done in Batch 1 |
| `GET /_node/{node}/_config`, `_stats`, `_system` | ✅ done in Batch 1 |
| `GET\|PUT /{db}/_revs_limit` | Revision limit management |
| `POST /{db}/_missing_revs` / `POST /{db}/_revs_diff` | Replication helpers |
| `POST /{db}/_view_cleanup` | View index cleanup |
| `__contains__` on `AsyncServer` | Ergonomic gap — Python disallows async `__contains__` but a helper like `await client.has_db(name)` could fill the gap |
| `GET /{db}/_changes` with `feed=continuous\|eventsource` | Streaming feeds — deferred; requires iterator/stream response handling |

---

## Implementation patterns

### `Database.changes()` — GET vs POST dispatch

```python
def changes(self, *, doc_ids=None, selector=None, feed=None, ...):
    # Validate feed
    if feed in ("continuous", "eventsource"):
        raise ValueError(
            f"feed={feed!r} is not supported; use feed='normal' or feed='longpoll'. "
            "Streaming feeds require changes_stream() (not yet implemented)."
        )
    query_kwargs = {
        "conflicts": conflicts, "descending": descending, "feed": feed,
        "filter": filter, "heartbeat": heartbeat, "include_docs": include_docs,
        ...
    }
    if doc_ids is not None:
        # POST with filter=_doc_ids
        query_kwargs["filter"] = "_doc_ids"
        return self._post(
            resource="_changes",
            body={"doc_ids": doc_ids},
            query_kwargs=query_kwargs,
        ).json()
    elif selector is not None:
        # POST with filter=_selector
        query_kwargs["filter"] = "_selector"
        return self._post(
            resource="_changes",
            body={"selector": selector},
            query_kwargs=query_kwargs,
        ).json()
    else:
        return self._get(resource="_changes", query_kwargs=query_kwargs).json()
```

### Node-level path construction

Node API methods live at `/_node/{node}/_config`, `/_stats`, `/_system`. These paths are **not** relative to a database root — they are server-level endpoints.

In `Base._request`, the `root` parameter allows overriding the URL path prefix. Pass `root=None` to use the server root directly:

```python
def node_config(self, node: str = "_local", section: str | None = None, key: str | None = None):
    resource = f"_node/{node}/_config"
    if section:
        resource = f"{resource}/{section}"
        if key:
            resource = f"{resource}/{key}"
    # Server subclass: self.root is "" so no root override needed
    return self._get(resource=resource).json()
```

For `Server` (which has `self.root = ""`), no special root override is needed — the resource path is correct as-is.

### `setup_cluster()` — POST /_cluster_setup (destructive)

**Do not run in integration tests against a production or shared CouchDB instance.**
Use `@unittest.skip("requires isolated CouchDB cluster — destructive")` on the test.

The action must be one of: `"enable_single_node"`, `"enable_cluster"`, `"add_node"`, `"finish_cluster"`.

### `node_config()` return type

- No `section`, no `key` → returns `dict` (full config tree)
- `section` only → returns `dict` (section dict)
- `section` + `key` → returns `str` or primitive (a single JSON value, e.g. `"info"` for log level)

Annotate as `dict | str` to cover all three cases.

---

## Test files

| File | What it covers |
|---|---|
| `tests/test_database.py` | `TestDatabase.test_changes_*` (sync) |
| `tests/test_async_database.py` | `TestAsyncDatabase.test_changes_*` (async) |
| `tests/test_server.py` | `TestClient.test_membership`, `test_cluster_setup`, `test_node_config_*`, `test_node_stats`, `test_node_system`, `test_reload_node_config` |
| `tests/test_async_server.py` | Same, all `async def` |

---

## Files modified in Batch 1

| File | Change |
|---|---|
| `src/couchdb3/sync/database.py` | Added `Database.changes()` |
| `src/couchdb3/aio/async_database.py` | Added `AsyncDatabase.changes()` |
| `src/couchdb3/sync/server.py` | Added `membership`, `cluster_setup`, `setup_cluster`, `node_config`, `set_node_config`, `delete_node_config`, `reload_node_config`, `node_stats`, `node_system` |
| `src/couchdb3/aio/async_server.py` | Same 9 methods, all `async def` |
| `tests/test_database.py` | `test_changes_normal`, `test_changes_since`, `test_changes_doc_ids`, `test_changes_include_docs` |
| `tests/test_async_database.py` | Same 4 tests, async |
| `tests/test_server.py` | `test_membership`, `test_cluster_setup`, `test_node_config_full`, `test_node_config_section`, `test_node_config_key`, `test_set_and_delete_node_config`, `test_reload_node_config`, `test_node_stats`, `test_node_system`, `test_setup_cluster_skipped` |
| `tests/test_async_server.py` | Same tests, async |
| `TODO.md` | Struck through completed items |
| `pyproject.toml` / `setup.py` | Version bumped to `3.3.0` |
