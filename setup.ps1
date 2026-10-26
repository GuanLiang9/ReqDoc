# One-time setup: Python venv + packages + AI models + web app build. Safe to re-run.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Python {
    $candidates = @(
        { & py -3 -c "import sys;print(sys.executable)" },
        { & python -c "import sys;print(sys.executable)" },
        { (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1).FullName }
    )
    foreach ($c in $candidates) {
        try {
            $exe = & $c 2>$null
            if ($exe -and (Test-Path $exe)) {
                $v = & $exe -c "import sys;print('%d.%d' % sys.version_info[:2])"
                if ([version]$v -ge [version]"3.11") { return $exe }
            }
        } catch {}
    }
    return $null
}

function Find-Node {
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($cmd) { return Split-Path $cmd.Source }
    foreach ($dir in @("$env:LOCALAPPDATA\Programs\nodejs", "$env:ProgramFiles\nodejs")) {
        if (Test-Path "$dir\node.exe") { return $dir }
    }
    return $null
}

function Get-EnvValue($name, $default) {
    if (Test-Path ".env") {
        foreach ($line in Get-Content ".env") {
            if ($line -match "^$name=(.+)$") { return $Matches[1].Trim() }
        }
    }
    return $default
}

# 1. Python + packages
$py = Find-Python
if (-not $py) {
    Write-Host "Python 3.11+ not found. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then re-run." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python: $py"
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & $py -m venv .venv
}
$venvPy = ".\.venv\Scripts\python.exe"
Write-Host "Installing packages (first time takes a few minutes)..."
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

# 2. AI model (Ollama)
$model = Get-EnvValue "OLLAMA_MODEL" "qwen2.5:7b"
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) { $ollama = $ollama.Source }
if (-not $ollama -and (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe")) { $ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" }
if ($ollama) {
    Write-Host "Downloading AI model '$model' (several GB the first time)..."
    & $ollama pull $model
} else {
    Write-Host ""
    Write-Host "Ollama is not installed. Install it from https://ollama.com/download, then run:  ollama pull $model" -ForegroundColor Yellow
}

# 3. Speech model (Whisper) for recordings
$whisper = Get-EnvValue "WHISPER_MODEL" "small"
Write-Host "Downloading speech model '$whisper' (about 500 MB for 'small')..."
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
& $venvPy -c "from faster_whisper.utils import download_model; download_model('$whisper')" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not download the speech model now. It will download the first time you upload a recording (needs internet)." -ForegroundColor Yellow
}

# 4. Web app (needs Node.js only here, not to run the app)
if (Test-Path "frontend\dist\index.html") {
    Write-Host "Web app already built."
} else {
    $nodeDir = Find-Node
    if ($nodeDir) {
        $env:Path = "$nodeDir;$env:Path"
        Write-Host "Building the web app..."
        Push-Location frontend
        try {
            npm install --no-audit --no-fund
            npm run build
        } finally { Pop-Location }
    } else {
        Write-Host ""
        Write-Host "Node.js is not installed, so the web app could not be built." -ForegroundColor Yellow
        Write-Host "Install Node.js LTS from https://nodejs.org (or ask a teammate for the built 'frontend\dist' folder), then run setup.ps1 again."
    }
}

Write-Host ""
Write-Host "Setup finished. Start the app with:  powershell -ExecutionPolicy Bypass -File .\run.ps1" -ForegroundColor Green
