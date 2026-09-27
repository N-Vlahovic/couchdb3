---
name: couchdb3-roadmap
description: Use when planning, prioritising, or implementing the next couchdb3 feature. Contains the agreed feature backlog (Batches A-E), release versioning strategy, constraints, and the git branching workflow for this project.
---

# couchdb3 Feature Roadmap

Agreed in the Sep 2026 planning session. Update the Status table as batches are completed.

## Constraints / decisions

- Primary audience: app developers (not ops)
- Sync + async parity is mandatory — every method must land in both `sync/` and `aio/`
- CouchDB 3.5.x features added transparently — no version guards
- Releases are batched by theme — one minor version bump per batch
- Full-text search (Nouveau/Clouseau) is a low-priority placeholder — not actively scheduled
- Ops endpoints (`_scheduler`, `_db_updates`, `_prometheus`) are medium priority — Batch D

---

## Git workflow

**Default branch:** `master`

Before starting any feature:
1. `git fetch origin && git checkout master && git pull` — ensure master is up to date
2. Check for an existing branch for the same feature: `git branch -a | grep <feature-slug>`
   - If one exists, check it out and continue from there instead of creating a new branch
3. Create the feature branch off latest master:
   `git checkout -b nvlahovic/$(date +"%Y%m%d%H%M")-<feature-slug>`
   Example: `git checkout -b nvlahovic/202609271435-changes-stream`
4. Work, commit, push, open PR against `master`

---

## Batch A — Streaming (v3.5.0) ✅ done (PR #49)

`Database.changes_stream()` and `AsyncDatabase.changes_stream()`

**What:** Streaming continuous/eventsource changes feed.
**Why:** Largest remaining functional gap. `changes()` raises `ValueError` for `feed=continuous|eventsource`. README documents this as unsupported.
**Branch slug:** `changes-stream`

Shipped as context-managed generators (`@contextmanager` sync / `@asynccontextmanager` async)
over `httpx` streaming. `feed` is fixed to `continuous`; `eventsource` (EventSource wire
framing) was deliberately not surfaced — add a sibling method later if needed.

Key behavioural notes (documented in docstrings + README): `limit` caps rows but does not
close the connection on CouchDB 3.3.x (callers must `break`); the terminal `{"last_seq": ...}`
object from CouchDB's docs is absent on 3.3.x and version-dependent, so guard on `"id" in row`.

---

## Batch B — Missing p3 API endpoints (v3.6.0) ← next up

**Branch slug:** `p3-api-endpoints`

### 1. Local documents (highest-value p3 item)
- `Database.local_docs()` → `GET /{db}/_local_docs`
- `Database.get_local(docid)` → `GET /{db}/_local/{docid}`
- `Database.save_local(doc)` → `PUT /{db}/_local/{docid}`
- `Database.delete_local(docid, rev)` → `DELETE /{db}/_local/{docid}`
- All sync + async

### 2. Replication helpers
- `Database.missing_revs(data)` → `POST /{db}/_missing_revs`
- `Database.revs_diff(data)` → `POST /{db}/_revs_diff`
- Both sync + async

### 3. Revision limit
- `Database.revs_limit()` → `GET /{db}/_revs_limit` (returns `int`)
- `Database.set_revs_limit(limit)` → `PUT /{db}/_revs_limit` (returns `bool`)
- Both sync + async

### 4. View cleanup
- `Database.view_cleanup()` → `POST /{db}/_view_cleanup` (returns `bool`)
- Both sync + async

### 5. Dead code fix
- `Database.save()` — remove redundant double `batch = "ok" if batch else None` evaluation (~line 969 and inline in `query_kwargs`)

### Deliverables
- `sync/database.py`, `aio/async_database.py`
- Tests in `test_database.py` / `test_async_database.py`
- `TODO.md` — strike through p3 items
- Version bump to `3.6.0`

---

## Batch C — CouchDB 3.5 ergonomics (v3.7.0)

**Branch slug:** `couchdb35-ergonomics`

### 1. `Server.uuids(count, algorithm)` / `AsyncServer.uuids(...)`
- `GET /_uuids?count=N&algorithm=...`
- `algorithm` values: `sequential` (default), `random`, `utc_random`, `utc_id`, `uuid_v7` (new in CouchDB 3.5.1)
- Returns `list[str]`

### 2. `all_dbs(inclusive_end=...)` param
- Add `inclusive_end: bool | None` to `Server.all_dbs()` and `AsyncServer.all_dbs()`

### 3. `X-Couch-Request-ID` header passthrough
- Add `request_id: str | None` to `Base._request()` / `AsyncBase._request()`
- Forwarded as `X-Couch-Request-ID` when provided

### 4. Docstring notes for new built-in reducers
- Add a note to `put_design()` docstrings: CouchDB 3.5 supports `_top_N`, `_bottom_N`, `_first`, `_last` as built-in `reduce` values
- No code change required

### Deliverables
- `sync/server.py`, `aio/async_server.py`, `sync/base.py`, `aio/async_base.py`, `sync/database.py`, `aio/async_database.py`
- Tests in `test_server.py` / `test_async_server.py`
- Version bump to `3.7.0`

---

## Batch D — Ops / replication monitoring (v3.8.0)

**Branch slug:** `ops-endpoints`

### 1. `Server.db_updates()` / `AsyncServer.db_updates()`
- `GET /_db_updates` — params: `feed`, `timeout`, `heartbeat`, `since`

### 2. Replication scheduler
- `Server.scheduler_jobs()` → `GET /_scheduler/jobs`
- `Server.scheduler_docs()` → `GET /_scheduler/docs`
- Both sync + async

### 3. Prometheus metrics
- `Server.node_prometheus(node="_local")` → `GET /_node/{node}/_prometheus`
- Returns `str` (Prometheus exposition format, not JSON — use `response.text`)

### Deliverables
- `sync/server.py`, `aio/async_server.py`
- Tests in `test_server.py` / `test_async_server.py`
- Version bump to `3.8.0`

---

## Batch E — Full-text search, placeholder (unscheduled)

Nouveau / Clouseau `_search`, `_index`, `_nouveau_cleanup`. Not actively scheduled — requires a separate service. Start only when there is a clear demand signal.

---

## Status

| Batch | Theme | Target version | Status |
|---|---|---|---|
| A | `changes_stream()` streaming | 3.5.0 | ✅ Done (PR #49) |
| B | Local docs, replication helpers, revs_limit, view_cleanup, save() fix | 3.6.0 | **Next up** |
| C | CouchDB 3.5 compat + uuids + ergonomics | 3.7.0 | Pending |
| D | Ops: _scheduler, _db_updates, _prometheus | 3.8.0 | Pending |
| E | Full-text search (Nouveau/Clouseau) | TBD | Unscheduled |
