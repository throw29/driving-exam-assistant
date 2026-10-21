# Start backend (delegates to backend/scripts/start.ps1)
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'backend\scripts\start.ps1'
& $script
exit $LASTEXITCODE
