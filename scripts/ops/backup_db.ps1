param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$OutputDir = "./backups/db"
)

$ErrorActionPreference = "Stop"

if (-not $DatabaseUrl) {
    Write-Error "DATABASE_URL is not set. Pass -DatabaseUrl or set env:DATABASE_URL."
}

if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    Write-Error "pg_dump is not installed or not on PATH. Install PostgreSQL client tools."
}

$normalizedUrl = $DatabaseUrl -replace "^postgresql\+asyncpg://", "postgresql://"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$backupFile = Join-Path $OutputDir "anchora_db_$timestamp.dump"

Write-Host "Starting database backup..."
pg_dump --format=custom --no-owner --file "$backupFile" "$normalizedUrl"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Database backup failed."
}

Write-Host "Backup completed: $backupFile"
