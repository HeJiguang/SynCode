param(
    [Parameter(Mandatory = $true)]
    [string]$DbSummary,

    [Parameter(Mandatory = $true)]
    [string]$RedisSummary
)

function Get-MetricValue {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Summary,

        [Parameter(Mandatory = $true)]
        [string]$Metric,

        [Parameter(Mandatory = $true)]
        [string]$Field
    )

    return [double]$Summary.metrics.$Metric.$Field
}

function Format-PercentDelta {
    param(
        [double]$OldValue,
        [double]$NewValue,
        [bool]$HigherIsBetter = $false
    )

    if ($OldValue -eq 0) {
        return "n/a"
    }

    if ($HigherIsBetter) {
        $delta = (($NewValue - $OldValue) / $OldValue) * 100
    } else {
        $delta = (($OldValue - $NewValue) / $OldValue) * 100
    }

    return "{0:N2}%" -f $delta
}

$db = Get-Content $DbSummary -Raw | ConvertFrom-Json
$redis = Get-Content $RedisSummary -Raw | ConvertFrom-Json

$dbAvg = Get-MetricValue -Summary $db -Metric "http_req_duration" -Field "avg"
$dbP95 = Get-MetricValue -Summary $db -Metric "http_req_duration" -Field "p(95)"
$dbP99 = Get-MetricValue -Summary $db -Metric "http_req_duration" -Field "p(99)"
$dbRps = Get-MetricValue -Summary $db -Metric "http_reqs" -Field "rate"
$dbErrorRate = Get-MetricValue -Summary $db -Metric "http_req_failed" -Field "value"

$redisAvg = Get-MetricValue -Summary $redis -Metric "http_req_duration" -Field "avg"
$redisP95 = Get-MetricValue -Summary $redis -Metric "http_req_duration" -Field "p(95)"
$redisP99 = Get-MetricValue -Summary $redis -Metric "http_req_duration" -Field "p(99)"
$redisRps = Get-MetricValue -Summary $redis -Metric "http_reqs" -Field "rate"
$redisErrorRate = Get-MetricValue -Summary $redis -Metric "http_req_failed" -Field "value"

$rows = @(
    [PSCustomObject]@{
        Interface = "DB list"
        AvgMs = "{0:N2}" -f $dbAvg
        P95Ms = "{0:N2}" -f $dbP95
        P99Ms = "{0:N2}" -f $dbP99
        ReqPerSec = "{0:N2}" -f $dbRps
        ErrorRate = "{0:P2}" -f $dbErrorRate
    }
    [PSCustomObject]@{
        Interface = "Redis list"
        AvgMs = "{0:N2}" -f $redisAvg
        P95Ms = "{0:N2}" -f $redisP95
        P99Ms = "{0:N2}" -f $redisP99
        ReqPerSec = "{0:N2}" -f $redisRps
        ErrorRate = "{0:P2}" -f $redisErrorRate
    }
)

$rows | Format-Table -AutoSize

Write-Host ""
Write-Host "Improvement summary (Redis compared with DB):"
Write-Host ("  Avg latency improvement: {0}" -f (Format-PercentDelta -OldValue $dbAvg -NewValue $redisAvg))
Write-Host ("  P95 latency improvement: {0}" -f (Format-PercentDelta -OldValue $dbP95 -NewValue $redisP95))
Write-Host ("  P99 latency improvement: {0}" -f (Format-PercentDelta -OldValue $dbP99 -NewValue $redisP99))
Write-Host ("  Throughput improvement: {0}" -f (Format-PercentDelta -OldValue $dbRps -NewValue $redisRps -HigherIsBetter $true))
