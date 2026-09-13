---
name: couchdb3-version-bump
description: Use when bumping the couchdb3 version. Lists every file to update, the correct command to sync uv.lock, and the semantic versioning rules for choosing a, b, or c in a.b.c.
---

# couchdb3 Version Bump

## Files to update

| File | What to change |
|---|---|
| `pyproject.toml` | `version = "x.y.z"` under `[project]` |
| `setup.py` | `version="x.y.z"` |
| `uv.lock` | **Do not edit manually** — run `uv sync` after updating the above two files |

## SOP

1. Decide the new version (see rules below)
2. Update `pyproject.toml` → `version = "x.y.z"`
3. Update `setup.py` → `version="x.y.z"`
4. Run `uv sync` to regenerate `uv.lock`
5. Run `make test` to verify nothing is broken
6. Commit all three files: `git commit -m "Bump version to x.y.z"`

## Semantic versioning rules (`a.b.c`)

`couchdb3` follows [Semantic Versioning](https://semver.org). The library is in the `3.x.x` family
(the `3` reflects CouchDB 3.x compatibility, not a breaking API change).

### `c` — patch (e.g. `3.2.0` → `3.2.1`)
- Bug fixes with no public API changes
- Linting, formatting, or style-only changes shipped as a release
- Dependency pin adjustments
- Internal refactors with no user-visible behaviour change

### `b` — minor (e.g. `3.2.0` → `3.3.0`)
- New functionality added in a backward-compatible way
- New public methods, classes, or parameters with defaults
- New submodules or re-export paths that don't remove existing ones
- Examples: async client added (`3.1.0` → `3.2.0`)

### `a` — major (e.g. `3.2.0` → `4.0.0`)
- Breaking changes to the public API
- Removing or renaming existing public classes, methods, or parameters
- Changing method signatures in a non-backward-compatible way
- Dropping Python version support

## Version history

| Version | PR | Change |
|---|---|---|
| `3.0.4` | — | Original baseline |
| `3.1.0` | #32 | `requests` → `httpx` migration |
| `3.2.0` | #34 | Async client, `sync/` and `aio/` subpackages |
| `3.2.1` | #36 | Linting/style fixes, ruff config, dependency cleanup |
| `3.3.0` | #37 | `Database.changes()`, `Server.membership()`, `cluster_setup()`, `setup_cluster()`, `node_config()`, `set_node_config()`, `delete_node_config()`, `reload_node_config()`, `node_stats()`, `node_system()` — all sync + async |
| `3.3.1` | #38 | Fix `RuntimeError` on chained `Server().__getitem__().method()` (session lifetime bug, issue #39); adds read-only `Database.server`, `Partition.database`, `AsyncDatabase.server`, `AsyncPartition.database` back-reference properties |
| `3.4.0` | #40 | `Database.delete_index()`, `Database.design_docs()`, `AsyncServer.has_db()` (all sync + async); fix `put_design` options bug and `Server.replicate` endpoint; broader test coverage |
