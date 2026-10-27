param([switch]$Browser, [switch]$Model, [switch]$Desktop, [string]$BrowserChannel = '')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.runtime\browsers'
$env:LOCAL_AGENT_BROWSER_TEST = [string][int]$Browser.IsPresent
$env:LOCAL_AGENT_MODEL_TEST = [string][int]$Model.IsPresent
$env:LOCAL_AGENT_DESKTOP_TEST = [string][int]$Desktop.IsPresent
$env:LOCAL_AGENT_BROWSER_CHANNEL = $BrowserChannel
& .\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
exit $LASTEXITCODE
