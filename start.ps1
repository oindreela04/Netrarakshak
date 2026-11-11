# Opens the API and the web app in two new PowerShell windows, then the browser.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$root\start-backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$root\start-frontend.ps1"
Start-Sleep -Seconds 8
Start-Process "http://localhost:3000"
