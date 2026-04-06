param(
    [switch]$SkipMavenInstall,
    [switch]$SkipJob,
    [switch]$SkipFrontends
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path $PSScriptRoot))
$frontendRoot = Join-Path $repoRoot "frontend"
$runtimeRoot = Join-Path $repoRoot "logs\local-runtime"
$localEnvScript = Join-Path $PSScriptRoot "local-env.ps1"
$agentScript = Join-Path $repoRoot "deploy\dev\agent\start-oj-agent-local.ps1"

if (-not (Test-Path $runtimeRoot)) {
    New-Item -ItemType Directory -Path $runtimeRoot | Out-Null
}

. $localEnvScript

function Get-EnvInt {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [int]$DefaultValue
    )

    $rawValue = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($rawValue)) {
        return $DefaultValue
    }

    return [int]$rawValue
}

function Resolve-CommandPath {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Candidates
    )

    foreach ($candidate in $Candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw "Cannot find command: $($Candidates -join ', ')"
}

function Test-PortListening {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Start-DetachedProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    if (Test-PortListening -Port $Port) {
        Write-Host ("[{0}] port {1} already listening, skip start." -f $Name, $Port) -ForegroundColor Yellow
        return
    }

    $stdout = Join-Path $runtimeRoot ("{0}.out.log" -f $Name)
    $stderr = Join-Path $runtimeRoot ("{0}.err.log" -f $Name)
    $pidFile = Join-Path $runtimeRoot ("{0}.pid" -f $Name)

    if (Test-Path $stdout) { Remove-Item -LiteralPath $stdout -Force }
    if (Test-Path $stderr) { Remove-Item -LiteralPath $stderr -Force }

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru `
        -WindowStyle Hidden

    Set-Content -LiteralPath $pidFile -Value $process.Id
    Write-Host ("[{0}] started pid={1}, port={2}" -f $Name, $process.Id, $Port) -ForegroundColor Green
}

function Wait-ForHttp {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSec = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Host ("[{0}] ready -> {1} ({2})" -f $Name, $Url, $response.StatusCode) -ForegroundColor Green
                return
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "[${Name}] not ready within ${TimeoutSec}s: ${Url}"
}

$mvn = Resolve-CommandPath -Candidates @("mvn.cmd", "mvn")
$npm = Resolve-CommandPath -Candidates @("npm.cmd", "npm")
$powershellExe = Resolve-CommandPath -Candidates @("powershell.exe")
$frontendWebPort = Get-EnvInt -Name "FRONTEND_WEB_PORT" -DefaultValue 4000
$frontendAppPort = Get-EnvInt -Name "FRONTEND_APP_PORT" -DefaultValue 4201
$frontendAdminPort = Get-EnvInt -Name "FRONTEND_ADMIN_PORT" -DefaultValue 4002
$agentPort = Get-EnvInt -Name "OJ_AGENT_PORT" -DefaultValue 8016
$frontendWebUrl = "http://127.0.0.1:{0}" -f $frontendWebPort
$frontendAppUrl = "http://127.0.0.1:{0}/app" -f $frontendAppPort
$frontendAdminUrl = "http://127.0.0.1:{0}/admin" -f $frontendAdminPort

if (-not $SkipMavenInstall) {
    Write-Host "[maven] installing local snapshots to temp/m2-repo..." -ForegroundColor Cyan
    Push-Location $repoRoot
    try {
        & $mvn "-q" "-Dmaven.repo.local=temp/m2-repo" "-DskipTests" "install"
    }
    finally {
        Pop-Location
    }
}

$services = @(
    @{
        Name = "oj-agent"
        FilePath = $powershellExe
        Args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $agentScript)
        WorkingDirectory = $repoRoot
        Port = $agentPort
    }
    @{
        Name = "oj-system"
        FilePath = $mvn
        Args = @("-f", "oj-modules/oj-system/pom.xml", "-Dmaven.repo.local=temp/m2-repo", "spring-boot:run", "-Dspring-boot.run.profiles=local")
        WorkingDirectory = $repoRoot
        Port = 9201
    }
    @{
        Name = "oj-judge"
        FilePath = $mvn
        Args = @("-f", "oj-modules/oj-judge/pom.xml", "-Dmaven.repo.local=temp/m2-repo", "spring-boot:run", "-Dspring-boot.run.profiles=local")
        WorkingDirectory = $repoRoot
        Port = 9204
    }
    @{
        Name = "oj-friend"
        FilePath = $mvn
        Args = @("-f", "oj-modules/oj-friend/pom.xml", "-Dmaven.repo.local=temp/m2-repo", "spring-boot:run", "-Dspring-boot.run.profiles=local")
        WorkingDirectory = $repoRoot
        Port = 9202
    }
    @{
        Name = "oj-gateway"
        FilePath = $mvn
        Args = @("-f", "oj-gateway/pom.xml", "-Dmaven.repo.local=temp/m2-repo", "spring-boot:run", "-Dspring-boot.run.profiles=local")
        WorkingDirectory = $repoRoot
        Port = 19090
    }
)

if (-not $SkipJob) {
    $services += @{
        Name = "oj-job"
        FilePath = $mvn
        Args = @("-f", "oj-modules/oj-job/pom.xml", "-Dmaven.repo.local=temp/m2-repo", "spring-boot:run", "-Dspring-boot.run.profiles=local")
        WorkingDirectory = $repoRoot
        Port = 9203
    }
}

if (-not $SkipFrontends) {
    $services += @(
        @{
            Name = "frontend-web"
            FilePath = $npm
            Args = @("run", "dev", "-w", "@aioj/web", "--", "--port", $frontendWebPort.ToString())
            WorkingDirectory = $frontendRoot
            Port = $frontendWebPort
        }
        @{
            Name = "frontend-app"
            FilePath = $npm
            Args = @("run", "dev", "-w", "@aioj/app", "--", "--port", $frontendAppPort.ToString())
            WorkingDirectory = $frontendRoot
            Port = $frontendAppPort
        }
        @{
            Name = "frontend-admin"
            FilePath = $npm
            Args = @("run", "dev", "-w", "@aioj/admin", "--", "--port", $frontendAdminPort.ToString())
            WorkingDirectory = $frontendRoot
            Port = $frontendAdminPort
        }
    )
}

foreach ($service in $services) {
    Start-DetachedProcess `
        -Name $service.Name `
        -FilePath $service.FilePath `
        -ArgumentList $service.Args `
        -WorkingDirectory $service.WorkingDirectory `
        -Port $service.Port
}

Write-Host "[health] waiting for backend services..." -ForegroundColor Cyan
& $powershellExe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "check-local-services.ps1")

if (-not $SkipFrontends) {
    Write-Host "[health] waiting for frontend services..." -ForegroundColor Cyan
    Wait-ForHttp -Name "frontend-web" -Url $frontendWebUrl -TimeoutSec 240
    Wait-ForHttp -Name "frontend-app" -Url $frontendAppUrl -TimeoutSec 240
    Wait-ForHttp -Name "frontend-admin" -Url $frontendAdminUrl -TimeoutSec 240
}

Write-Host ""
Write-Host "Local stack is ready." -ForegroundColor Green
Write-Host ("Logs: {0}" -f $runtimeRoot) -ForegroundColor Green
