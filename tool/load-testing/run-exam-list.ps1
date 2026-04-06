param(
    [ValidateSet("db", "redis")]
    [string]$Mode = "db",

    [ValidateSet("warmup", "formal")]
    [string]$Phase = "formal",

    [int]$Vus = 50,

    [string]$Duration = "",

    [string]$BaseUrl = "http://127.0.0.1:19090"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$k6Exe = Join-Path $scriptDir "bin\k6-v1.7.1-windows-amd64\k6.exe"
$k6Script = Join-Path $scriptDir "exam-list-db-vs-redis.js"
$resultsDir = Join-Path $scriptDir "results"

if (!(Test-Path $k6Exe)) {
    throw "k6 executable not found: $k6Exe"
}

if (!(Test-Path $resultsDir)) {
    New-Item -ItemType Directory -Force $resultsDir | Out-Null
}

$endpoint = if ($Mode -eq "redis") {
    "/friend/exam/semiLogin/redis/list"
} else {
    "/friend/exam/semiLogin/list"
}

if ([string]::IsNullOrWhiteSpace($Duration)) {
    $Duration = if ($Phase -eq "warmup") { "30s" } else { "60s" }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$summaryFile = Join-Path $resultsDir "exam-list-$Mode-$Phase-$timestamp.json"

Write-Host "Running exam list load test..."
Write-Host "  Mode: $Mode"
Write-Host "  Phase: $Phase"
Write-Host "  BaseUrl: $BaseUrl"
Write-Host "  Endpoint: $endpoint"
Write-Host "  VUs: $Vus"
Write-Host "  Duration: $Duration"
Write-Host "  Summary: $summaryFile"

$env:BASE_URL = $BaseUrl
$env:ENDPOINT = $endpoint
$env:VUS = [string]$Vus
$env:DURATION = $Duration
$env:PAUSE_SECONDS = "1"

& $k6Exe run $k6Script --summary-export $summaryFile
$exitCode = $LASTEXITCODE

Remove-Item Env:BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:ENDPOINT -ErrorAction SilentlyContinue
Remove-Item Env:VUS -ErrorAction SilentlyContinue
Remove-Item Env:DURATION -ErrorAction SilentlyContinue
Remove-Item Env:PAUSE_SECONDS -ErrorAction SilentlyContinue

if ($exitCode -ne 0) {
    throw "k6 run failed with exit code $exitCode"
}

Write-Host ""
Write-Host "Load test finished."
Write-Host "Summary file: $summaryFile"
