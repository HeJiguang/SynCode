$ErrorActionPreference = "Stop"

$agentPort = if ($env:OJ_AGENT_PORT) { [int]$env:OJ_AGENT_PORT } else { 8016 }

$targets = @(
    @{ Name = "gateway"; Port = 19090; Path = "/friend/doc.html" },
    @{ Name = "oj-system"; Port = 9201; Path = "/doc.html" },
    @{ Name = "oj-friend"; Port = 9202; Path = "/doc.html" },
    @{ Name = "oj-job"; Port = 9203; Path = "/" },
    @{ Name = "oj-judge"; Port = 9204; Path = "/doc.html" },
    @{ Name = "oj-agent"; Port = $agentPort; Path = "/docs" }
)

$results = foreach ($target in $targets) {
    $url = "http://127.0.0.1:{0}{1}" -f $target.Port, $target.Path
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
        [PSCustomObject]@{
            Name = $target.Name
            Port = $target.Port
            Url = $url
            Ok = $true
            Status = $response.StatusCode
        }
    }
    catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -lt 500) {
            [PSCustomObject]@{
                Name = $target.Name
                Port = $target.Port
                Url = $url
                Ok = $true
                Status = [int]$_.Exception.Response.StatusCode
            }
            continue
        }

        [PSCustomObject]@{
            Name = $target.Name
            Port = $target.Port
            Url = $url
            Ok = $false
            Status = $_.Exception.Message
        }
    }
}

$results | Format-Table -AutoSize

$failed = $results | Where-Object { -not $_.Ok }
if ($failed) {
    Write-Host ""
    Write-Host "Some local services are not ready." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "All local application services responded successfully." -ForegroundColor Green
