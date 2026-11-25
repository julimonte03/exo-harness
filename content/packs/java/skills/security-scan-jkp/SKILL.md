---
name: security-scan-jkp
description: >-
  Security scan for Java, Kotlin and Python projects, read-only: detects the
  build (Maven, Gradle, pip, Poetry, uv), audits the dependencies through an
  open chain (the build's OWASP dependency-check plugin or pip-audit, then
  OSV-Scanner, then the dependency-check CLI; SonarQube or Fortify only when
  the project already uses them), searches the code for insecure patterns,
  cross-checks the findings, and reports each one with severity, location,
  CVE or CWE and its OWASP Top 10:2025 category. Never installs a tool or
  changes the build. Conditional in the SDD verify phase when a dependency or
  a lockfile changes. Use it when a pom.xml, build.gradle, requirements or
  lockfile changes, or when asked whether dependencies are vulnerable.
  Triggers: "scan dependencies", "check for CVEs", "vulnerable
  dependencies", "security scan", "dependency-check", "pip-audit", "OSV",
  "is this library version safe", "are any of these dependencies
  vulnerable".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-only
---

# security-scan-jkp

## Result

A scan report, in the same shape as the Node scan of the `frontend` pack:

1. **Tools:** each step of the chain with its exact command and outcome: ran, not available, or not run (and why).
2. **Dependencies** (`DEP-n`): package, version, advisory (CVE or GHSA), severity, fixed version, direct or transitive (and through what), exposure, and the tools that confirm it.
3. **Manifests and lockfiles** (`LOCK-n`): versions pinned against the BOM, unpinned or dynamic versions, new repositories.
4. **Code patterns** (`PAT-n`): insecure patterns with `path:line` and CWE.
5. Every finding with its OWASP Top 10:2025 category; the Critical and High ones ready for Issues Found; and a closing line `Scan: complete` or `Scan: partial (<why>)` with the counts per severity.

You change nothing: no edits to the build, no upgrades, no installs.

## When

- **SDD verify, Conditional** (`.exo/shared/phase-skill-map.md`): the diff changes a dependency manifest or a lockfile: `pom.xml`, `build.gradle(.kts)`, `settings.gradle(.kts)`, `gradle/libs.versions.toml`, `gradle.lockfile`, `requirements*.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock`, `pdm.lock`, `Pipfile.lock`.
- **On request:** "are our dependencies vulnerable", before a release, after an advisory.
- **Not for:** Node projects (`security-scan-node`, pack `frontend`); a full security review of the code of a diff (skill:security-code-review, which uses this report for its dependency check SCR-DEP-2).

## Permissions and network

- Read-only. Run only scanners the project already has: a plugin declared in the build, or a tool already on the path. Never add a plugin, never install a tool, never change a version.
- **Nothing that installs or builds packages.** `pip-audit -r <requirements>` resolves the requirements with pip in a temporary virtual environment: it downloads the packages and can run the build of a source distribution, which is running third-party code. Use it only as step 3 says.
- Scanners download advisory data (NVD, OSV, PyPI) and OSV-Scanner sends package names and versions, never code. Run them where the project already runs them (CI) or where the person allows network access. Without network, the step is `not run`.
- SonarQube and Fortify analyses upload code to their server: use them only when the project already does (a `sonar-project.properties`, a Sonar or Fortify plugin, a CI step), preferably by reading the result its CI already produced. They are never required.
- Never copy a secret into the report. A hard-coded credential is a finding at its `path:line`, without the value (`.exo/shared/data-protection.md`).

## 1. Detect the project

| Signal | Ecosystem | Manifests to scan |
|---|---|---|
| `pom.xml`, `mvnw` | Maven (Java, Kotlin) | every `pom.xml` of the reactor |
| `build.gradle(.kts)`, `gradlew` | Gradle (Java, Kotlin) | `gradle.lockfile` when present, `libs.versions.toml`, the build scripts |
| `requirements*.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock`, `pdm.lock`, `Pipfile.lock` | Python | the lockfile first; requirements files otherwise |

A project can have several: run the chain for each ecosystem.

## 2. See what changed

`git diff <base>...HEAD -- <manifests>` (or `git diff --staged`): the dependencies added, upgraded, downgraded or removed. Scan everything, but mark which findings the change introduced: those are the ones the change must fix or justify. Review the manifest changes by hand as `LOCK-n` findings: a version pinned below the framework's BOM, a dynamic or open version (`+`, `latest.release`, a Maven range, a Python requirement without `==`), a SNAPSHOT outside the project's own modules, a new repository or index URL, a lockfile that did not change with its manifest.

## 3. Run the dependency chain

Go down the chain until one step gives a result; run the next steps too when they are available, to cross-check. The commands, report locations and how to read them are in `references/tool-chain.md`.

| Step | Java / Kotlin | Python |
|---|---|---|
| 1. Native audit | the OWASP dependency-check plugin, when the build declares it: `./mvnw -B org.owasp:dependency-check-maven:check` or `./gradlew dependencyCheckAnalyze` | `pip-audit` with no arguments inside the project's environment, already installed; or `pip-audit -r <file> --no-deps --disable-pip` only when every requirement is pinned with `==` (better, with `--hash`) |
| 2. OSV-Scanner | `osv-scanner scan source -r .` (reads `pom.xml` and the Gradle lockfiles) | the same command: it reads `poetry.lock`, `uv.lock`, `pdm.lock`, `Pipfile.lock` and pinned requirements without installing anything; prefer it for a Python lockfile |
| 3. dependency-check CLI | `dependency-check --scan . --format JSON --out <folder outside the repo>` | same, with its Python analyzers (experimental) |
| Optional | SonarQube or Fortify results, only when the project already has them | same |

A Python project with only loose requirements and no environment: run OSV-Scanner if it is there; otherwise the dependency step is `not run`, with the command, because auditing them would install them.

**When no tool can run** (none installed, no network, or your tools cannot run commands): say so for each step, with the exact command the person or CI should run, and review the changed dependencies by hand:

- list each added or changed dependency with its version and whether the framework's BOM manages it (a version pinned below the BOM's is suspect);
- report only advisories you are sure about, from the advisory ID and the affected range, marked `manual, not confirmed by a scanner`; a few well-known examples are in `references/tool-chain.md`;
- say that the absence of findings proves nothing until a scanner runs.

## 4. Search the code for insecure patterns

Search the changed files first, then the rest of the source, for the patterns of `references/code-patterns.md`: injection sinks, unsafe deserialization, XML external entities, weak cryptography and randomness, disabled TLS checks, hard-coded secrets, permissive security configuration, debug settings, SSRF and path traversal sinks, and exceptions that fail open. Read each hit in context before reporting it: a constant argument is not an injection.

## 5. Cross-check

- **Same advisory from two tools:** one finding, confirmed by both. A CVE and its GHSA alias are one finding.
- **One tool only:** keep it, and say which tool.
- **Exposure** goes in its own column and never changes the severity: the scope (`runtime`, `test`, `provided`, `build plugin`) and the reachability: `reachable` with the `path:line` that calls the vulnerable API with untrusted input, `not reachable` with the reason, or `unknown`.
- **A code finding that matches a dependency finding** (the vulnerable API called from an endpoint): report the pair, each pointing at the other's ID, with the dependency's exposure `reachable` at the code finding's `path:line`.
- **False positives:** a CPE mismatch of dependency-check (a different product with the same name), or a pattern with constant input. Drop them with the reason in one line; never drop one without saying so. A test-only dependency is not a false positive: keep it, with exposure `test`.

## 6. Rate

- **Dependencies:** the advisory's CVSS base score: Critical 9.0 to 10.0, High 7.0 to 8.9, Medium 4.0 to 6.9, Low below 4.0. When sources disagree (NVD and the GitHub advisory), keep the higher and say so. Never raise or lower it for exposure: the person decides with the Exposure column.
- **Manifests and code:** the usual severity of the pattern in `references/code-patterns.md`, or Medium for a `LOCK-n` finding (High when it pins a known vulnerable version); lower a pattern only when the code proves the input is trusted.
- **OWASP Top 10:2025:** each finding gets one category, written with its year, from its CWE through `.exo/shared/owasp-2025.md` (`CWE-502, A08:2025 Software or Data Integrity Failures`). Dependency findings are `A03:2025 Software Supply Chain Failures`.

## 7. Report and hand off

- **Fixes as text:** the fixed version and where to set it (the BOM property such as `<log4j2.version>` in Spring Boot, `dependencyManagement`, a Gradle constraint, the lockfile), an exclusion, or the safe API for a code pattern. You do not apply them.
- **In verify:** it runs where the verify runs (`sdd-verifier`, read-only, or the session that runs the verify). The Critical and High findings go to Issues Found of `verify-record.md`, which `sdd-verify` writes. When the tier has the `security_review` gate, skill:security-code-review takes this report as the result of its check SCR-DEP-2: give the same findings as rows in the gate's Findings format (`| Critical | pom.xml:52 | DEP-1: log4j-core 2.14.1 ... | CWE-1395, A03:2025 Software Supply Chain Failures |`). This skill writes no gate and no file.
- **Outside SDD:** the report goes in the answer. Findings the person decides not to fix go to `dismissed_followups` with their reason, recorded by the orchestrator inside a change; never drop or dismiss one yourself.

## Return

```markdown
# Security scan: PROJ-88-export-reports (origin/main...HEAD)

Scope: pom.xml changed (snakeyaml pinned), ReportImport.java added.
Tools: dependency-check-maven (declared in pom.xml:142): `./mvnw -B org.owasp:dependency-check-maven:check`, not run (this agent cannot run Maven here); osv-scanner: not available on the path; dependency-check CLI: not available on the path; SonarQube, Fortify: not configured.

## Dependencies

| ID | Severity | Package | Installed, fixed | Advisory | Path | Exposure | Introduced | OWASP 2025 | Source |
|---|---|---|---|---|---|---|---|---|---|
| DEP-1 | Critical | org.yaml:snakeyaml | 1.33, 2.0 | CVE-2022-1471 (unsafe constructor) | direct, pom.xml:88 | runtime, reachable: PAT-1 | yes | CWE-1395, A03:2025 Software Supply Chain Failures | manual, not confirmed by a scanner |

## Manifests and lockfiles

| ID | Severity | path:line | Finding | OWASP 2025 |
|---|---|---|---|---|
| LOCK-1 | High | pom.xml:88 | snakeyaml is pinned below the version the Spring Boot BOM manages, at a known vulnerable version (DEP-1) | CWE-1357, A03:2025 Software Supply Chain Failures |

## Code patterns

| ID | Severity | path:line | Finding | OWASP 2025 |
|---|---|---|---|---|
| PAT-1 | Critical | src/main/java/com/example/reports/ReportImport.java:41 | `new Yaml().load(body)` on the request body of POST /reports/import: arbitrary types from user input (see DEP-1) | CWE-502, A08:2025 Software or Data Integrity Failures |

## Not checked

Transitive dependencies (no scanner ran).

## Fixes (for the person)

1. PAT-1: `new Yaml(new SafeConstructor(new LoaderOptions()))` and a typed mapping.
2. DEP-1, LOCK-1: remove the explicit snakeyaml version, so the Boot BOM manages it.

Scan: partial (no scanner ran; dependency findings are manual). Critical 2, High 1, Medium 0, Low 0.
```

- IDs: `DEP-n` for vulnerable packages, `LOCK-n` for manifest and lockfile findings, `PAT-n` for code patterns; unique in the report.
- `Scan: complete` only when a scanner covered the full dependency tree (from a lockfile or the resolved build); otherwise `Scan: partial (<why>)`.

## Record

Inside an SDD change, an inline verify records the skill and each tool that ran (`.exo/shared/capability-attribution.md`); a subagent lists them in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "security-scan-jkp", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "osv-scanner", "type": "command", "activation": "auto"}'
exo change record <change> --add skills_used '"security-scan-jkp"'
```

Record a tool only when it ran. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Every step of the chain has its exact command and outcome; nothing was installed, built or changed.
- [ ] Each dependency finding has its advisory, fixed version, path, exposure and confirmation source; manual ones say so.
- [ ] Each finding has its ID, a severity that exposure did not change, and an OWASP Top 10:2025 category with its year from `.exo/shared/owasp-2025.md`.
- [ ] Reachability is stated where the code shows it; dropped false positives have a reason.
- [ ] The Critical and High findings are listed for verify, no secret is copied into the report, and the last line is `Scan: complete` or `Scan: partial (<why>)` with the counts.
