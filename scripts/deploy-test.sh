#!/usr/bin/env bash
uv pip install build twine --quiet
if [ -z "$(ls -A dist 2>/dev/null)" ]; then
	echo "dist folder empty"
else
	mkdir -p archive
	mv dist/* archive
fi
uv run python3 -m build
uv run python3 -m twine upload --repository testpypi dist/*