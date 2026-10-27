param([switch]$SkipOllama)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path (Get-Location) '.runtime\python'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.runtime\browsers'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required. Install it using https://docs.astral.sh/uv/getting-started/installation/'
}
uv sync --python 3.12 --extra automation --extra dev
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; inspect network access.' }
& .\.venv\Scripts\python.exe -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed.' }
if (-not $SkipOllama) {
    $destination = Join-Path (Get-Location) '.runtime\ollama'
    if (-not (Test-Path (Join-Path $destination 'ollama.exe'))) {
        $release = Invoke-RestMethod 'https://api.github.com/repos/ollama/ollama/releases/latest'
        $asset = $release.assets | Where-Object name -eq 'ollama-windows-amd64.zip'
        if (-not $asset -or -not $asset.digest.StartsWith('sha256:')) {
            throw 'Release archive or SHA256 digest missing; inspect official release manually.'
        }
        $archive = Join-Path (Get-Location) '.runtime\ollama-download.zip'
        Invoke-WebRequest $asset.browser_download_url -OutFile $archive -UseBasicParsing
        $expected = $asset.digest.Substring(7)
        if ((Get-FileHash $archive -Algorithm SHA256).Hash -ne $expected) { throw 'Ollama checksum mismatch' }
        New-Item -ItemType Directory -Force $destination | Out-Null
        Expand-Archive -LiteralPath $archive -DestinationPath $destination
        $release.tag_name | Set-Content (Join-Path $destination 'VERSION')
    }
    Write-Output 'Next: .\scripts\start-model.ps1, then .\scripts\pull-model.ps1 in another terminal.'
}
uv pip freeze > requirements-installed.txt
Write-Output 'Dependencies installed. Run the tests and live acceptance checks documented in README.md.'
