# LogRaven API — run from LogRaven\backend (folder that contains app\ and alembic.ini)
param([int]$Port = 8000)
$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
$env:PYTHONPATH = $BackendRoot
Set-Location $BackendRoot
$py = Join-Path $BackendRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
Write-Host "PYTHONPATH=$BackendRoot"
Write-Host "Verifying PlayParser routes are registered..."
& $py -c @"
from app.main import app
paths = [getattr(r, 'path', '') for r in app.routes if 'play-parser' in getattr(r, 'path', '')]
assert '/api/v1/play-parser/meta' in paths, (
    'PlayParser not mounted. Use this repo/branch, run from LogRaven\\backend, '
    'and restart uvicorn so app.api.router includes play_parser.'
)
print('  OK —', ' '.join(sorted(paths)))
"@
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
# Only watch app/ — otherwise edits under tests/, alembic/, etc. reload mid-request → 404 / ECONNRESET on PlayParser uploads.
& $py -m uvicorn app.main:app --reload --port $Port --reload-dir app
