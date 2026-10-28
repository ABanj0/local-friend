$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$missing = @('uv', 'node', 'npm', 'cargo', 'rustc') | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) }
if ($missing) { throw "Missing tools: $($missing -join ', '). Follow docs/desktop.md prerequisite steps, then reopen PowerShell." }
$env:UV_CACHE_DIR = Join-Path $root '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $root '.runtime\python'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $root '.runtime\browsers'
uv sync --python 3.12 --extra automation --extra desktop --extra dev --extra bundle --extra mcp
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed to install. Check the package download error; do not disable security software.' }
& .\.venv\Scripts\python.exe -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed.' }
Push-Location desktop
try {
    if (Test-Path package-lock.json) { npm ci } else { npm install }
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependencies failed to install.' }
} finally { Pop-Location }
Write-Output 'Dependencies installed. Next: .\desktop-dev.ps1'
