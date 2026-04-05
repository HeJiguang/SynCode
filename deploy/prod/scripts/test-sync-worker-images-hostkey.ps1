$ErrorActionPreference = "Stop"

$scriptPath = "deploy/prod/scripts/sync-worker-images.sh"
$content = Get-Content $scriptPath -Raw

function Require-Pattern {
    param(
        [string]$Pattern,
        [string]$Message
    )

    if (-not $content.Contains($Pattern)) {
        throw $Message
    }
}

Require-Pattern 'known_hosts_file="$(mktemp "${TMPDIR:-/tmp}/onlineoj-worker-known-hosts.XXXXXX")"' `
    "missing temporary known_hosts file setup"
Require-Pattern '-o UserKnownHostsFile="$known_hosts_file"' `
    "missing explicit user known_hosts configuration"
Require-Pattern '-o GlobalKnownHostsFile=/dev/null' `
    "missing global known_hosts isolation"
Require-Pattern '-o StrictHostKeyChecking=yes' `
    "missing strict host key enforcement after keyscan"
Require-Pattern 'ssh-keyscan -H -p "$WORKER_SSH_PORT" "$WORKER_SSH_HOST" > "$known_hosts_file" 2>/dev/null' `
    "missing worker host key preseed step"
Require-Pattern 'ssh "${ssh_opts[@]}" "${WORKER_SSH_USER}@${WORKER_SSH_HOST}" "cat > ''${remote_archive}''" < "$archive"' `
    "missing ssh stream transport for worker image archive"
