$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js is missing. See docs/desktop.md.' }
if (-not (Test-Path '.venv\Scripts\python.exe') -or -not (Test-Path 'desktop\node_modules')) {
    throw 'Run .\scripts\setup-desktop.ps1 first.'
}
& .\.venv\Scripts\python.exe -c 'import fastapi, uvicorn, websockets'
if ($LASTEXITCODE -ne 0) { throw 'Desktop backend dependencies are missing. Run setup-desktop.ps1.' }
Push-Location desktop
try {
    npm run desktop
    if ($LASTEXITCODE -ne 0) { throw 'Desktop startup failed; inspect the compiler output above.' }
} finally { Pop-Location }
