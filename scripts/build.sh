#!/usr/bin/env bash
uv add build
if [ -z "$(ls -A dist)" ]; then
	echo "dist folder empty"
else
	mkdir -p archive
	mv dist/* archive
fi
python3 -m build
