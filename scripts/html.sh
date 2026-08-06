#!/usr/bin/env bash
uv add pdoc3
rm -rf docs
pdoc --html -o docs couchdb3 --force
mv docs/couchdb3/* docs/
rm -rf docs/couchdb3
