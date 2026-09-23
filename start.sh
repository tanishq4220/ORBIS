#!/usr/bin/env bash
# Render startup script
set -euo pipefail

cd backend
exec uvicorn server:app --host 0.0.0.0 --port "${PORT:-10000}"
