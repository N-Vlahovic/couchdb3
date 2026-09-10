#!/usr/bin/env bash
rm -rf docs
uv run pdoc --html -o docs src/couchdb3 --force
mv docs/couchdb3/* docs/
rm -rf docs/couchdb3

