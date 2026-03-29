# Anchora Disaster Recovery Runbook

## Scope
This runbook defines recovery steps for Anchora production services and aligns to policy objectives:
- Tier-1 RTO: <= 4 hours
- Tier-1 RPO: <= 1 hour

## Preconditions
- On-call incident commander assigned
- Latest database backup artifact available
- Access to infrastructure, Supabase, and deployment platform
- Communication bridge opened for responders

## Severity Mapping
- P1: Full production outage or data integrity event
- P2: Major degradation with partial unavailability

## Recovery Workflow
1. Declare incident and assign roles:
- Incident Commander
- Tech Lead
- Comms Lead
- Scribe

2. Stabilize and contain:
- Stop automated deploy pipelines
- Freeze schema changes
- Capture current system state and timestamps

3. Validate backup set:
- Confirm latest successful backup timestamp
- Confirm backup integrity via restore test checksum report
- Confirm RPO window is acceptable

4. Restore database:
- Use scripts/ops/restore_db.ps1 with approved backup artifact
- Apply schema migration head check if required
- Verify connectivity and key table counts

5. Rehydrate services:
- Restart API service
- Validate health endpoint and auth flow
- Validate critical journeys: decisions, workflows, audit, knowledge

6. Business validation:
- Confirm P95 latency and error-rate thresholds
- Confirm last known good transactions present
- Confirm no unauthorized data drift

7. Return to service:
- Incident Commander authorizes production reopen
- Comms Lead sends status update
- Start post-incident review timer

## Validation Checklist
- /api/health returns ok
- Login works for admin and analyst roles
- New decision creation works
- Workflow start/approve path works
- Audit trace endpoint returns expected lifecycle logs

## Evidence to Capture
- Backup file name and timestamp
- Restore start/end times
- RTO achieved
- RPO achieved
- Failing and passing checks
- Corrective actions logged

## Post-Incident Activities
- PIR completed within 10 business days
- Action items tracked with owner and due date
- Playbook updates merged into repository
