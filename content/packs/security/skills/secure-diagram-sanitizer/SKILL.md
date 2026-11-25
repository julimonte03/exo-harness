---
name: secure-diagram-sanitizer
description: >-
  Sanitizes diagrams and technical documents before they are shared outside
  the team: finds internal URLs and hostnames, IP addresses, ports, secrets,
  personal data, and the names of repositories, environments and cloud
  accounts, in the visible text and in what a viewer can still reach (source
  comments, alt text, notes, links, hidden layers, metadata), and replaces
  each with a consistent generic label. Never modifies the original: writes
  the sanitized copy apart, and gives the table of replacements only to the
  person who asked, never inside the shared piece. Applies the data
  protection contract. Use it before a diagram, a design document or a slide
  leaves the team: to a vendor, a partner, a client, a public page, a talk or
  an external tool. Triggers: "sanitize this diagram", "clean this before
  sharing", "remove internal hostnames", "redact this architecture", "make
  this safe to share externally", "anonymize the diagram", "strip the IPs
  from this doc".
metadata:
  exo-pack: security
  exo-execution: inline
  exo-permissions: write-specs
---

# secure-diagram-sanitizer

A diagram that leaves the team takes the network with it: hostnames, address ranges, account IDs and repository names are a map for an attacker, and personal data in a sample is a leak. This skill produces a copy that tells the same story with generic labels, and leaves the original untouched.

## Result

- **A sanitized copy,** written apart from the original, in the same format so it still renders. Name it for its content (`network-overview.shared.drawio`), never with a name or a folder that carries an identifier of the original, and ask where it goes: next to the original only when the person says so (`references/hidden-content.md`, Around the file). Inside an SDD change, a copy in the repository is a project document, written with the person's approval once the plan lists it (design.md, Modules / Files, in Tier 3; the Scope of proposal.md in Tier 1 and 2), so verify does not count it as drift (`.exo/shared/sdd-phase-common.md`, section C). The original is only read.
- **The replacement table,** in your answer to the person who asked, and nowhere else: each label, its kind, where it was in the original, and the original value only when it is Internal (section The replacement table).
- **Residual risks:** what text replacement cannot fix (an image with text in its pixels, a topology that identifies the organization by itself), and what you could not check.

## When

- Before a diagram, a design document, an architecture page or a slide goes outside the team: a vendor, a partner, a client, an auditor, a public repository or page, a conference talk, an external chat or AI tool.
- When the diagram skills of the `design` pack (`diagram-design`, `architecture-diagram-designer`, `uml-visual-designer`) or `executive-visual-quality-gate` hand a piece over for sharing.
- **Not for:** cleaning logs, tickets or data before they reach a prompt (skill:prompt-hygiene); deciding the level of data in a change (skill:data-classification); secrets committed in code (they are a finding of skill:security-code-review, and the credential must be rotated).

The rules come from `.exo/shared/data-protection.md`: the levels (section A), the destinations (section B) and the matrix (section C). Read it first.

## The destination decides

| Destination | Remove |
|---|---|
| Inside the organization: the same team or other teams | Critical (secrets) and Restricted (personal data). Only the Internal identifiers stay |
| Outside the organization: vendors, clients, partners, the public, external tools | Critical, Restricted, and every Internal identifier of the categories below |

Critical never stays. Restricted stays only where a waiver in force covers the path the copy goes to (`.exo/shared/data-protection.md`, section E). When the person does not say where it goes, ask once; without an answer, assume outside the organization.

## What to look for

| Category | Examples | Level | Replace with |
|---|---|---|---|
| Secrets | API keys, tokens, passwords, connection strings with credentials, signed links, private keys, cookies | Critical | Nothing: remove it and the line that carried it; say "removed" in the table |
| Personal data | Names of customers or employees, emails, phone numbers, national IDs, account and card numbers, addresses | Restricted | A role (`Support agent`), `Person A`, `user1@example.com`, `<national-id>`, `****1234` |
| Internal URLs and hostnames | Intranet sites, service hosts under the organization's domains, `*.internal`, `*.corp`, `*.local`, admin consoles | Internal | `service-a.example.com`, `https://portal-a.example.com` |
| IP addresses and networks | Private ranges, the organization's public addresses, subnets and CIDR blocks, VPN ranges | Internal | Documentation ranges: `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, `2001:db8::/32` |
| Ports | Non-standard ports, management ports, port lists on firewall rules | Internal | The protocol name instead (`HTTPS`, `PostgreSQL`), or nothing |
| Cloud accounts and resources | Account, subscription, tenant and project IDs, resource identifiers, bucket and registry names, key vault names | Internal | `<cloud-account-1>`, `bucket-a`, `<registry>` |
| Repositories and code hosts | Organization and repository names, internal Git URLs, package feeds, file paths that reveal them | Internal | `repo-a`, `<code-host>`, `<package-feed>` |
| Environments and infrastructure | Environment codes, cluster, namespace, server and data center names, region and zone combinations | Internal | The generic role: `production`, `staging`, `cluster-1`, `region-1` |
| Organization identifiers | Ticket IDs, project codenames, customer and tenant names, internal team names | Internal | `TICKET-1`, `Project A`, `Customer A`, `Team A` |
| Exact versions of exposed components | Server and framework versions on an internet-facing element | Internal | The product without its version, for a public destination |

Search patterns for each category, and the cases that patterns miss, are in `references/detectors.md`.

**What stays:** generic, descriptive names that identify no one ("Orders API", "Payment provider", "PostgreSQL"), standard protocols, and the structure of the diagram. Replace names that point to the organization, a customer, a codename, an environment or a person.

## Where hidden text lives

A viewer, or anyone with the file, can reach more than the rendered picture. Check every place, per format, with `references/hidden-content.md`:

- source comments (`%%`, `'`, `//`, HTML comments), including evidence comments such as `[Code] path:line`, which reveal repository paths;
- accessible titles and descriptions, alt text, tooltips, notes and captions;
- link targets and click actions;
- hidden layers, other pages or tabs, hidden slides, speaker notes, comments and tracked changes;
- file names, folder paths, document properties and image metadata;
- embedded images, whose pixels may show text that no search finds.

## Steps

1. **Scope.** The original files, the destination, and where the copy goes, with its name. Ask once for what is missing. Several files shared together are one job: they share one label map.
2. **Read** each original in full. Never edit it, rename it or stage it.
3. **Find.** Search with the patterns of `references/detectors.md`, then read the text line by line: patterns miss names. Cover the hidden places of the format.
4. **Classify** each hit: its level (`.exo/shared/data-protection.md`, section A) and whether the destination allows it (the table above). When in doubt, replace it.
5. **Build the label map.**
   - **Consistent:** the same original value gets the same label everywhere, in every file of the job, so relations survive.
   - **Role-preserving:** a database stays a database (`database-a`), a host stays a host (`service-b.example.com`); numbering follows first appearance.
   - **Unlinkable:** labels never derive from the original (no initials, no hashes, no partial values).
6. **Write the copy** apart, named for its content, where the person said (step 1), with every replacement applied. Remove source comments rather than relabel them, except the style marker (`exo-style:`), which reveals nothing. Remove secrets with their whole line or attribute. Never write the label map into the copy.
7. **Verify** the copy:
   - search it for every original value of the map, exactly; none may remain;
   - run the category patterns again;
   - render it when the project has the renderer, and check that the message still reads: labels consistent, relations intact, the legend still right;
   - for formats you cannot edit as text (slides, PDFs, images), say so: give the person the replacements to make in their editor, or rebuild the piece as source text; install nothing.
8. **Report** in your answer: the path of the copy, the replacement table, the residual risks and what you could not check.

## The replacement table

Only in your answer, for the person who asked. Never in the shared copy, the repository, memory, a PR description, a tracker or a chat; if the person wants to keep it, they keep it themselves in an internal place.

| Level | The Original column shows |
|---|---|
| Critical | Nothing: "removed", with the location. If it looked real, tell the person to rotate it |
| Restricted | Nothing: the location and the kind, or the value masked (`****1234`) |
| Internal | The original value, since the requester is inside the organization |

```markdown
| Label | Kind | Where in the original | Original |
|---|---|---|---|
| service-a.example.com | Internal hostname | architecture.md:14, :22 | orders.<internal-domain> |
| 203.0.113.10 | Private IP address | architecture.md:30 | 10.<…> (load balancer) |
| cluster-1 | Cluster name | architecture.md:41 | <cluster name> |
| Support agent | Person's name | architecture.md:8 | removed: personal data |
| — | Connection string with password | architecture.md:52 (comment) | removed: secret; rotate it if it was real |
```

## Return

```markdown
Sanitized copy: docs/architecture/architecture.shared.md (the original is unchanged).
Destination: an external vendor. Removed: 1 secret, 1 personal name. Replaced: 9 internal identifiers (table below).
Comments removed: 14 evidence comments with repository paths.
Verified: no original value remains in the copy; the diagram renders and its relations are intact.
Residual risks: the screenshot in section 3 shows a hostname in its pixels; replace the image or crop it.
Not checked: the PDF export, which I cannot edit here.
```

Then the replacement table.

## Record

Inside an SDD change, a phase that runs inline records the skill, never the label map (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "secure-diagram-sanitizer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I). Never save the map, the originals or unmasked excerpts in memory.

## Before you finish

- [ ] The original is unchanged; the copy is apart and in the same format.
- [ ] Every category was searched in the visible text and in every hidden place of the format.
- [ ] Labels are consistent across all the files of the job, keep the role, and cannot be traced back to the originals.
- [ ] No original value of the map remains in the copy; no secret remains anywhere in it.
- [ ] The replacement table is only in the answer, with Critical and Restricted values never shown.
- [ ] Residual risks and unchecked parts are stated.
