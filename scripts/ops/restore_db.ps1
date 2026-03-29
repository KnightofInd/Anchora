param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$DatabaseUrl = $env:DATABASE_URL
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file not found: $BackupFile"
}

if (-not $DatabaseUrl) {
    Write-Error "DATABASE_URL is not set. Pass -DatabaseUrl or set env:DATABASE_URL."
}

if (-not (Get-Command pg_restore -ErrorAction SilentlyContinue)) {
    Write-Error "pg_restore is not installed or not on PATH. Install PostgreSQL client tools."
}

$normalizedUrl = $DatabaseUrl -replace "^postgresql\+asyncpg://", "postgresql://"

Write-Warning "This operation will overwrite objects in target database."
$confirm = Read-Host "Type RESTORE to continue"
if ($confirm -ne "RESTORE") {
    Write-Host "Restore cancelled."
    exit 1
}

Write-Host "Starting database restore from $BackupFile ..."
pg_restore --clean --if-exists --no-owner --dbname "$normalizedUrl" "$BackupFile"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Database restore failed."
}

Write-Host "Restore completed successfully."
