# Verification commands

Use the wrapper when the project has one. Run a tool only when the build declares it; the plugin's own configuration (rules, thresholds, exclusions) is the project's and is never changed here.

## Maven

| Step | Command | Present when | Report |
|---|---|---|---|
| Compile | `./mvnw -B test-compile` | always | console |
| Unit tests | `./mvnw -B test` | always | `target/surefire-reports/` |
| Unit and integration tests | `./mvnw -B verify` | always (Failsafe runs `*IT` tests when configured) | `target/failsafe-reports/` |
| Coverage | part of `verify` when JaCoCo binds `report` and `check` | `org.jacoco:jacoco-maven-plugin` | `target/site/jacoco/jacoco.xml`, `index.html` |
| Checkstyle | `./mvnw -B checkstyle:check` | `maven-checkstyle-plugin` | `target/checkstyle-result.xml` |
| PMD | `./mvnw -B pmd:check` | `maven-pmd-plugin` | `target/pmd.xml` |
| SpotBugs | `./mvnw -B spotbugs:check` | `com.github.spotbugs:spotbugs-maven-plugin` | `target/spotbugsXml.xml` |
| Spotless (check only) | `./mvnw -B spotless:check` | `com.diffplug.spotless:spotless-maven-plugin` | console |
| Error Prone | part of `compile` | `error_prone_core` in `annotationProcessorPaths` with `-Xplugin:ErrorProne` | console |
| Dependency check | `./mvnw -B org.owasp:dependency-check-maven:check` | `org.owasp:dependency-check-maven` | `target/dependency-check-report.html` |
| SonarQube | read CI's result; `./mvnw -B sonar:sonar` only if the project already runs it and the person asks | `sonar-maven-plugin` or a CI step | the server |

## Gradle

| Step | Command | Present when | Report |
|---|---|---|---|
| Compile | `./gradlew compileJava compileTestJava` | always | console |
| Tests | `./gradlew test` | always | `build/test-results/test/`, `build/reports/tests/test/` |
| Everything the build wires into check | `./gradlew check` | always | per plugin |
| Coverage | `./gradlew jacocoTestReport jacocoTestCoverageVerification` | the `jacoco` plugin | `build/reports/jacoco/test/` |
| Checkstyle | `./gradlew checkstyleMain checkstyleTest` | the `checkstyle` plugin | `build/reports/checkstyle/` |
| PMD | `./gradlew pmdMain` | the `pmd` plugin | `build/reports/pmd/` |
| SpotBugs | `./gradlew spotbugsMain` | `com.github.spotbugs` | `build/reports/spotbugs/` |
| Spotless (check only) | `./gradlew spotlessCheck` | `com.diffplug.spotless` | console |
| Dependency check | `./gradlew dependencyCheckAnalyze` | `org.owasp.dependencycheck` | `build/reports/dependency-check-report.html` |
| SonarQube | read CI's result; `./gradlew sonar` only if the project already runs it and the person asks | `org.sonarqube` | the server |

## Reading the reports

- **Surefire and Failsafe:** each `TEST-<class>.xml` has `tests`, `failures`, `errors` and `skipped` attributes; the `.txt` files hold the failure messages and stack traces.
- **JaCoCo XML:** per class, `<counter type="LINE" missed=".." covered=".."/>` and `BRANCH`; coverage is covered divided by covered plus missed. Report the classes the diff changed.
- **Checkstyle, PMD, SpotBugs:** each violation has a file and a line; compare with the changed lines of the diff to tell new violations from old ones.

## Finding the changed files

| Need | Command |
|---|---|
| Files changed on the branch | `git diff --name-only <base>...HEAD` |
| Staged files | `git diff --staged --name-only` |
| Manifests and lockfiles changed | `git diff --name-only <base>...HEAD -- pom.xml '**/pom.xml' '*.gradle*' gradle/libs.versions.toml '*.lockfile'` |
| Migrations changed (should list only new files) | `git diff --name-status <base>...HEAD -- src/main/resources/db/migration` (`A` is new, `M` is an edit) |
