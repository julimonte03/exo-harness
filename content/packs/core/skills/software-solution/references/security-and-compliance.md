# Security and compliance

Steps 2 and 9 of `software-solution`: the security baseline every solution gets, and the controls a regulated environment adds. The architecture says how each control is supported and what evidence it produces; it never claims that the solution is compliant: the organization's compliance function decides that.

## Baseline (every solution)

| Area | The architecture says |
|---|---|
| Identity of people | How users and staff sign in (the organization's identity provider, single sign-on), and how sessions end |
| Identity of services | How components prove who they are to each other (workload identities, mutual TLS, signed tokens), with no shared static credentials |
| Authorization | The model (roles, attributes, ownership checks), where it is enforced (on the server, at every entry point), and deny by default |
| Secrets | Where they live (a secret manager or the platform's store), who can read them, how they rotate; never in code, images, logs or tickets |
| Encryption | In transit on every hop (TLS), at rest for stores with Internal data or above; who manages the keys |
| Input and output | Validation at every boundary, encoding for each output context, limits on sizes and rates |
| Audit logging | Security events (sign-in, permission changes, access to Restricted data, admin actions) logged with who, what and when, and no secrets or personal data in the log text |
| Network | Which components are reachable from where; public entry points behind the organization's edge protection |
| Supply chain | Dependencies from expected sources, pinned, scanned; images and artifacts built in the pipeline |
| Data protection | Each data flow labeled with its level on the scale of `.exo/shared/data-protection.md`, section A (Public, Internal, Restricted, Critical). Secrets travel only from the secret store to the component that uses them; every Restricted flow that crosses a trust boundary is flagged for the threat model and the person's decision. That contract's matrix and waivers govern what the agent may copy, not the system's runtime flows |

## Threats

- Inside a change from Tier 3, `threat-modeling` (pack `security`) is Required in design and writes the `threat_model` gate. Give it the context view, the trust boundaries and the data flows of step 4; its threats and mitigations go to Risks & Mitigations through `sdd-design`.
- Outside a change, or when that skill is not installed (say `security/threat-modeling not installed — applying inline criteria`): for each entry point and trust boundary, list the threats that apply (STRIDE: spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege) and the mitigation of each.

## Regulated environments

Add these controls when step 2 decided the regime is regulated. For each, write how the design supports it and what evidence it leaves; the organization's own requirements may add or change items.

| Control | How the design supports it | Evidence it produces |
|---|---|---|
| Traceability | Every requirement maps to components and tests; every change to production comes from a reviewed change in version control | Living specs, the change records, pull requests with approvals |
| Segregation of duties | The person who writes a change is not the one who approves or deploys it; production access is separate from development access | Branch protection with required approvers, deployment approvals, access lists |
| Audit trail | Business-relevant actions (approvals, refunds, data exports, permission changes) recorded as append-only events with who, what, when and from where | The audit log store, its retention and its access controls |
| Change control | Production changes go through the pipeline, with approvals where the organization requires them, and can be rolled back | Pipeline history, approvals, release notes |
| Access reviews | Roles are defined per component; access is granted by role and reviewed periodically | The role model, the review records |
| Data residency | Stores, backups, logs and vendors stay in the allowed regions | The deployment configuration, vendor agreements |
| Retention and deletion | Each data set has a retention period with its source, and a deletion process that covers copies and backups | The retention table, deletion job logs |
| Third parties | Each vendor that receives Internal or Restricted data has an agreement and an assessment | The vendor list with agreement references |
| Resilience obligations | Recovery time and recovery point objectives agreed with the business, tested | The DR plan, restore test records |
| Incident handling | Security and data incidents detected, escalated and reported as the organization's process says | Alerts, the incident runbook, incident records |

Questions to settle with the person, as open questions with a default when nobody answers:

1. Which obligations apply, according to the organization's compliance function?
2. Which approvals does a production change need?
3. How long must audit records be kept, and who may read them?
4. In which regions may each data set be stored and processed?
5. Which vendors are already approved for which data levels?

## Non-regulated environments

The baseline is enough, scaled to the data:

- **Only Public and Internal data:** the baseline; audit logging for admin actions.
- **Restricted data:** the baseline, plus minimization, retention with deletion, access logged for Restricted reads, and the flows to vendors checked.
- Keep the design ready to add regulated controls (an append-only audit log, role-based access) when the business may grow into a regulated market; say so as an assumption, not as scope.

## Wording

| Avoid | Write |
|---|---|
| "The solution is compliant with <regulation>" | "The design supports <control>; evidence: <what>. Compliance is confirmed by the organization's compliance function" |
| "Secure by design" | The specific controls and where they are enforced |
| "Data is anonymized" (when it is only masked or pseudonymized) | Exactly what is done: "names replaced by a random ID; the mapping table stays in the returns store" |
