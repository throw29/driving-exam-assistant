@echo off
setlocal
cd /d "%~dp0"
echo Frontend URL: http://127.0.0.1:5500
echo Press Ctrl+C to stop.

where python >nul 2>nul
if not errorlevel 1 (
  python -m http.server 5500 --bind 127.0.0.1 --directory "%~dp0frontend"
  exit /b %errorlevel%
)

where uv >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Neither python nor uv is available. Open frontend\index.html directly instead.
  exit /b 1
)

pushd "%~dp0backend"
uv run python -m http.server 5500 --bind 127.0.0.1 --directory "%~dp0frontend"
set ERR=%errorlevel%
popd
exit /b %ERR%
