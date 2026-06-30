Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "Starting FastAPI backend on http://127.0.0.1:8000"
& ".\.venv\Scripts\python.exe" -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
