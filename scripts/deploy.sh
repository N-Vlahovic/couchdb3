#!/usr/bin/env bash
uv add twine
mkdir -p archive
mv dist/* archive
python3 -m build
python3 -m twine upload --repository pypi dist/*
