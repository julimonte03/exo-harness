# Auditing the ADR folder

The checks of `architecture-decision-record` when it audits a folder, with the rule ID for the Rule column of the findings table. The audit is read-only: it lists, reads and searches, and writes nothing.

## 1. Inventory

List every `.md` in the ADR folder, and for each one note:
- the number and the slug of the file name;
- the title;
- the status line: `Status:` in the header, or the folder's own form (a `Status` bullet, a `## Status` section);
- the sections it has;
- the numbers it supersedes or is superseded by.

Files that are not ADRs (a README, an index, a template) are skipped. Say which ones you skipped.

## 2. The checks

| Rule | Finding | Severity |
|---|---|---|
| `ADR-STATUS` | No status line | Medium |
| `ADR-STATUS` | A status outside `Proposed`, `Accepted`, `Superseded by NNNN` and `Recovered`, when the folder has no vocabulary of its own | Low |
| `ADR-STATUS` | `Proposed` for a decision the code already follows | Low |
| `ADR-CONFLICT` | Two `Accepted` ADRs that decide opposite things on the same topic, without a supersede link | High |
| `ADR-CODE` | An `Accepted` ADR the code no longer follows | High for security, data or a public API; Medium otherwise |
| `ADR-LINK` | `Superseded by NNNN` pointing to an ADR that does not exist | Medium |
| `ADR-LINK` | A `Supersedes:` whose old ADR is still `Accepted`, or a chain of supersedes that loops | Medium |
| `ADR-MISSING` | A decision the code shows and no ADR explains | Medium; Low for a choice that is easy to reverse |
| `ADR-FORM` | Two ADRs with the same number | Medium |
| `ADR-FORM` | A name that is not `NNNN-<slug>.md` (or the folder's own scheme), a title number that differs from the file's, a missing section | Low |
| `ADR-RECOVERED` | A recovered ADR without `Confidence:` or `Source:`, or a claim of it without an evidence marker | Medium |

- **The folder's own vocabulary counts.** When its ADRs use other statuses consistently (`Deprecated`, or a status in another language), map them and report only the ADRs outside that vocabulary.
- **Contradictions:** group the ADRs by topic (the title and the Decision) and compare the `Accepted` ones in each group. A later ADR on the same topic that does not say `Supersedes:` is the usual cause.
- **Against the code:** for each `Accepted` ADR, find the code its Decision governs and check that it still holds, with `path:line` for what contradicts it. The fix is either a new ADR that supersedes it or a change to the code: the person decides, and a code change is an SDD change.

## 3. Decisions without an ADR

Look for what the project decided and cannot reverse cheaply:

| Decision | Where it shows |
|---|---|
| Language and runtime | Manifests, version files (`.python-version`, `.nvmrc`), Dockerfiles |
| Frameworks | Dependencies in the manifests |
| Data stores and their schema | Database drivers, migrations, compose files |
| Messaging and external services | Clients of queues, brokers and third-party APIs |
| API style and contracts | OpenAPI, proto and GraphQL files; the routing layer |
| Authentication and authorization | Auth libraries, middleware, token handling |
| Deployment and infrastructure | Dockerfiles, infrastructure as code, CI and release workflows |
| Architecture style | The module layout, layering rules, the dependencies between modules |

- **In a project adopted with reverse engineering,** start from `.exo/discovery/inventory.json` (`frameworks`, `manifests`, `migrations`, `api_contracts`, `infrastructure`, `ci`) and `.exo/discovery/module-graph.mmd`, and from the as-is specs. Never rebuild them by hand.
- **Otherwise,** read the Stack of `.exo/context.md` first, then the files of the table.
- **Each decision found** is a finding with the evidence of where it shows. The suggested fix is a new ADR: `Recovered` during an adoption, `Proposed` otherwise.

## 4. The report

~~~markdown
| Severity | File:line | Finding | Rule | Suggestion |
|---|---|---|---|---|
| High | docs/adr/0004-rest-only.md:9 | Accepted "REST only", but src/api/grpc_server.py:12 serves gRPC | ADR-CODE | A new ADR that supersedes 0004, or a change that removes gRPC |
| Medium | docs/adr/0006-cache.md:1 | No status line | ADR-STATUS | Add `Status:` with the person's answer |
| Medium | pyproject.toml:14 | Celery with Redis runs the background jobs, and no ADR explains it | ADR-MISSING | Propose an ADR for the job queue |
| Low | docs/adr/0002-logging.md:1 | No Alternatives section | ADR-FORM | Add the alternatives, or say that there were none |
~~~

- `File:line` is relative to the repository root.
- With no findings, a single row that says "No findings".
- After the table, list the fixes you can draft (new ADRs and status changes) and ask which ones to write. Each one is written only when the person approves its text.
