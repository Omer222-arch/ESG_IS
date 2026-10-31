Set-Location (Split-Path $PSScriptRoot -Parent)

$apiKeyLine = Get-Content ".env" | Where-Object { $_ -match '^ESG_API_KEY=(.*)$' } | Select-Object -First 1
if (-not $apiKeyLine) {
    throw "ESG_API_KEY was not found in .env"
}

$apiKey = $apiKeyLine -replace '^ESG_API_KEY=', ''
$body = @{ user_query = "Which companies have the highest revenue?" } | ConvertTo-Json -Compress

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/analyze" -Method Post -Headers @{ "X-API-Key" = $apiKey } -ContentType "application/json" -Body $body
$response | ConvertTo-Json -Depth 20