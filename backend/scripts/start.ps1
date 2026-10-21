# Driving Exam Assistant - backend launcher (Windows PowerShell)
$ErrorActionPreference = 'Stop'
$backend = Split-Path -Parent $PSScriptRoot
Set-Location $backend

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] uv not found. Install it first:" -ForegroundColor Red
    Write-Host '  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    exit 1
}

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host '[INFO] Created backend/.env from .env.example. Please change DT_API_KEY.' -ForegroundColor Yellow
}

Write-Host '[1/2] Syncing dependencies with uv...' -ForegroundColor Cyan
uv sync

Write-Host '[2/2] Starting API server at http://127.0.0.1:8000 ...' -ForegroundColor Cyan
uv run serve
