# Todo

## Authentication
- <s>Add cookie based authentication</s>

## Misc
- <s>Abstract away partition path insertion</s>
- Fix `put_design` bug: `options = (options or {}).update(...)` always sets `options = None` (both sync and async)
- Fix `Server.__repr__` docstring — currently copy-pasted from `__del__`, says "Close the session on delete"
- Fix `Server.replicate` — posts to `_replicator` DB instead of `/_replicate` endpoint (persistent vs. one-shot replication)
- Remove dead code: commented-out `self.root` line in `Partition.__init__`
- Remove orphaned `:return:` stub at end of `Database.save` docstring

## Test
- <s>Add partitioned methods tests</s> — `test_partitioned_database.py` has 2 tests (`test_create`, `test_put_design`); `Partition` class methods are untested in sync (async covered via `TestAsyncPartition`)
- Add sync `Partition` method tests: `get`, `save`, `rev`, `delete`, `all_docs`, `find`, `view`, `info`, `bulk_docs`, `bulk_get`, `__contains__`
- Add test for cookie auth token renewal path (`_is_auth_token_expired` + `_renew_auth_token`)
- Add test for `Database.purge`
- Add test for `Database.compact(ddoc=...)` (only no-arg path is tested)

## Missing API coverage
- `GET /{db}/_changes` — change feed (polling / longpoll / continuous)
- `DELETE /{db}/_index/{ddoc}/json/{name}` — delete a Mango index
- `GET /{db}/_design_docs` — list design documents
- `GET /{db}/_local_docs` / `GET|PUT|DELETE /{db}/_local/{docid}` — local documents
- `GET /_membership` — cluster node membership
- `POST /_cluster_setup` / `GET /_cluster_setup` — cluster setup API
- `GET /_node/{node}/_config`, `_stats`, `_system` — node-level APIs
- `GET|PUT /{db}/_revs_limit` — revision limit management
- `POST /{db}/_missing_revs` / `POST /{db}/_revs_diff` — replication helpers
- `POST /{db}/_view_cleanup` — view index cleanup
- `__contains__` on `AsyncServer` (sync `Server` supports `if db in server`; async does not)
