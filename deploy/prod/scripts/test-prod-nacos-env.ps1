$ErrorActionPreference = "Stop"

$workflowPaths = @(
    ".github/workflows/cd.yml",
    ".github/workflows/prod-recover.yml"
)

foreach ($path in $workflowPaths) {
    $content = Get-Content $path -Raw

    $requiredSnippets = @(
        "NACOS_ENABLED=true",
        "NACOS_CONFIG_ENABLED=true",
        "NACOS_DISCOVERY_ENABLED=true"
    )

    foreach ($snippet in $requiredSnippets) {
        if (-not $content.Contains($snippet)) {
            throw "$path is missing production Nacos injection: $snippet"
        }
    }
}

$envPaths = @(
    "deploy/prod/env/runtime.env.prod.template",
    "deploy/prod/env/runtime.env.example"
)

foreach ($path in $envPaths) {
    $content = Get-Content $path -Raw

    $requiredSnippets = @(
        "NACOS_ENABLED=true",
        "NACOS_CONFIG_ENABLED=true",
        "NACOS_DISCOVERY_ENABLED=true"
    )

    foreach ($snippet in $requiredSnippets) {
        if (-not $content.Contains($snippet)) {
            throw "$path is missing Nacos runtime env: $snippet"
        }
    }
}
