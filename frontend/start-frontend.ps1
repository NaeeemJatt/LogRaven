# LogRaven — Start Frontend Dev Server on port 5173
# Usage: .\start-frontend.ps1  (from the frontend/ folder)

$PORT = 5173

Write-Host ""
Write-Host "  LOGRAVEN frontend" -ForegroundColor Cyan
Write-Host "  Port: $PORT" -ForegroundColor DarkGray
Write-Host ""

$connections = Get-NetTCPConnection -LocalPort $PORT -ErrorAction SilentlyContinue

if ($connections) {
    foreach ($conn in $connections) {
        $procId = $conn.OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $procName = if ($proc) { $proc.Name } else { "unknown" }
        Write-Host "  Killing PID $procId ($procName) on port $PORT ..." -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 800
    Write-Host "  Port $PORT is now free." -ForegroundColor Green
} else {
    Write-Host "  Port $PORT is already free." -ForegroundColor Green
}

Write-Host ""

Set-Location $PSScriptRoot
npm run dev
