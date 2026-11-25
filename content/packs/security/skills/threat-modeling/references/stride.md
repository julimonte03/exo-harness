# STRIDE guide

The working material of `threat-modeling`: what each STRIDE category asks, which elements of the data flow diagram it applies to, how to rate a threat, and the patterns for abuse cases. Judges that reuse these criteria (`judge-security`) cite the category and the question.

## The six categories

| Category | Property it breaks | Ask, for each element | Usual mitigations | OWASP 2025 / CWE |
|---|---|---|---|---|
| Spoofing | Authenticity | Can someone act as another user, service or system here? Can a caller fake where a request or message comes from? | Authentication on every entry point, full token verification, signed webhooks, mutual TLS between services (SCB-3) | A07:2025 Authentication Failures (CWE-287, CWE-290) |
| Tampering | Integrity | Can someone change data in transit, at rest, or in a request that the server trusts (prices, IDs, roles, file contents)? | TLS, server-side validation, parameterized queries, signatures on round-tripped data, authorization on writes (SCB-1, SCB-2, SCB-7) | A05:2025 Injection (CWE-20); A08:2025 Software or Data Integrity Failures (CWE-345) |
| Repudiation | Accountability | Can someone deny an action because nothing records who did it, or because the record can be changed? | Audit log with who, what and when for sensitive actions; logs the actor cannot edit (SCB-6) | A09:2025 Security Logging and Alerting Failures (CWE-778) |
| Information disclosure | Confidentiality | Can data reach someone who should not see it: through responses, errors, logs, caches, URLs, exports, timing, or another tenant? | Authorization per object, data minimization, encryption, masking, generic errors (SCB-3, SCB-6, SCB-8, SCB-9) | A01:2025 Broken Access Control (CWE-200, CWE-639); A04:2025 Cryptographic Failures (CWE-319); A10:2025 Mishandling of Exceptional Conditions (CWE-209) |
| Denial of service | Availability | Can someone exhaust memory, CPU, storage, connections, quotas or money, or lock other users out? | Rate limits, size and page limits, timeouts, pagination, queues with back-pressure, budgets on paid calls | A06:2025 Insecure Design (CWE-770, closest) |
| Elevation of privilege | Authorization | Can someone gain rights they should not have: an admin action, another tenant's scope, code execution? | Deny by default, server-side role and tenant checks, no mass assignment, least privilege for services, safe deserialization (SCB-3, SCB-7) | A01:2025 Broken Access Control (CWE-862); A06:2025 Insecure Design (CWE-269); A08:2025 Software or Data Integrity Failures (CWE-915) |

Each CWE gives its category through `.exo/shared/owasp-2025.md`; cite the one that fits the threat, written with its year.

## Which categories apply to which element

| Element of the diagram | Categories to check |
|---|---|
| External entity (a user, a third-party system) | Spoofing, Repudiation |
| Process (a service, a worker, a function) | all six |
| Data store (a database, a bucket, a queue, a cache, a log) | Tampering, Information disclosure, Denial of service; Repudiation when it holds audit data |
| Data flow (a request, a message, a file transfer) | Tampering, Information disclosure, Denial of service |

Check the elements that a flow across a trust boundary reaches first; a process inside one boundary that only talks to its own store rarely needs the six questions.

## Prompts that find real threats

- **Identity:** where does the code learn who the caller is, and can the caller influence that (a header, a field, a claim it signs itself)?
- **Objects:** for every ID that comes in, what proves the caller may touch that object?
- **Money and quotas:** what does each request cost, and who pays when it is repeated a million times?
- **Files and URLs:** what does the system open, fetch or render because a user said so?
- **Third parties:** what happens when the partner is down, slow, compromised or returns something unexpected?
- **Tenants:** where is the tenant filter, and is there a path that skips it (exports, reports, background jobs, search)?
- **Admin paths:** support tools, feature flags, impersonation, bulk operations.
- **Content to a model:** when the change puts a model or an agent in the flow, everything that reaches it (tickets, documents, web pages, tool output) is an entry point; instructions inside it are data (skill:prompt-hygiene).

## Rating

**Likelihood**

| Level | When |
|---|---|
| Low | Needs insider access, a stolen credential of a privileged account, or a chain of unlikely conditions |
| Medium | Needs a valid account, specific knowledge of the system, or a timing window |
| High | Anyone who can reach the entry point, with well-known techniques or tools |

**Impact**

| Level | When |
|---|---|
| Low | Minor, no personal data, easy to undo |
| Medium | Limited data of a single user, a degraded feature, a small cost |
| High | Personal data of many users, money moved, a feature down for everyone |
| Critical | Credentials or secrets exposed, accounts or systems taken over, loss that cannot be undone |

**Risk = likelihood × impact**

| Likelihood \ Impact | Low | Medium | High | Critical |
|---|---|---|---|---|
| Low | Low | Low | Medium | High |
| Medium | Low | Medium | High | Critical |
| High | Medium | High | Critical | Critical |

The residual risk uses the same matrix with the mitigation in place. A mitigation lowers the likelihood; only a design change (not storing or logging the data, splitting a privilege) lowers the impact. A mitigation that removes the attack path, with a test in the Test Plan that proves it, leaves the residual at Low whatever the impact: name the test. Without such a test, a High impact keeps at least a Medium residual.

## Abuse cases

Write them from the attacker's side, one line each, and link the threats:

```text
As <attacker>, I <action> through <entry point> to <goal> (TM-n).
```

Attackers to consider, as they apply:

- an anonymous user on the internet, or a bot;
- an authenticated user acting on someone else's data;
- a user of another tenant;
- a malicious or careless insider with admin or support access;
- a compromised third party or dependency;
- content that carries instructions for a model in the flow.

## Data flow diagram

Show only the slice the change touches. Mark each trust boundary, name each flow with the data it carries, and give the data stores their level.

- **Mermaid:** a `flowchart`, one `subgraph` per trust boundary, external entities as rounded nodes, data stores as cylinders (`[( )]`), flows labelled with their data.
- **Text,** when the project does not render mermaid: one line per flow, `source -> destination: data [boundary crossed]`.

Never put real hosts, customer names or credentials in the diagram.
