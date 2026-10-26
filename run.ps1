# Start ReqDoc AI and open it in the browser (default http://localhost:8000).
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

$port = 8000
if (Test-Path ".env") {
    foreach ($line in Get-Content ".env") {
        if ($line -match "^REQDOC_PORT=(\d+)$") { $port = [int]$Matches[1] }
    }
}
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Port $port is already in use (is ReqDoc already running, or another app?)." -ForegroundColor Red
    Write-Host "Close it, or set a different REQDOC_PORT in .env."
    exit 1
}
if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "The web app is not built yet. Run setup.ps1 (needs Node.js)." -ForegroundColor Yellow
}

$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$url = "http://localhost:$port"
Start-Job { param($u) Start-Sleep 3; Start-Process $u } -ArgumentList $url | Out-Null
Write-Host "ReqDoc AI is starting at $url  (press Ctrl+C to stop)" -ForegroundColor Green
& .\.venv\Scripts\python.exe -m uvicorn reqdoc.api:app --host 127.0.0.1 --port $port
