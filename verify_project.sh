#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
"$PY" -m compileall -q ai game utils main.py config.py
"$PY" -m pytest -q
"$PY" tools/verify_release.py --episodes 20 --output verification/verification.json
