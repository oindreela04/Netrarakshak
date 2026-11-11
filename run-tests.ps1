$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\backend"
& .\.venv\Scripts\python.exe -m pytest -q
Set-Location "$root\frontend"
npm run typecheck
npm run build
