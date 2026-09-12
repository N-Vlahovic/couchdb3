#!/usr/bin/env bash
uv pip install pdoc3 --quiet
rm -rf docs
uv run pdoc --html -o docs src/couchdb3 --force
mv docs/couchdb3/* docs/
rm -rf docs/couchdb3

