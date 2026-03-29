# Backup and Restore Drill Checklist

## Drill Metadata
- Drill date:
- Environment:
- Incident Commander:
- Database artifact:

## Pre-Drill
- [ ] Confirm latest backup exists and is readable
- [ ] Confirm restore target environment is isolated
- [ ] Confirm rollback snapshot exists
- [ ] Confirm all required credentials are available securely

## Backup Validation
- [ ] Run scripts/ops/backup_db.ps1
- [ ] Capture backup filename and checksum
- [ ] Record backup duration

## Restore Validation
- [ ] Run scripts/ops/restore_db.ps1 against drill target
- [ ] Verify migration compatibility
- [ ] Verify key table row counts
- [ ] Verify API health endpoint response

## Functional Validation
- [ ] Login flow works
- [ ] Decision creation works
- [ ] Workflow transitions work
- [ ] Audit trace endpoint works

## SLO Validation
- [ ] Recovery completed within RTO target
- [ ] Data freshness within RPO target

## Post-Drill
- [ ] Capture findings and corrective actions
- [ ] Create follow-up tickets for gaps
- [ ] Update runbooks if needed
