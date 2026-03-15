# LogRaven - Windows Development Setup Script
#
# Run this at the start of every dev session instead of
# manually activating the venv each time.
#
# Usage:
#   cd C:\Users\Naeem\Documents\LogRaven
#   .\scripts\windows_setup.ps1

$ErrorActionPreference = "Stop"

# Resolve paths

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"
$VenvScript  = Join-Path $BackendDir "venv\Scripts\Activate.ps1"

# ASCII Banner (no unicode - safe for all PowerShell terminals)

function Show-Banner {
    Write-Host ""
    Write-Host "  _                  ______" -ForegroundColor DarkRed
    Write-Host " | |    ___  __ _   |  __  \  __ _ __   _____ _ __" -ForegroundColor Red
    Write-Host " | |   / _ \/ _' |  | |__) |/ _' '_ \ / / _ \ '_ \" -ForegroundColor Red
    Write-Host " | |__| (_) | (_| | |  _  /| (_| | | V /  __/ | | |" -ForegroundColor Red
    Write-Host " |_____\___/ \__, | |_| \_\ \__,_|_| \_/ \___|_| |_|" -ForegroundColor DarkRed
    Write-Host "              __/ |" -ForegroundColor DarkRed
    Write-Host "             |___/   Watch your logs. Find the threat." -ForegroundColor Gray
    Write-Host ""
}

# Step 1: Disable psql pager (fixes 'more' not recognised error)

Write-Host "[1/4] " -NoNewline -ForegroundColor Cyan
Write-Host "Disabling psql pager (fixes Windows 'more' error)..." -ForegroundColor White
$env:PAGER   = ""
$env:PGPAGER = ""
Write-Host "      OK - PAGER disabled for this session" -ForegroundColor Green

# Step 2: Set PYTHONPATH so 'from app.x import y' works everywhere

Write-Host "[2/4] " -NoNewline -ForegroundColor Cyan
Write-Host "Setting PYTHONPATH to include backend/..." -ForegroundColor White
$env:PYTHONPATH = $BackendDir
Write-Host "      OK - PYTHONPATH=$env:PYTHONPATH" -ForegroundColor Green

# Step 3: Activate virtual environment

Write-Host "[3/4] " -NoNewline -ForegroundColor Cyan
Write-Host "Activating virtual environment..." -ForegroundColor White

if (-Not (Test-Path $VenvScript)) {
    Write-Host "      ERROR - venv not found at: $VenvScript" -ForegroundColor Red
    Write-Host "             Run: python -m venv backend\venv" -ForegroundColor Yellow
    exit 1
}

. $VenvScript

$PythonVersion = & python --version 2>&1
Write-Host "      OK - venv activated ($PythonVersion)" -ForegroundColor Green

# Step 4: Change to backend directory

Write-Host "[4/4] " -NoNewline -ForegroundColor Cyan
Write-Host "Switching to backend/ directory..." -ForegroundColor White
Set-Location $BackendDir
Write-Host "      OK - cwd: $(Get-Location)" -ForegroundColor Green

# Summary

Write-Host ""
Write-Host "-----------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  Dev environment ready. Common commands:" -ForegroundColor White
Write-Host ""
Write-Host "  Start API server:" -ForegroundColor Gray
Write-Host "    uvicorn app.main:app --reload --port 8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Database utilities (no psql needed):" -ForegroundColor Gray
Write-Host "    python scripts/db.py check" -ForegroundColor Yellow
Write-Host "    python scripts/db.py tables" -ForegroundColor Yellow
Write-Host "    python scripts/db.py migrations" -ForegroundColor Yellow
Write-Host "    python scripts/db.py drop" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Run migrations:" -ForegroundColor Gray
Write-Host "    alembic upgrade head" -ForegroundColor Yellow
Write-Host ""
Write-Host "-----------------------------------------------------" -ForegroundColor DarkGray

Show-Banner
