param([switch]$ConfigLoaderRunner)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
foreach ($tool in @('npm', 'cargo', 'rustc')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Missing $tool. See docs/desktop.md." }
}
& .\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed.' }
& .\.venv\Scripts\python.exe -m ruff check local_agent tests
if ($LASTEXITCODE -ne 0) { throw 'Python lint failed.' }
& .\.venv\Scripts\python.exe -c "from local_agent.mcp_provider import require_sdk; require_sdk()"
if ($LASTEXITCODE -ne 0) { throw 'Pinned MCP dependencies missing. Run scripts/setup-desktop.ps1.' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --name agent-backend --collect-all playwright --collect-all pywinauto --collect-all pyautogui --collect-all uvicorn --collect-all websockets --collect-submodules mcp.client --collect-submodules mcp.server.lowlevel --collect-submodules mcp.shared --collect-submodules mcp.os --collect-data mcp --collect-all mcp_types --copy-metadata mcp --copy-metadata mcp-types --hidden-import psutil --paths $root local_agent/studio/runtime.py
if ($LASTEXITCODE -ne 0) { throw 'Python sidecar build failed.' }
$triple = (rustc -vV | Select-String '^host: ').ToString().Substring(6)
New-Item -ItemType Directory -Force desktop/src-tauri/binaries, desktop/src-tauri/resources | Out-Null
Copy-Item -LiteralPath dist/agent-backend.exe -Destination "desktop/src-tauri/binaries/agent-backend-$triple.exe" -Force
# Package a reviewed template, not the user's credentials or local configuration.
Copy-Item -LiteralPath desktop/agent.example.toml -Destination desktop/src-tauri/resources/agent.toml -Force
Push-Location desktop
try {
    if ($ConfigLoaderRunner) {
        $buildOverlay = Join-Path $root ('.runtime\package-' + [guid]::NewGuid().ToString('N') + '.json')
        @{ build = @{ beforeBuildCommand = 'npm run build -- --configLoader runner' } } |
            ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $buildOverlay -Encoding UTF8
        npm run package -- --config $buildOverlay
    } else { npm run package }
    $bundleExitCode = $LASTEXITCODE
} finally { Pop-Location }
$manifestArgs = @('--output', 'dist/release-manifest.json', '--sidecar', 'dist/agent-backend.exe')
if ($bundleExitCode -eq 0) { $manifestArgs += '--bundle-succeeded' }
& .\.venv\Scripts\python.exe scripts/release-manifest.py @manifestArgs
if ($LASTEXITCODE -ne 0) { throw 'Release manifest generation failed.' }
if ($bundleExitCode -ne 0) { throw 'Tauri bundling failed. See compiler/download errors above; partial artifact hashes are in dist/release-manifest.json.' }
Write-Output 'Installer: desktop/src-tauri/target/release/bundle/nsis/'
