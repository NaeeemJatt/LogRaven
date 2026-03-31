# Apply Alembic migrations — run from LogRaven\backend
$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
Set-Location $BackendRoot
$py = Join-Path $BackendRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py -m alembic upgrade head
