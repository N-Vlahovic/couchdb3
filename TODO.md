# Todo

## Authentication
- <s>Add cookie based authentication</s>

## Misc
- <s>Abstract away partition path insertion</s>
- <s>Fix `put_design` bug: `options = (options or {}).update(...)` always sets `options = None` (both sync and async)</s> — fixed in v3.4.0
- <s>Fix `Server.__repr__` docstring — currently copy-pasted from `__del__`, says "Close the session on delete"</s> — fixed in v3.4.0
- <s>Fix `Server.replicate` — posts to `_replicator` DB instead of `/_replicate` endpoint (persistent vs. one-shot replication)</s> — fixed in v3.4.0
- <s>Remove dead code: commented-out `self.root` line in `Partition.__init__`</s> — no dead code present
- <s>Remove orphaned `:return:` stub at end of `Database.save` docstring</s> — fixed in v3.4.0

## Test
- <s>Add partitioned methods tests</s> — `test_partitioned_database.py` has 2 tests (`test_create`, `test_put_design`); `Partition` class methods are untested in sync (async covered via `TestAsyncPartition`)
- <s>Add sync `Partition` method tests: `get`, `save`, `rev`, `delete`, `all_docs`, `find`, `view`, `info`, `bulk_docs`, `bulk_get`, `__contains__`</s> — added in v3.4.0
- <s>Add test for cookie auth token renewal path (`_is_auth_token_expired` + `_renew_auth_token`)</s> — added in v3.4.0
- <s>Add test for `Database.purge`</s> — added in v3.4.0
- <s>Add test for `Database.compact(ddoc=...)` (only no-arg path is tested)</s> — added in v3.4.0

## Missing API coverage
- <s>`GET /{db}/_changes` — change feed (polling / longpoll / continuous)</s> — `normal` and `longpoll` implemented in v3.3.0; `continuous`/`eventsource` streaming deferred
- <s>`GET /_membership` — cluster node membership</s> — implemented in v3.3.0
- <s>`POST /_cluster_setup` / `GET /_cluster_setup` — cluster setup API</s> — implemented in v3.3.0 (`cluster_setup` + `setup_cluster`)
- <s>`GET /_node/{node}/_config`, `_stats`, `_system` — node-level APIs</s> — implemented in v3.3.0 (`node_config`, `set_node_config`, `delete_node_config`, `reload_node_config`, `node_stats`, `node_system`)
- <s>`DELETE /{db}/_index/{ddoc}/json/{name}` — delete a Mango index</s> — implemented in v3.4.0 (`delete_index`)
- <s>`GET /{db}/_design_docs` — list design documents</s> — implemented in v3.4.0 (`design_docs`)
- <s>`__contains__` on `AsyncServer` (sync `Server` supports `if db in server`; async does not)</s> — implemented in v3.4.0 as `AsyncServer.has_db()`
- `GET /{db}/_local_docs` / `GET|PUT|DELETE /{db}/_local/{docid}` — local documents
- `GET|PUT /{db}/_revs_limit` — revision limit management
- `POST /{db}/_missing_revs` / `POST /{db}/_revs_diff` — replication helpers
- `POST /{db}/_view_cleanup` — view index cleanup
- `GET /{db}/_changes` with `feed=continuous|eventsource` — streaming feeds (deferred)
  - **sync:** implement `Database.changes_stream()` as a generator using `httpx.Client.stream()`, yielding parsed JSON objects line-by-line from the NDJSON response; caller controls iteration and closure via a `with` block or explicit `.close()`
  - **async:** implement `AsyncDatabase.changes_stream()` as an async generator using `httpx.AsyncClient.stream()`, yielding the same parsed objects; caller drives with `async for` and the underlying connection is released on `aclose()` or generator exhaustion
