# LogRaven API — run from LogRaven\backend (folder that contains app\ and alembic.ini)
param([int]$Port = 8000)
$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
$env:PYTHONPATH = $BackendRoot
Set-Location $BackendRoot
$py = Join-Path $BackendRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
Write-Host "PYTHONPATH=$BackendRoot"
& $py -m uvicorn app.main:app --reload --port $Port
