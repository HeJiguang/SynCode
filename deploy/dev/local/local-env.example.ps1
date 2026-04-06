$env:SPRING_PROFILES_ACTIVE = "local"

# Keep Nacos off for local pressure tests.
$env:NACOS_ENABLED = "false"
$env:NACOS_CONFIG_ENABLED = "false"
$env:NACOS_DISCOVERY_ENABLED = "false"

# Local service addresses.
$env:OJ_FRIEND_BASE_URL = "http://127.0.0.1:9202"
$env:OJ_JUDGE_BASE_URL = "http://127.0.0.1:9204"
$env:AI_GATEWAY_URI = "http://127.0.0.1:8016"
$env:AGENT_PUBLIC_BASE_URL = "http://127.0.0.1:8016"
$env:OJ_AGENT_PORT = "8016"
$env:FRONTEND_WEB_PORT = "4000"
$env:FRONTEND_APP_PORT = "4201"
$env:FRONTEND_ADMIN_PORT = "4002"

# Database: replace these if you want to use cloud MySQL.
$env:SPRING_DATASOURCE_URL = "jdbc:mysql://127.0.0.1:3306/bitoj_dev?useUnicode=true&characterEncoding=utf-8&useSSL=false&serverTimezone=Asia/Shanghai"
$env:SPRING_DATASOURCE_USERNAME = "ojtest"
$env:SPRING_DATASOURCE_PASSWORD = "change-me-local"

# Local middleware.
$env:REDIS_HOST = "127.0.0.1"
$env:REDIS_PORT = "16379"
$env:REDIS_PASSWORD = "change-me-local"

$env:RABBITMQ_HOST = "127.0.0.1"
$env:RABBITMQ_PORT = "5672"
$env:RABBITMQ_DEFAULT_USER = "admin"
$env:RABBITMQ_DEFAULT_PASS = "change-me-local"

$env:SPRING_ELASTICSEARCH_URIS = "http://127.0.0.1:9200"

# Judge sandbox: adjust if your Docker exposure differs.
# On some Windows setups Docker Desktop is exposed on tcp://localhost:2375.
$env:SANDBOX_DOCKER_HOST = "unix:///var/run/docker.sock"
$env:SANDBOX_DOCKER_VOLUME = "/usr/share/java"

# Optional mail / XXL-Job defaults for local.
$env:MAIL_IS_SEND = "false"
$env:XXL_JOB_ADMIN_ADDRESSES = "http://127.0.0.1:8080/xxl-job-admin"
$env:XXL_JOB_ACCESS_TOKEN = ""
$env:XXL_JOB_EXECUTOR_APPNAME = "oj-job"

Write-Host "Local pressure-test env vars loaded into current session." -ForegroundColor Green
