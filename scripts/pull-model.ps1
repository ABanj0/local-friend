param([string]$Model = 'qwen3.5:9b')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:OLLAMA_HOST = '127.0.0.1:11434'
& .\.runtime\ollama\ollama.exe pull $Model
if ($LASTEXITCODE -ne 0) { throw 'Model pull failed' }
