---
name: security-scan-node
description: >-
  Scans a Node.js, JavaScript or TypeScript project, read-only, for vulnerable
  dependencies and insecure code patterns with an open toolchain: the package
  manager's audit (npm, pnpm, yarn, bun), then OSV-Scanner, then OWASP
  dependency-check, with SonarQube or Fortify only when the project already
  has them. Reviews manifest and lockfile changes by hand (missing lockfiles,
  unpinned versions, unexpected registries, install scripts, typosquats),
  cross-checks the sources, and maps each finding to OWASP Top 10:2025 with
  its advisory ID or CWE. Never installs or fixes anything. In SDD verify it
  runs when a dependency or a lockfile changes; its Critical and High findings
  go to Issues Found. Use it when package.json or a lockfile changes, before a
  release, or when someone asks whether a Node project has vulnerable
  dependencies. Triggers: "npm audit", "check our dependencies for
  vulnerabilities", "scan this Node project", "are these packages safe",
  "CVEs in our dependencies", "I added a package".
metadata:
  exo-pack: frontend
  exo-execution: inline
  exo-permissions: read-only
---

# security-scan-node

## Result

- A scan report: the tools that ran and the ones that could not, with their exact commands; the vulnerable dependencies (package, version, fixed version, advisory, exposure, OWASP Top 10:2025 category); the manifest and lockfile problems; the insecure code patterns in the changed files; what was not checked; and a closing line `Scan: complete` or `Scan: partial (<why>)` with the counts per severity.
- In SDD verify: the Critical and High findings, ready for Issues Found of `verify-record.md`, and as rows for the `security_review` gate when the tier has it.
- Nothing installed, upgraded or fixed: the fixes are text for the person.

## When

| Moment | Trigger | What you scan |
|---|---|---|
| verify (`.exo/shared/phase-skill-map.md`, Conditional) | The diff changes a `package.json`, a lockfile or `.npmrc` | The dependency changes and the changed code |
| Before a release, or on request | Someone asks whether the dependencies are safe | The whole dependency tree and the code they name |

- **Lockfiles:** `package-lock.json`, `npm-shrinkwrap.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock` (or the older `bun.lockb`). Find the changes with `git diff --name-only <base>...HEAD`.
- **Not for:** a full security review of the code (skill:security-code-review, pack `security`, or skill:typescript-reviewer for a stack review); Java, Kotlin or Python dependencies (`security-scan-jkp`, pack `java`); upgrading packages, which is code work for the person after the scan.

## Permissions

- **Read-only.** Read files, run read-only git, and run the audit tools the project already has.
- **Never install or fix:** no `npm install`, `npm audit fix`, `pnpm update`, `yarn up`; no `npm install --package-lock-only` (it writes a lockfile); no `npx` of a scanner the project does not have (it downloads it). Suggest them as commands for the person.
- **Network:** the audits send the list of package names and versions to their advisory service (the registry, osv.dev, the NVD mirror), never source code. If the project forbids that (an offline build), run only what works offline and say so.
- **Never copy a secret** you meet in `.npmrc` or config files: point at `path:line` and tell the person to rotate it (`.exo/shared/data-protection.md`).
- **When you cannot run a command** (no tool, no shell permission, no lockfile), say so, give the exact command you would run, and do the manual review in step 4. Never report a result you did not see.

## 1. Know the project

1. **Package manager:** the `packageManager` field in the root `package.json`, else the lockfile. Use that manager's commands only.
2. **Workspaces:** `workspaces` in the root `package.json` or `pnpm-workspace.yaml`. One root lockfile covers them all.
3. **Lockfile:** present and committed? Changed together with the manifests that changed? Without a lockfile, versions are not pinned and the native audits refuse to run: that is a finding (step 4), not a reason to stop.
4. **What ships:** `dependencies` of server packages run in production; whatever the bundler pulls into browser code ships to every visitor; `devDependencies` run on developer and CI machines (still a supply-chain risk, a lower exposure).
5. **Tools present:** `osv-scanner --version`, `dependency-check --version`, a SonarQube setup (`sonar-project.properties`, a CI step), a Fortify setup. Only what answers is available.

## 2. Run the chain

Run the first step that works; when later steps are also available, run them too and cross-check. Commands per package manager and per tool are in `references/toolchain.md`.

| Step | Tool | Example | Runs when |
|---|---|---|---|
| 1 | The package manager's audit | `npm audit --omit=dev --json`, then `npm audit --json` | Always, when there is a lockfile |
| 2 | OSV-Scanner | `osv-scanner scan -r .` | Installed |
| 3 | OWASP dependency-check | `dependency-check --scan . --format JSON --out <temporary folder>` | Installed, with its data already set up |
| Optional | SonarQube, Fortify | The project's existing CI job or CLI | Already configured in the project; never set them up |

- Production first (`--omit=dev`, `--prod`), then the full tree, so the report can tell the exposures apart.
- When no step runs, the manual review of step 4 is the scan, and the closing line says `Scan: partial`.

## 3. Read the results

For each vulnerable package, note: the package and installed version; direct or transitive, and through which direct dependency (`npm explain <package>`, `pnpm why`, `yarn why` when `node_modules` exists, or the lockfile); the advisory IDs (GHSA, CVE, OSV); the source's severity; the first fixed version; and the exposure:

| Exposure | Meaning |
|---|---|
| runtime | A production dependency that server code loads or that ships in the browser bundle |
| build | A tool that runs at build time and shapes what ships (bundler, compiler, codegen) |
| dev | Tests, linters, local tooling |
| unreachable | The vulnerable function or feature is not used: name the evidence (`path:line` of every use) |

## 4. Review the manifests and the lockfile by hand

Always, also when the tools ran: they do not see everything. The checks, with their IDs and signals, are in `references/toolchain.md`, Manual review:

- a manifest changed without its lockfile, or no lockfile at all;
- loose or risky version specs: `*`, `latest`, open ranges, git URLs, tarball URLs, `file:` outside the repo;
- `resolved` URLs to an unexpected host or over `http://`; an `integrity` value changed for the same version;
- new install scripts (`preinstall`, `install`, `postinstall`; `hasInstallScript` in `package-lock.json`);
- names one typo away from a popular package, internal scopes resolved from the public registry, `.npmrc` registry or `strict-ssl` changes;
- `overrides` or `resolutions` that pin or downgrade a package;
- a package moved from `devDependencies` to `dependencies`.

A version you recognize as vulnerable without a tool result is reported as `Unconfirmed:`, with the advisory you remember and the command that would confirm it. Never present memory as a scan result.

## 5. Insecure code patterns

In the files the diff changes (or the files the person names), look for the Node and browser patterns of `references/code-patterns.md`: injection into queries, commands and HTML; prototype pollution through deep merges of request data; unsafe deserialization; SSRF and path traversal; secrets in code or client bundles; weak randomness and hashing; missing authorization; errors that fail open. Pay most attention to code that uses the dependency that changed. This is a pattern scan, not a full review: when the diff needs one, say which skill does it (skill:security-code-review or skill:typescript-reviewer).

## 6. Cross-check and rate

- **Deduplicate** by advisory ID and its aliases (a GHSA and its CVE are one finding); list every source that reported it.
- **Severity:** the source's rating from the CVSS base score (Critical 9.0 and up, High 7.0 to 8.9, Medium 4.0 to 6.9, Low below 4.0). When sources disagree, keep the higher and say so. Exposure is a separate column: never lower a severity because a package is dev-only or looks unreachable; the person decides with that information.
- **Manual and pattern findings** use the severities in `references/toolchain.md` and `references/code-patterns.md`.
- **Map** each finding to its CWE and, from the CWE, to its OWASP Top 10:2025 category with its year, through `.exo/shared/owasp-2025.md`, the table the Java scan and the stack reviewers use too: a vulnerable component is `A03:2025` (Software Supply Chain Failures) with `CWE-1395`.
- **Fix as text:** the first fixed version and whether it is a major upgrade; for transitive packages, the direct dependency to upgrade or an `overrides` entry, with its risk.

## Return

```markdown
# Dependency scan: node-shop (origin/main...HEAD)

Scope: packages/api/package.json changed (lodash added). No lockfile in the repository.
Tools: npm audit --omit=dev: not run (npm audit needs package-lock.json); osv-scanner: not installed; dependency-check: not installed; SonarQube, Fortify: not configured.

## Dependencies

| ID | Severity | Package | Installed, fixed | Advisory | Exposure | OWASP 2025 | Source |
|---|---|---|---|---|---|---|---|
| DEP-1 | High | lodash (direct, packages/api) | 4.17.15, 4.17.21 | Unconfirmed: CVE-2021-23337, command injection through `template` | runtime | A03:2025, CWE-1395 | manual; confirm with `npm audit --omit=dev` |

## Manifests and lockfile

| ID | Severity | path:line | Finding | OWASP 2025 |
|---|---|---|---|---|
| LOCK-1 | Medium | package.json:1 | No lockfile: every install resolves new versions, and no audit can run | A03:2025, CWE-1357 |

## Code patterns

| ID | Severity | path:line | Finding | OWASP 2025 |
|---|---|---|---|---|
| PAT-1 | High | packages/api/src/routes/preferences.js:12 | The request body is deep-merged into an object with lodash `merge`, so a `__proto__` key can pollute prototypes | A08:2025, CWE-1321 |

## Not checked

Transitive dependencies (no lockfile); install scripts of transitive packages.

## Fixes (for the person)

1. Pin lodash to 4.17.21 or later, or drop it for a native alternative.
2. Commit a lockfile (`npm install --package-lock-only` writes it), then run `npm audit --omit=dev`.

Scan: partial (no lockfile, no scanner installed). Critical 0, High 2, Medium 1, Low 0.
```

- IDs: `DEP-n` for vulnerable packages, `LOCK-n` for manifest and lockfile findings, `PAT-n` for code patterns; unique in the report.
- `Scan: complete` only when a tool covered the full tree from a lockfile; otherwise `Scan: partial (<why>)`.

## In an SDD change

- **Verify:** it runs where the verify runs (`sdd-verifier`, read-only, or the session that runs the verify). Every Critical and High finding goes to Issues Found of `verify-record.md` (severity, `path:line` or package, impact, fix), which `sdd-verify` writes; dev-only ones are marked as such, and the person decides.
- **The `security_review` gate,** when the tier has it, is written by `security-code-review` (pack `security`). Give the same Critical and High findings as rows in the gate's Findings format (`| High | packages/api/package.json:14 | DEP-1: lodash 4.17.15 ... | A03:2025, CWE-1395 |`) so that whoever writes the gate includes them. This skill writes no gate and no file.
- **A missing tool** is not a degradation of this skill: it is a partial scan, said in the report and in the envelope notes. When this skill itself is not installed, the verify applies the inline criteria of `.exo/shared/phase-skill-map.md`.

## Record

Inline, before the phase envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "security-scan-node", "type": "skill", "activation": "auto", "resolution": "fallback-registry", "note": "partial: no lockfile"}'
exo change record <change> --add skills_used '"security-scan-node"'
exo change record <change> --add capabilities_used '{"name": "npm audit", "type": "command", "activation": "auto"}'
```

Record each audit tool that ran as a `command`. Findings the person decides not to fix go to `dismissed_followups` with their reason, recorded by the orchestrator; never dismiss one yourself. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] You identified the package manager, the workspaces, the lockfile and what ships.
- [ ] Each tool of the chain either ran with its exact command or is listed with why it could not.
- [ ] The manual review of manifests and lockfile was done, whatever the tools said.
- [ ] Every finding has a severity, an exposure, an advisory ID or CWE and its OWASP Top 10:2025 category with its year from `.exo/shared/owasp-2025.md`; recalled versions are marked `Unconfirmed:`.
- [ ] Duplicates across sources are merged; no severity was lowered for exposure.
- [ ] Nothing was installed, upgraded, fixed or written; no secret was copied.
- [ ] The report ends with `Scan: complete` or `Scan: partial (<why>)` and the counts.
