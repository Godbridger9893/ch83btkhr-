#!/bin/bash
# Celestia — macOS / Linux launcher.
# Uses ./.venv when present, falls back to python3. Double-clickable in Finder
# when given a .command copy, or run from Terminal:  ./start_brahma.sh
set -e
cd "$(dirname "$0")"

if [ -x "./.venv/bin/python" ]; then
    PY="./.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "ERROR: python3 not found. Install it with:  brew install python@3.12"
    exit 1
fi

# First run ever? Bootstrap dependencies + config automatically.
if [ ! -f "config/api_keys.json" ]; then
    echo "First launch detected — running setup..."
    "$PY" setup.py || { echo "Setup failed. Fix the errors above and re-run."; exit 1; }
fi

exec "$PY" main.py "$@"
