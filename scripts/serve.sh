#!/usr/bin/env bash
set -euo pipefail
exec python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${PORT:-10000}" --workers 1
