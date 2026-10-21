# Start backend and static frontend in two PowerShell windows (Windows convenience)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process powershell -ArgumentList @(
    '-NoExit', '-ExecutionPolicy', 'Bypass',
    '-File', (Join-Path $root 'start-backend.ps1')
)
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList @(
    '-NoExit', '-ExecutionPolicy', 'Bypass',
    '-File', (Join-Path $root 'start-frontend.ps1')
)
Start-Sleep -Seconds 1
Start-Process 'http://127.0.0.1:5500'

Write-Host 'Backend  : http://127.0.0.1:8000'
Write-Host 'API docs : http://127.0.0.1:8000/docs'
Write-Host 'Frontend : http://127.0.0.1:5500'
