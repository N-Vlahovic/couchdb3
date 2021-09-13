#!/usr/bin/env bash
python3 -m pip install --upgrade pdoc3
rm -rf docs
pdoc --html -o docs couchdb3 --force
mv docs/couchdb3/* docs/
rm -rf docs/couchdb3
