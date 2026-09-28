#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python_command=""
for candidate in python3.13 python3.12 python3.11 python3.14 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
    python_command="$candidate"
    break
  fi
done
if [ -z "$python_command" ]; then
  echo "Python 3.11 or newer is needed. Install Python from https://www.python.org/downloads/macos/ and reopen Terminal."
  exit 1
fi
if [ -x .venv/bin/python ]; then
  if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)'; then
    echo "The existing .venv uses an older Python. Rename it, then rerun this script to create a new environment."
    exit 1
  fi
else
  "$python_command" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.lock
if [ ! -f frontend/dist/index.html ]; then
  (cd frontend && npm ci && npm run build)
fi
exec .venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
