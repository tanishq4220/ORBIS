#!/usr/bin/env bash
# Render build script for native Python runtime
set -euo pipefail

echo "==> Building React frontend"
cd frontend
if [ -f package-lock.json ]; then
  npm ci --ignore-scripts
else
  npm install
fi
npm run build
cd ..

echo "==> Installing Python dependencies"
pip install -U pip
pip install -r backend/requirements.txt

echo "==> Build complete"
