$ErrorActionPreference = "Stop"

$frontendWebPort = if ($env:FRONTEND_WEB_PORT) { [int]$env:FRONTEND_WEB_PORT } else { 4000 }
$frontendAppPort = if ($env:FRONTEND_APP_PORT) { [int]$env:FRONTEND_APP_PORT } else { 4201 }
$frontendAdminPort = if ($env:FRONTEND_ADMIN_PORT) { [int]$env:FRONTEND_ADMIN_PORT } else { 4002 }
$agentPort = if ($env:OJ_AGENT_PORT) { [int]$env:OJ_AGENT_PORT } else { 8016 }

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path $PSScriptRoot))
$runtimeRoot = Join-Path $repoRoot "logs\local-runtime"

$services = @(
    @{ Name = "frontend-web"; Port = $frontendWebPort },
    @{ Name = "frontend-app"; Port = $frontendAppPort },
    @{ Name = "frontend-admin"; Port = $frontendAdminPort },
    @{ Name = "oj-agent"; Port = $agentPort },
    @{ Name = "oj-gateway"; Port = 19090 },
    @{ Name = "oj-system"; Port = 9201 },
    @{ Name = "oj-friend"; Port = 9202 },
    @{ Name = "oj-job"; Port = 9203 },
    @{ Name = "oj-judge"; Port = 9204 }
)

function Stop-ByPidFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $pidFile = Join-Path $runtimeRoot ("{0}.pid" -f $Name)
    if (-not (Test-Path $pidFile)) {
        return $false
    }

    $pidValue = Get-Content $pidFile | Select-Object -First 1
    if ($pidValue -and (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
        & taskkill /PID $pidValue /T /F | Out-Null
        Write-Host ("[{0}] stopped by pid={1}" -f $Name, $pidValue) -ForegroundColor Green
    }

    Remove-Item -LiteralPath $pidFile -Force
    return $true
}

function Stop-ByPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        & taskkill /PID $listener.OwningProcess /T /F | Out-Null
        Write-Host ("[{0}] stopped by port {1}, pid={2}" -f $Name, $Port, $listener.OwningProcess) -ForegroundColor Yellow
    }
}

foreach ($service in $services) {
    $stoppedByPidFile = Stop-ByPidFile -Name $service.Name
    if (-not $stoppedByPidFile) {
        Stop-ByPort -Name $service.Name -Port $service.Port
    }
}

Write-Host ""
Write-Host "Local stack stop attempt finished." -ForegroundColor Green
