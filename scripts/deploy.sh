#!/usr/bin/env bash
python3 -m pip install --upgrade twine
mkdir -p archive
mv dist/* archive
python3 -m build
python3 -m twine upload --repository pypi dist/*
