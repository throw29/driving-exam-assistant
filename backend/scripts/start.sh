#!/usr/bin/env bash
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BACKEND_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "[ERROR] uv not found. Install it first:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
  echo "[INFO] Created backend/.env from .env.example. Please change DT_API_KEY."
fi

echo "[1/2] Syncing dependencies with uv..."
uv sync

echo "[2/2] Starting API server at http://127.0.0.1:8000 ..."
exec uv run serve
