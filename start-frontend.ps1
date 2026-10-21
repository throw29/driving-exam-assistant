# Serve the static frontend over HTTP (optional; opening index.html directly also works)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root 'frontend'
$backend = Join-Path $root 'backend'
$port = 5500

Write-Host "Frontend directory: $frontend"
Write-Host "URL: http://127.0.0.1:$port"
Write-Host 'Press Ctrl+C to stop.'

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m http.server $port --bind 127.0.0.1 --directory $frontend
    exit $LASTEXITCODE
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host '[ERROR] Neither python nor uv is available. Open frontend/index.html directly instead.' -ForegroundColor Red
    exit 1
}

Push-Location $backend
try {
    uv run python -m http.server $port --bind 127.0.0.1 --directory $frontend
} finally {
    Pop-Location
}
