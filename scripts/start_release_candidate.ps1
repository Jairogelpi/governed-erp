$ErrorActionPreference = "Stop"

$HostName = if ($env:HOST) { $env:HOST } else { "0.0.0.0" }
$Port = if ($env:PORT) { $env:PORT } else { "8000" }

if (-not $env:ERPGUARD_DATABASE_URL) {
    $env:ERPGUARD_DATABASE_URL = "sqlite:///./erpguard_release_candidate.db"
}
if (-not $env:ALLOW_GENERIC_REAL_ODOO_WRITES) {
    $env:ALLOW_GENERIC_REAL_ODOO_WRITES = "false"
}
if (-not $env:ALLOW_R3_R4_REAL_WRITES) {
    $env:ALLOW_R3_R4_REAL_WRITES = "false"
}

@'
from erpguard.db.session import init_db

init_db()
print("Database initialized for ERPGuard release candidate.")
'@ | python -

Write-Host "Starting ERPGuard v0.12.0-rc1 on ${HostName}:${Port}"
Write-Host "Health: http://127.0.0.1:${Port}/v1/release/health"
uvicorn apps.api.main:app --host $HostName --port $Port
