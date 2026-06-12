$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
