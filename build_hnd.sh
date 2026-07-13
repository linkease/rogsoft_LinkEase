#!/bin/sh
set -e

cd "$(dirname "$0")"
if [ -n "$LINKEASE_FULL_ARTIFACT_DIR" ]; then
	python3 ./build.py --artifact-dir "$LINKEASE_FULL_ARTIFACT_DIR"
else
	python3 ./build.py
fi
