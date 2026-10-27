param([string]$ConfigPath = (Join-Path $env:LOCALAPPDATA 'local.agent.studio\agent.toml'))
$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path $PSScriptRoot -Parent
if (Get-Process -Name 'local-agent-studio' -ErrorAction SilentlyContinue) {
    throw 'Close Studio before configuring its installed Ollama paths.'
}
Push-Location $repositoryRoot
try {
    & .\.venv\Scripts\python.exe -m local_agent.studio.ollama_config --config $ConfigPath --executable (Join-Path $repositoryRoot '.runtime\ollama\ollama.exe') --models (Join-Path $repositoryRoot '.runtime\models')
    if ($LASTEXITCODE -ne 0) { throw 'Ollama configuration was not applied. Review the error above.' }
} finally { Pop-Location }
