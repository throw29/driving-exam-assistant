#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${FRONTEND_PORT:-5500}"

echo "Frontend URL: http://127.0.0.1:${PORT}"
echo "Press Ctrl+C to stop."

if command -v python3 >/dev/null 2>&1; then
  exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT/frontend"
elif command -v python >/dev/null 2>&1; then
  exec python -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT/frontend"
elif command -v uv >/dev/null 2>&1; then
  cd "$ROOT/backend"
  exec uv run python -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT/frontend"
else
  echo "[ERROR] Neither python nor uv is available. Open frontend/index.html directly instead."
  exit 1
fi
