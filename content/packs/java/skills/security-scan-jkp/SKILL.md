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

A scan report with four parts:

1. **Tools:** each step of the chain with its exact command and outcome: ran, not available, or not run (and why).
2. **Dependency findings:** package, version, advisory (CVE or GHSA), severity, fixed version, direct or transitive (and through what), and the tools that confirm it.
3. **Code findings:** insecure patterns with `path:line`, CWE and OWASP Top 10:2025 category.
4. **For verify:** the Critical and High findings, ready for Issues Found.

You change nothing: no edits to the build, no upgrades, no installs.

## When

- **SDD verify, Conditional** (`.exo/shared/phase-skill-map.md`): the diff changes a dependency manifest or a lockfile: `pom.xml`, `build.gradle(.kts)`, `settings.gradle(.kts)`, `gradle/libs.versions.toml`, `gradle.lockfile`, `requirements*.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock`, `Pipfile.lock`.
- **On request:** "are our dependencies vulnerable", before a release, after an advisory.
- **Not for:** Node projects (`security-scan-node`, pack `frontend`); a full security review of the code of a diff (skill:security-code-review, which uses this report for its dependency check SCR-DEP-2).

## Permissions and network

- Read-only. Run only scanners the project already has: a plugin declared in the build, or a tool already on the path. Never add a plugin, never install a tool, never change a version.
- Scanners download advisory data (NVD, OSV, PyPI) and OSV-Scanner sends package names and versions, never code. Run them where the project already runs them (CI) or where the person allows network access. Without network, the step is `not run`.
- SonarQube and Fortify analyses upload code to their server: use them only when the project already does (a `sonar-project.properties`, a Sonar or Fortify plugin, a CI step), preferably by reading the result its CI already produced. They are never required.
- Never copy a secret into the report. A hard-coded credential is a finding at its `path:line`, without the value (`.exo/shared/data-protection.md`).

## 1. Detect the project

| Signal | Ecosystem | Manifests to scan |
|---|---|---|
| `pom.xml`, `mvnw` | Maven (Java, Kotlin) | every `pom.xml` of the reactor |
| `build.gradle(.kts)`, `gradlew` | Gradle (Java, Kotlin) | `gradle.lockfile` when present, `libs.versions.toml`, the build scripts |
| `requirements*.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock`, `Pipfile.lock` | Python | the lockfile first; requirements files otherwise |

A project can have several: run the chain for each ecosystem.

## 2. See what changed

`git diff <base>...HEAD -- <manifests>` (or `git diff --staged`): the dependencies added, upgraded, downgraded or removed, and versions pinned against the framework's BOM. Scan everything, but mark which findings the change introduced: those are the ones the change must fix or justify.

## 3. Run the dependency chain

Go down the chain until one step gives a result; run the next steps too when they are available, to cross-check. The commands, report locations and how to read them are in `references/tool-chain.md`.

| Step | Java / Kotlin | Python |
|---|---|---|
| 1. Native audit | the OWASP dependency-check plugin, when the build declares it: `mvn -B org.owasp:dependency-check-maven:check` or `./gradlew dependencyCheckAnalyze` | `pip-audit -r requirements.txt` (or on the active environment) |
| 2. OSV-Scanner | `osv-scanner scan source -r .` (reads `pom.xml`, Gradle lockfiles and the Python lockfiles) | same command |
| 3. dependency-check CLI | `dependency-check --scan . --format JSON --out <folder outside the repo>` | same, with its Python analyzers (experimental) |
| Optional | SonarQube or Fortify results, only when the project already has them | same |

**When no tool can run** (none installed, no network, or your tools cannot run commands): say so for each step, with the exact command the person or CI should run, and review the changed dependencies by hand:

- list each added or changed dependency with its version and whether the framework's BOM manages it (a version pinned below the BOM's is suspect);
- report only advisories you are sure about, from the advisory ID and the affected range, marked `manual, not confirmed by a scanner`; a few well-known examples are in `references/tool-chain.md`;
- say that the absence of findings proves nothing until a scanner runs.

## 4. Search the code for insecure patterns

Search the changed files first, then the rest of the source, for the patterns of `references/code-patterns.md`: injection sinks, unsafe deserialization, XML external entities, weak cryptography and randomness, disabled TLS checks, hard-coded secrets, permissive security configuration, debug settings, SSRF and path traversal sinks, and exceptions that fail open. Read each hit in context before reporting it: a constant argument is not an injection.

## 5. Cross-check

- **Same advisory from two tools:** one finding, confirmed by both.
- **One tool only:** keep it, and say which tool.
- **Reachability:** a vulnerable library is worse when the code calls the vulnerable API with untrusted input; say `reachable` with the `path:line` that proves it, `not reachable` with the reason, or `unknown`.
- **A code finding that matches a dependency finding** (the vulnerable API called from an endpoint) raises both: report the pair.
- **False positives:** a CPE mismatch of dependency-check (a different product with the same name), a test-only dependency, or a pattern with constant input. Drop them with the reason in one line; never drop one without saying so.

## 6. Rate

- **Dependencies:** the advisory's CVSS: Critical 9.0 to 10.0, High 7.0 to 8.9, Medium 4.0 to 6.9, Low below 4.0; when sources disagree (NVD and the GitHub advisory), take the higher. Raise one level when it is reachable from untrusted input; never lower one without evidence.
- **Code:** Critical when anyone who reaches the entry point can exploit it (injection, deserialization of request data, a credential in code); High when it needs sign-in or a second condition; Medium for missing hardening; Low for suggestions.
- **OWASP Top 10:2025:** each finding gets one category, written with its year (`A03:2025 Software Supply Chain Failures`). The list, and its correspondence with the 2021 edition that other skills cite, is in `references/owasp-2025.md`.

## 7. Report and hand off

- **Fixes as text:** the fixed version and where to set it (the BOM property such as `<log4j2.version>` in Spring Boot, `dependencyManagement`, a Gradle constraint, the lockfile), an exclusion, or the safe API for a code pattern. You do not apply them.
- **In verify:** the Critical and High findings go to Issues Found of `verify-record.md`, which `sdd-verify` writes. When the tier has the `security_review` gate, skill:security-code-review takes this report as the result of its check SCR-DEP-2. This skill writes no gate.
- **Outside SDD:** the report goes in the answer. A finding the person decides to accept stays visible in the report with their reason; never drop it on your own.

## Return

```markdown
# Security scan: PROJ-88-export-reports

## Tools

| Step | Tool | Command | Outcome |
|---|---|---|---|
| 1 | dependency-check-maven (declared in pom.xml:142) | mvn -B org.owasp:dependency-check-maven:check | not run: this agent cannot run Maven here |
| 2 | OSV-Scanner | osv-scanner scan source -r . | not available on the path |
| 3 | dependency-check CLI | dependency-check --scan . --format JSON --out <folder> | not available on the path |
| - | SonarQube, Fortify | - | not configured in this project |

No scanner ran: dependency findings below are manual and need a scanner to confirm.

## Dependency findings

| Severity | Package | Version | Advisory | Fixed in | Path | Introduced by this change | Confirmed by |
|---|---|---|---|---|---|---|---|
| Critical | org.yaml:snakeyaml | 1.33 | CVE-2022-1471 (unsafe constructor) | 2.0 | direct, pom.xml:88, pinned below the Boot BOM | yes | manual, not confirmed by a scanner |

## Code findings

| Severity | path:line | Finding | CWE | OWASP Top 10:2025 |
|---|---|---|---|---|
| Critical | src/main/java/com/example/reports/ReportImport.java:41 | `new Yaml().load(body)` on the request body: arbitrary types from user input; reachable from POST /reports/import | CWE-502 | A08:2025 Software or Data Integrity Failures |

## For verify

- Critical: ReportImport.java:41 unsafe YAML load of request data (CWE-502, A08:2025); use `new Yaml(new SafeConstructor(new LoaderOptions()))` and a typed mapping.
- Critical: snakeyaml 1.33 pinned below the Boot BOM (CVE-2022-1471, A03:2025); remove the explicit version.
```

## Record

Inside an SDD change, an inline verify records the skill and each tool that ran (`.exo/shared/capability-attribution.md`); a subagent lists them in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "security-scan-jkp", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "osv-scanner", "type": "command", "activation": "auto"}'
exo change record <change> --add skills_used '"security-scan-jkp"'
```

Record a tool only when it ran. In Windows PowerShell 5.1, pass the JSON as `@<file>` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Every step of the chain has its exact command and outcome; nothing was installed or changed.
- [ ] Each dependency finding has its advisory, fixed version, path and confirmation source; manual ones say so.
- [ ] Each code finding has `path:line`, CWE and an OWASP Top 10:2025 category with its year.
- [ ] Reachability is stated where the code shows it; dropped false positives have a reason.
- [ ] The Critical and High findings are listed for verify, and no secret is copied into the report.
