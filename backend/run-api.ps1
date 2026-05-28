# LogRaven API -- run from LogRaven\backend (the folder that contains app\ and alembic.ini)
param([int]$Port = 8000)
$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
$env:PYTHONPATH = $BackendRoot
Set-Location $BackendRoot

# Load .env from repo root
$EnvFile = Join-Path $BackendRoot "..\.env"
if (Test-Path $EnvFile) {
    Write-Host "Loading env vars from .env ..."
    foreach ($rawLine in Get-Content $EnvFile) {
        $trimmed = $rawLine.Trim()
        if ($trimmed -and -not $trimmed.StartsWith('#') -and $trimmed -match '^([^=]+)=(.*)$') {
            $k = $Matches[1].Trim()
            $v = $Matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
        }
    }
} else {
    Write-Warning ".env not found -- make sure env vars are set manually"
}

# Resolve Python executable
$py = Join-Path $BackendRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

Write-Host ""
Write-Host "PYTHONPATH = $BackendRoot"
Write-Host "Python     = $py"
Write-Host "Port       = $Port"
Write-Host ""

# Verify key routes are registered
Write-Host "Verifying routes are registered..."
& $py -c @"
from app.main import app
paths = [getattr(r, 'path', '') for r in app.routes]

pp = [p for p in paths if 'play-parser' in p]
assert '/api/v1/play-parser/meta' in pp, 'PlayParser not mounted'
print('  OK  PlayParser  ->', ' '.join(sorted(pp)))

assert any('/audit/start' in p for p in paths), 'Compliance routes not mounted. Check router.py'
co = [p for p in paths if 'audit' in p]
print('  OK  Compliance  ->', ' '.join(sorted(co)))
"@
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Starting uvicorn on http://localhost:$Port ..."
Write-Host "API docs  http://localhost:$Port/docs"
Write-Host ""

# Only watch app/ so edits under tests/, alembic/ etc. don't reload mid-request
& $py -m uvicorn app.main:app --reload --port $Port --reload-dir app
