# Anchora Incident Response Playbook

## Purpose
Operational response guide for security and availability incidents.

## Initial Triage (first 15 minutes)
1. Acknowledge alert and assign Incident Commander.
2. Classify severity (P1/P2/P3/P4).
3. Open timeline log and responder bridge.
4. Preserve forensic data before remediation.

## P1 Critical (target immediate action)
- Examples: ransomware, major breach, outage > 1 hour.
- Actions:
1. Isolate affected systems.
2. Revoke high-risk sessions and rotate exposed credentials.
3. Engage CISO, CTO, Legal, and Comms leads.
4. Start disaster-recovery runbook if service availability is impacted.

## P2 High (target <= 2 hours)
- Examples: confirmed exfiltration or single-system compromise.
- Actions:
1. Contain impacted component.
2. Validate blast radius and affected identities.
3. Begin service restoration plan.
4. Prepare regulatory impact summary for legal review.

## P3 Medium (target <= 4 hours)
- Examples: suspicious activity, blocked intrusion, policy violation.
- Actions:
1. Collect evidence and impacted asset details.
2. Patch or mitigate vulnerability.
3. Add detections to prevent recurrence.

## P4 Low (target <= 24 hours)
- Examples: isolated endpoint issue, low-impact spam burst.
- Actions:
1. Triage and resolve with service team.
2. Log incident for trend analysis.

## Containment Controls
- Disable compromised credentials
- Revoke refresh and access tokens where applicable
- Block known malicious IPs and user-agents
- Freeze vulnerable endpoints when needed

## Recovery Controls
- Restore from known-good backups if integrity is affected
- Validate user journeys and SLO endpoint
- Monitor for reinfection or repeated anomalous traffic

## Communication Rules
- Internal status updates every 30 minutes for P1/P2.
- External communication only through approved comms owners.
- No public statement without executive and legal approval.

## Closure Criteria
- Threat removed or contained
- Systems stable and monitored
- Root cause identified
- Action items tracked with owners
