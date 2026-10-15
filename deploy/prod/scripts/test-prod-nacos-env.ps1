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
        "NACOS_DISCOVERY_ENABLED=true",
        "MYSQL_HOST=",
        "MYSQL_APP_USER=",
        "MYSQL_PASSWORD=",
        "REDIS_HOST=",
        "REDIS_PASSWORD=",
        "RABBITMQ_HOST=",
        "RABBITMQ_DEFAULT_USER=",
        "RABBITMQ_DEFAULT_PASS=",
        "OJ_AGENT_PORT=",
        "OJ_AGENT_LLM_BASE_URL=",
        "OJ_AGENT_LLM_API_KEY=",
        "OJ_AGENT_CHAT_MODEL=",
        "OJ_AGENT_TRAINING_MODEL="
    )

    foreach ($snippet in $requiredSnippets) {
        if (-not $content.Contains($snippet)) {
            throw "$path is missing Nacos runtime env: $snippet"
        }
    }
}
