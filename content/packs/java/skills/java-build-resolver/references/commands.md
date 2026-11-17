# Diagnostic commands

Use the wrapper when the project has one (`./mvnw`, `./gradlew`; `mvnw.cmd`, `gradlew.bat` on Windows). These commands read and build; none of them changes the build files. Run them only when your tools allow it; otherwise give them to the person.

## Maven

| Goal | Command |
|---|---|
| Build with full error detail | `./mvnw -B -e verify` |
| Only compile main and test code | `./mvnw -B test-compile` |
| One module and what it needs | `./mvnw -B -pl <module> -am verify` |
| One test class or method | `./mvnw -B test -Dtest=OrderServiceTest` or `-Dtest='OrderServiceTest#cancels*'` |
| Who brings a dependency | `./mvnw dependency:tree -Dverbose -Dincludes=<groupId>:<artifactId>` |
| Declared but unused, used but undeclared | `./mvnw dependency:analyze` |
| The effective POM (versions after the parent and BOMs) | `./mvnw help:effective-pom -Doutput=<file>` |
| Which JDK and Maven run the build | `./mvnw -v` |
| Debug logging for a plugin problem | `./mvnw -B -X <goal>` (long output: save it to a file and search it) |

Reports: `target/surefire-reports/` (unit tests), `target/failsafe-reports/` (integration tests), `target/site/jacoco/` (coverage, when configured).

## Gradle

| Goal | Command |
|---|---|
| Build with stack traces | `./gradlew build --stacktrace` |
| Only compile | `./gradlew compileJava compileTestJava` |
| One subproject | `./gradlew :<module>:build` |
| One test | `./gradlew test --tests 'com.example.orders.OrderServiceTest'` |
| Who brings a dependency | `./gradlew dependencyInsight --dependency <artifactId> --configuration runtimeClasspath` |
| The whole dependency graph | `./gradlew dependencies --configuration runtimeClasspath` |
| Which JDK and Gradle run the build | `./gradlew -version`, and `./gradlew javaToolchains` |
| Why a task re-ran or failed in detail | `./gradlew <task> --info` |

Reports: `build/test-results/` (XML), `build/reports/tests/` (HTML), `build/reports/jacoco/` (coverage, when configured).

## Reading a Maven failure

```text
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.13.0:compile (default-compile) on project orders: Compilation failure
```

- `maven-compiler-plugin:3.13.0` is the plugin and its version; `compile` is the goal; `default-compile` the execution; `orders` the module.
- The compiler errors above that line have the form `<file>:[<line>,<column>] <message>`.

## Reading a Gradle failure

```text
* What went wrong:
Execution failed for task ':orders:compileJava'.
> Compilation failed; see the compiler error output for details.
```

- `:orders:compileJava` is the subproject and the task; the compiler errors are printed above, as `<file>:<line>: error: <message>`.
