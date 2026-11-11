# NetraRakshak one-time setup for Windows (PowerShell 5+). Run from the project root:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "== Checking prerequisites ==" -ForegroundColor Cyan
$py = (Get-Command py -ErrorAction SilentlyContinue)
if ($py) { $python = "py -3" } elseif (Get-Command python -ErrorAction SilentlyContinue) { $python = "python" } else { throw "Python 3.11+ not found. Install from https://www.python.org/downloads/ (tick 'Add to PATH')." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 20+ not found. Install the LTS from https://nodejs.org/" }
Invoke-Expression "$python --version"; node --version

Write-Host "== Backend: virtual environment and packages ==" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { Invoke-Expression "$python -m venv .venv" }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path ".env")) {
  Copy-Item .env.example .env
  $secret = & .\.venv\Scripts\python.exe -c "import secrets;print(secrets.token_urlsafe(48))"
  $key = & .\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
  (Get-Content .env) -replace '^JWT_SECRET=.*', "JWT_SECRET=$secret" -replace '^STORAGE_ENCRYPTION_KEY=.*', "STORAGE_ENCRYPTION_KEY=$key" | Set-Content .env
  Write-Host "Created backend\.env with a fresh JWT secret and storage key. Back up STORAGE_ENCRYPTION_KEY securely." -ForegroundColor Yellow
}
& .\.venv\Scripts\python.exe scripts\seed.py

Write-Host "== Frontend: packages ==" -ForegroundColor Cyan
Set-Location "$root\frontend"
if (-not (Test-Path ".env.local")) { Copy-Item .env.example .env.local }
npm install --no-fund --no-audit

Set-Location $root
Write-Host "`nSetup complete. Start the app with .\start.ps1 (or start-backend.ps1 and start-frontend.ps1 in two terminals)." -ForegroundColor Green
