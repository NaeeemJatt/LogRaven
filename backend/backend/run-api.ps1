# If your shell is under backend\backend by mistake, this jumps to the real backend root.
$ErrorActionPreference = "Stop"
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& (Join-Path $BackendRoot "run-api.ps1") @args
