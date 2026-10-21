@echo off
setlocal
cd /d "%~dp0.."

where uv >nul 2>nul
if errorlevel 1 (
  echo [ERROR] uv not found. Install it first:
  echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
  exit /b 1
)

if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  echo [INFO] Created backend\.env from .env.example. Please change DT_API_KEY.
)

echo [1/2] Syncing dependencies with uv...
uv sync
if errorlevel 1 exit /b 1

echo [2/2] Starting API server at http://127.0.0.1:8000 ...
uv run serve
