# Anchora

Anchora is an AI-assisted decision governance platform with policy enforcement,
workflow approvals, traceability, and auditability.

## Phase 6 Operations Readiness

This repository includes baseline production-readiness artifacts for secrets
hygiene, disaster recovery, and incident operations.

### Secrets and Environment

- `backend/.env` is sanitized and should not contain live credentials.
- Use `backend/.env.example` as the template for local setup.
- For production, prefer mounted secret files:
	- `SECRET_KEY_FILE`
	- `SUPABASE_SERVICE_KEY_FILE`
	- `GEMINI_API_KEY_FILE`

### Backup and Restore Scripts

PowerShell scripts are available in `scripts/ops`:

- `scripts/ops/backup_db.ps1`
- `scripts/ops/restore_db.ps1`

Examples:

```powershell
# Backup using DATABASE_URL from environment
./scripts/ops/backup_db.ps1

# Backup with explicit target
./scripts/ops/backup_db.ps1 -DatabaseUrl "postgresql://..." -OutputDir "./backups/db"

# Restore from a specific backup file
./scripts/ops/restore_db.ps1 -BackupFile "./backups/db/anchora_db_YYYYMMDD_HHMMSS.dump" -DatabaseUrl "postgresql://..."
```

Note: `pg_dump` and `pg_restore` must be installed and on `PATH`.

### Runbooks and Playbooks

- DR runbook: `ops/runbooks/disaster-recovery-runbook.md`
- Incident response: `ops/playbooks/incident-response-playbook.md`
- Escalation matrix: `ops/playbooks/incident-escalation-matrix.md`
- Drill checklist: `ops/dr/backup-restore-drill-checklist.md`
- Drill evidence template: `ops/dr/drill-evidence-log-template.md`

### Backup Artifact Hygiene

Backup artifacts are ignored by git via `.gitignore` entries for:

- `backups/`
- `*.dump`
- `*.backup`
- `*.sql.gz`