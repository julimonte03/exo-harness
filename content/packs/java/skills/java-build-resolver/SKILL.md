---
name: java-build-resolver
description: >-
  Diagnoses and fixes Maven and Gradle build failures in Java and Kotlin
  projects with the smallest change: compiler errors, missing or conflicting
  dependencies, versions that fight the Spring Boot or Quarkus BOM, javax to
  jakarta leftovers, plugin and toolchain errors (wrong JDK, release level),
  annotation processors such as Lombok and MapStruct, and tests that fail
  inside the build. Detects Spring Boot or Quarkus and applies their
  conventions. Works from the build log and the build files; when it cannot
  run the build it says exactly which command to run. Never skips or deletes
  tests to get green. Use it when mvn or gradle fails, CI breaks at the build,
  or the project does not compile. Triggers: "the build fails", "BUILD
  FAILURE", "mvn verify fails", "gradle build error", "cannot find symbol",
  "package does not exist", "could not resolve dependencies", "fix the
  compilation error", "dependency convergence".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-write
---

# java-build-resolver

## Result

- The root cause of the failure, named from the **first real error** in the log, with its `path:line` or the build file element.
- The smallest fix that removes it, applied to the build file or the code, or proposed when the person or the phase does not allow edits.
- The exact command that confirms the fix, run when you can, otherwise written as `not run` with the reason.

## When

- A Maven or Gradle build fails: locally, in CI, or in the apply or verify phase of an SDD change.
- **Not for:** a test that fails because the behavior is wrong (that is the change's own work: fix it within the plan), dependency vulnerabilities (skill:security-scan-jkp), or style findings (skill:java-coding-standards).

## Rules

- **Smallest change.** Fix the cause, one at a time. No upgrades, refactors or reformatting beyond what the error needs.
- **Never get green by hiding the failure:** no `-DskipTests`, `-Dmaven.test.failure.ignore`, `testFailureIgnore`, `@Disabled`, deleted or weakened assertions, `-Denforcer.skip`, removed plugins, lowered Java `release`, or `--offline` workarounds.
- **Never install anything:** no JDK, Maven, Gradle or plugin downloads on your own. If the environment lacks something, say what and how the person installs it.
- **No credentials in the chat.** A private repository that rejects the build needs credentials in `settings.xml`, `gradle.properties` or environment variables, which the person configures; tell them where, never ask for the values. When asking for a log, tell them to redact tokens and URLs with passwords.
- **Inside an SDD change,** a fix that the frozen plan does not cover (a new dependency, a version change) is a question for the person: return `status: needs-input` with the fix you propose.

## 1. Get the log

In this order:

1. The log the person pasted or saved (`build.log`, CI output), and the test reports (`target/surefire-reports/*.txt`, `target/failsafe-reports/`, `build/test-results/`, `build/reports/tests/`).
2. Run the build yourself, when your tools allow it, with the wrapper and verbose errors:
   - Maven: `./mvnw -B -e verify` (or `mvn -B -e verify` without a wrapper; `mvnw.cmd` on Windows).
   - Gradle: `./gradlew build --stacktrace` (`gradlew.bat` on Windows).
   - The command CI runs wins: read the pipeline file.
3. If you can neither read a log nor run the build, say the exact command to run and which part of the output to paste: from the first `[ERROR]` (Maven) or `* What went wrong:` (Gradle) to the end.

## 2. Detect the project

Read the build files, not only the log:

- **Tool and layout:** `pom.xml` (modules in `<modules>`), or `settings.gradle(.kts)` with `build.gradle(.kts)`, `gradle/libs.versions.toml`, `gradle.properties`; the wrapper version (`.mvn/wrapper/maven-wrapper.properties`, `gradle/wrapper/gradle-wrapper.properties`).
- **Java version:** `java.version` or `maven.compiler.release` (Maven), `java { toolchain { languageVersion } }` or `sourceCompatibility` (Gradle), `.java-version`, `.sdkmanrc`, the JDK in CI and in the Dockerfile.
- **Framework:**
  - Spring Boot: the `spring-boot-starter-parent` version, or `spring-boot-dependencies` imported as a BOM, or the `org.springframework.boot` plugin. Boot 3 needs Java 17+ and uses Jakarta EE (`jakarta.*`).
  - Quarkus: `io.quarkus.platform:quarkus-bom` and `quarkus-maven-plugin` (or the `io.quarkus` Gradle plugin) at the same version. Quarkus 3 uses `jakarta.*` too.
- **Processors and plugins:** Lombok, MapStruct, the compiler plugin and its `annotationProcessorPaths`, surefire and failsafe, enforcer, code generators (OpenAPI, jOOQ, protobuf).

## 3. Find the first real error

- **Maven:** the first `[ERROR]` lines, and the `Failed to execute goal <plugin>:<version>:<goal> (<execution>) on project <module>` line: it names the plugin, the phase and the module that failed.
- **Gradle:** the `* What went wrong:` block and the first `> Task :<module>:<task> FAILED`.
- **Errors cascade.** One missing package produces a "package does not exist" for the import and a "cannot find symbol" for every use. Count them as one cause.
- **Tests:** `Tests run: X, Failures: Y, Errors: Z`, then the report of the first failing test, and in it the deepest `Caused by:`.

## 4. Classify and fix

The catalog of symptoms, causes and fixes is in `references/error-catalog.md`; the diagnostic commands are in `references/commands.md`. The most common causes:

| Symptom | Usual cause | Fix |
|---|---|---|
| `package javax.validation does not exist` (or `javax.persistence`, `javax.servlet`) on Boot 3 or Quarkus 3 | code written for Java EE / Boot 2 | change the imports to `jakarta.*`; add the starter that provides the API (`spring-boot-starter-validation`) without a version |
| `package X does not exist`, `cannot find symbol` for a class from a library | dependency missing, or in the wrong scope (`test`, `provided`) | add the dependency, without a version when the BOM manages it |
| `cannot find symbol` for a getter or a builder of a Lombok class | Lombok not on the annotation processor path | add Lombok to `annotationProcessorPaths` (Maven) or the `annotationProcessor` configuration (Gradle) |
| `release version 21 not supported`, `invalid target release` | the JDK running the build is older than the target | run with the right JDK (`JAVA_HOME`, a toolchain); never lower the target |
| `Could not resolve dependencies`, `Could not find artifact` | a version that does not exist, a typo, a missing repository, no network or no credentials | fix the coordinates; check the repository and the credentials setup, without asking for them |
| `NoSuchMethodError`, `NoClassDefFoundError`, `ClassNotFoundException` at test or start-up | two versions of a library on the classpath; a version pinned against the BOM | find it with `dependency:tree` or `dependencyInsight`; remove the pinned version or align it in `dependencyManagement` / constraints |
| `Failed to load ApplicationContext` in tests | a bean or configuration error | read the deepest `Caused by:`: a missing property, a bean that fails, a database the test cannot reach |

- **Spring Boot:** do not pin versions of libraries the Boot BOM manages; the Boot plugin and parent share one version; change a managed version only through its property (`<jackson-bom.version>`) and only when the cause demands it.
- **Quarkus:** add capabilities as Quarkus extensions (`quarkus-hibernate-validator`, `quarkus-rest-jackson`), not raw libraries; the BOM and the plugin stay at the same version.
- **Tests that fail in the build:** decide first whether the failure is the code, the test, or the environment (no Docker for Testcontainers, a port in use, the time zone or locale). Fix the code or the test for the first two; for the environment, say what is missing. Never skip.

## 5. Apply and confirm

1. Apply one fix. Show what changed (the build element or the code line).
2. Run the same command again when you can. A new first error is a new cause: go back to step 3.
3. When you cannot run it, say so and give the command. Do not claim the build passes.

## Return

```markdown
Build: Gradle 8.10 (wrapper), Java 21 toolchain, Spring Boot 3.4.1 (plugin and dependency management)
First error: :test, OrderMapperTest > mapsLines() — java.lang.NoSuchMethodError in com.fasterxml.jackson.databind.ObjectMapper (build/test-results/test/TEST-com.example.orders.OrderMapperTest.xml); 3 more tests fail with the same error.
Cause: build.gradle.kts:41 pins jackson-databind 2.13.4, older than the Jackson that Boot 3.4 manages, so the classpath mixes two Jackson versions.
Fix (applied): build.gradle.kts:41 drops the explicit version; the Boot BOM manages it.
Confirm: ./gradlew dependencyInsight --dependency jackson-databind, then ./gradlew build — not run: this agent cannot run Gradle here.
Not touched: no test skipped or changed.
```

When the fix needs a decision (a version change, a new repository), say `Fix (proposed)` and wait for the person.

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "java-build-resolver", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"java-build-resolver"'
```

## Before you finish

- [ ] The first real error is named with its location; cascades are counted under it.
- [ ] The fix is the smallest one, and no test, check or plugin was skipped or removed.
- [ ] Versions the Spring Boot or Quarkus BOM manages were not pinned.
- [ ] The confirming command was run, or the answer says `not run` and why.
- [ ] No credentials were requested or copied; anything outside the plan went to the person.
