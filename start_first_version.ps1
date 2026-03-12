$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$basePython = Join-Path $env:LOCALAPPDATA "Programs\\Python\\Python311\\python.exe"

if (-not (Test-Path $basePython)) {
    throw "Python 3.11 not found at $basePython"
}

$pythonExe = $basePython
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $root "backend\\requirements.txt")

Push-Location (Join-Path $root "frontend")
try {
    npm install
    npm run build
}
finally {
    Pop-Location
}

& $pythonExe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
