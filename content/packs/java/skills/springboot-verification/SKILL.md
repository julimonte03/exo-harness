---
name: springboot-verification
description: >-
  The verification loop for a Spring Boot or Java change before a pull
  request or a release, read-only: compile, unit and integration tests,
  coverage with JaCoCo, the static analysis the build already declares
  (Checkstyle, PMD, SpotBugs, Error Prone, Spotless check), the dependency
  scan when a dependency changed, and a review of the diff, with the
  project's own commands; SonarQube only when the project
  already uses it. Reports each step as passed, failed or not run with its
  exact command and ends with a Verification line; never fixes anything.
  Use it when asked whether a Java or Spring Boot change is ready, to run
  the Maven or Gradle checks before a pull request, or to verify a release
  candidate. Not for the pre-commit check
  (pre-commit-review) or the SDD verify (sdd-verify). Triggers: "run the
  Maven checks", "run the Gradle checks", "mvn verify", "is this Spring
  Boot change ready for a PR", "check coverage with JaCoCo", "pre-release
  check of the Java service", "run the Java build and tests".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-only+tests
---

# springboot-verification

## Result

- A verification report: one row per step with the exact command and its outcome (`passed`, `failed`, `not run` with the reason), the numbers that matter (tests passed, failed and skipped; coverage of the changed code), and the findings of the analysis and the diff review with `path:line`.
- The last line is exactly one of:
  - `Verification: failed`: a step failed, or a Critical or High finding is open;
  - `Verification: incomplete`: nothing failed, but a step that applies could not run;
  - `Verification: passed`: every step that applies ran and passed, and no Critical or High finding is open.
- You change nothing.

## When

- Before a pull request or a release of a Spring Boot (or plain Maven or Gradle Java) project, or when someone asks whether a Java change is ready.
- **In SDD verify, on request:** the verify phase runs `harness-review` (pack `quality`) through `sdd-verify`, which owns the record and the gates. When the person or the verify asks for the Java checks, this skill gives the commands and steps that the verifier runs; its findings go to Issues Found and Tests of `verify-record.md`. Outside the phases, skill:backend-engineering routes here.
- **Not for:** the quick check before each commit (`pre-commit-review`, pack `quality`); the verify of an SDD change itself (`sdd-verify`, pack `sdd`); fixing what fails. A failing build goes to skill:java-build-resolver; a failing test or a finding goes back to the work (the apply phase in SDD).

## Permissions

- Read-only. Run only build, test and analysis commands, and read-only git (`git diff`, `git log`, `git status`, `git show`).
- Never: `-DskipTests` or `-x test` for the test step, `spotless:apply` or any formatter in fix mode, edits, stashes, checkouts, commits, dependency installs, new plugins in the build. Build output folders (`target/`, `build/`) are fine.
- **When your tools cannot run the build** (the command is not allowed, or there is no JDK): every command step is `not run: <reason>`, with the exact command for the person or CI. Do the steps that only read (diff review, test presence, configuration and migrations), and the result is at best `Verification: incomplete`.

## 0. Find the commands

In this order, and write down where each command came from:

1. `.exo/context.md`, Commands.
2. **CI wins over the README:** the pipeline file (`.github/workflows/*.yml`, `azure-pipelines.yml`, `.gitlab-ci.yml`, `Jenkinsfile`) shows what the project really runs (for example a Maven task with the goal `verify`).
3. The wrapper (`mvnw`, `gradlew`); without one, `mvn` or `gradle`.
4. The plugins the build declares: JaCoCo, Checkstyle, PMD, SpotBugs, Error Prone, Spotless, OWASP dependency-check, Sonar. Only declared tools run; a tool the build lacks is `not configured`, never installed.

The default commands per tool are in `references/commands.md`.

## 1. Compile

`./mvnw -B test-compile` or `./gradlew compileJava compileTestJava`. A failure stops the loop: report the first error and hand it to skill:java-build-resolver.

## 2. Tests

- The full suite as CI runs it: `./mvnw -B verify` (unit tests with Surefire, integration tests with Failsafe) or `./gradlew check`.
- Read the counts from the reports (`target/surefire-reports`, `target/failsafe-reports`, `build/test-results`): passed, failed, errors, skipped.
- A failing test: its name, the assertion, and whether the change touched the code it covers. Re-run a failing test once only to tell a flaky test from a real failure, and report it as flaky, never as passed.
- Tests that need Docker (Testcontainers) or a service: if it is not available, that part is `not run` with the reason.
- **Tests for the change:** every new or changed behavior in the diff has a test that would fail without it. Missing tests are a finding (High for a changed rule or a new endpoint).

## 3. Coverage

- Only with JaCoCo configured: read `target/site/jacoco/jacoco.xml` or `build/reports/jacoco/test/jacocoTestReport.xml` and report line and branch coverage **of the changed classes**, plus the project's threshold (`jacoco:check` rules) and whether it passes.
- No threshold of your own. Without JaCoCo: `not configured`, and list the changed classes that have no test at all.

## 4. Static analysis

- Run the checks the build declares, in check mode only: `checkstyle:check`, `pmd:check`, `spotbugs:check`, `spotless:check`, Error Prone through the compiler; the Gradle `check` task runs the ones applied.
- Report the violations on changed lines first; pre-existing ones only as a count.
- None configured: say so. skill:java-coding-standards can review the changed files by reading.

## 5. Dependency scan

- A dependency manifest or lockfile changed (`git diff --name-only <base>...HEAD`): run skill:security-scan-jkp and take its Critical and High findings.
- No dependency change: `not needed: no manifest or lockfile changed`.

## 6. Diff review

`git diff <base>...HEAD` (or the staged diff the person names), with the changed files read in full:

- the Java changes with skill:java-reviewer (or, when you keep it short, its main checks: correctness, transactions, N+1 and unbounded queries, security, error handling);
- debug leftovers: `System.out`, `printStackTrace`, commented-out code, focused or disabled tests (`@Disabled` without a reason);
- configuration: profiles, secrets (`.exo/shared/data-protection.md`; point at the line, never copy the value), Actuator exposure, `ddl-auto` other than `validate` or `none`;
- migrations: new files only; **an edited migration that already ran is High** (Flyway checksums fail on every database that applied it);
- the API contract (OpenAPI) updated when endpoints changed.

## 7. Optional: SonarQube

Only when the project already has it (a `sonar-project.properties`, the Sonar plugin, a Sonar step in CI). Prefer the quality gate result CI already produced. Running an analysis uploads code to the server: only when the project already does it and the person asks. Its absence is never a finding.

## Return

```markdown
# Verification: feat/PROJ-41-cancel-orders against main

| Step | Command (source) | Outcome |
|---|---|---|
| Compile | ./mvnw -B test-compile (.exo/context.md) | passed |
| Tests | ./mvnw -B verify (CI: .github/workflows/build.yml:31) | failed: 212 passed, 1 failed (OrderServiceTest.cancelsWithinWindow), 0 skipped |
| Coverage | JaCoCo report | changed classes: OrderService 81% lines, 70% branches; project rule 75% lines: passed |
| Static analysis | ./mvnw -B checkstyle:check spotbugs:check | passed (Checkstyle 0 new, SpotBugs 0) |
| Dependency scan | security-scan-jkp | not needed: no manifest or lockfile changed |
| Diff review | git diff main...HEAD, 6 files | 2 findings |
| SonarQube | - | not configured |

## Findings

| Severity | path:line | Finding | Fix |
|---|---|---|---|
| High | src/test/java/com/example/orders/OrderServiceTest.java:88 | cancelsWithinWindow fails: the window is read in hours but the test sets minutes | align the test or the property with the spec |
| Low | src/main/java/com/example/orders/OrderService.java:57 | System.out.println left in | remove it or log at debug |

Verification: failed
```

## Record

Inside an SDD change, the session that runs the verify records the skill and the commands it ran (`.exo/shared/capability-attribution.md`); a subagent lists them in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "springboot-verification", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "mvn verify", "type": "command", "activation": "auto"}'
exo change record <change> --add skills_used '"springboot-verification"'
```

Record a command only when it ran.

## Before you finish

- [ ] Every step has its exact command, where it came from, and an outcome; nothing was skipped silently.
- [ ] Test counts come from the reports; flaky tests are reported as flaky.
- [ ] Coverage and analysis use only what the build declares; no threshold was invented.
- [ ] The diff review covered leftovers, secrets, configuration, migrations and tests for the change.
- [ ] Nothing was changed, and the last line is `Verification: passed`, `failed` or `incomplete`.
