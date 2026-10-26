# For front-end developers: Python API with auto-reload (new window) + Rsbuild dev server on http://localhost:3000
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Run setup.ps1 first." -ForegroundColor Red
    exit 1
}
$nodeDir = $null
foreach ($dir in @((Get-Command node -ErrorAction SilentlyContinue | ForEach-Object { Split-Path $_.Source }), "$env:LOCALAPPDATA\Programs\nodejs", "$env:ProgramFiles\nodejs")) {
    if ($dir -and (Test-Path "$dir\node.exe")) { $nodeDir = $dir; break }
}
if (-not $nodeDir) {
    Write-Host "Node.js is required for front-end development. Install it from https://nodejs.org" -ForegroundColor Red
    exit 1
}
$env:Path = "$nodeDir;$env:Path"

$port = 8000
if (Test-Path ".env") {
    foreach ($line in Get-Content ".env") {
        if ($line -match "^REQDOC_PORT=(\d+)$") { $port = [int]$Matches[1] }
    }
}
$env:REQDOC_PORT = "$port"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; .\.venv\Scripts\python.exe -m uvicorn reqdoc.api:app --reload --port $port"
Set-Location frontend
if (-not (Test-Path "node_modules")) { npm install --no-audit --no-fund }
npm run dev
