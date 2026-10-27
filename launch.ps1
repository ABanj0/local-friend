param([Parameter(Mandatory=$true, Position=0)][string]$Task,
      [ValidateSet('unified','coding','browser','desktop')][string]$Profile = 'unified')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PSScriptRoot '.runtime\browsers'
& .\.venv\Scripts\python.exe -m local_agent run $Task --profile $Profile
exit $LASTEXITCODE
