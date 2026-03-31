$ErrorActionPreference = "Stop"
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& (Join-Path $BackendRoot "migrate.ps1") @args
