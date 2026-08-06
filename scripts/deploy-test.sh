#!/usr/bin/env bash
uv add twine
mkdir -p archive
mv dist/* archive
uv run python3 -m build
uv run python3 -m twine upload --repository testpypi dist/*