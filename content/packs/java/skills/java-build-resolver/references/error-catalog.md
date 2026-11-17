# Build error catalog

Symptom, likely causes in order, and the fix. Confirm the cause in the build files before changing anything.

## Compilation

| Symptom | Causes | Fix |
|---|---|---|
| `package X does not exist` | 1. the dependency is missing; 2. it is in `test` or `provided` scope but used from main code; 3. a `javax.*` package on a Jakarta stack; 4. generated sources not generated (OpenAPI, jOOQ, protobuf) | 1. add it (no version when a BOM manages it); 2. fix the scope; 3. move to `jakarta.*`; 4. check the generator plugin runs in `generate-sources` and its input exists |
| `cannot find symbol` for a project class | a typo, a class moved or renamed, a missing import, a module dependency missing in a multi-module build | fix the import or add the module dependency |
| `cannot find symbol` for `getX()`, `builder()`, `log` on a Lombok class | Lombok is not running as an annotation processor | Maven: add Lombok to `maven-compiler-plugin` `annotationProcessorPaths`; Gradle: `compileOnly` plus `annotationProcessor` |
| MapStruct generates mappers without the Lombok properties | processor order | `annotationProcessorPaths` in this order: `lombok`, `lombok-mapstruct-binding`, `mapstruct-processor` |
| `incompatible types`, `method X in class Y cannot be applied` | an API changed in an upgraded library | adapt the call to the new API, or keep the old version if the upgrade was not intended |
| `release version 21 not supported`, `invalid target release: 21`, `class file has wrong version 65.0, should be 61.0` | the JDK running the build (or the IDE) is older than the target, or a dependency was compiled for a newer Java | run with the right JDK (`JAVA_HOME`, Maven toolchains, Gradle toolchain); a dependency built for a newer Java needs a newer JDK or an older dependency version |
| `illegal character` at the first column of a file, or `unmappable character for encoding` | file encoding, or a byte order mark at the start of the file | set `project.build.sourceEncoding` to `UTF-8` (Maven) or `options.encoding = "UTF-8"` (Gradle); remove the byte order mark |
| `preview features are not enabled` | the code uses a preview feature of the JDK | remove the preview feature, or enable `--enable-preview` in compile and test consistently if the project decided to |

## javax to jakarta (Spring Boot 3, Quarkus 3, Jakarta EE 9+)

| Old import | New import | Provided by (Spring Boot) |
|---|---|---|
| `javax.validation.*` | `jakarta.validation.*` | `spring-boot-starter-validation` |
| `javax.persistence.*` | `jakarta.persistence.*` | `spring-boot-starter-data-jpa` |
| `javax.servlet.*` | `jakarta.servlet.*` | `spring-boot-starter-web` / `-tomcat` (`spring-boot-starter-webmvc` on Boot 4) |
| `javax.transaction.Transactional` | `jakarta.transaction.Transactional`, or Spring's `org.springframework.transaction.annotation.Transactional` | |
| `javax.annotation.PostConstruct` | `jakarta.annotation.PostConstruct` | `jakarta.annotation-api` (transitive in the starters) |

Not every `javax` moved: `javax.sql.DataSource`, `javax.crypto`, `javax.net.ssl` are part of the JDK and stay. Adding the old `javax.validation:validation-api` jar makes the code compile but leaves validation silently off, because Hibernate Validator 8 implements only Jakarta: do not do it.

## Spring Boot 4 upgrade

Boot 4 (Spring Framework 7, Jakarta EE 11, Java 17 or later) splits the auto-configuration into modules. Upgrade from the latest 3.5 with its deprecation warnings fixed; then these are the usual first errors.

| Symptom | Cause | Fix |
|---|---|---|
| `package org.springframework.boot.test.autoconfigure.web.servlet does not exist`, `cannot find symbol: WebMvcTest` (or `DataJpaTest`, `AutoConfigureTestDatabase`) | the slices moved to per-technology test modules and packages | add the test starter of the technology without a version (`spring-boot-starter-webmvc-test`, `spring-boot-starter-data-jpa-test`); take the new import from the module (`org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest`) |
| `cannot find symbol: MockBean` or `SpyBean` | removed in Boot 4 | `@MockitoBean` and `@MockitoSpyBean` from Spring Framework; a mock declared in a `@Configuration` class moves to the test class |
| `No qualifying bean of type MockMvc` in a `@SpringBootTest` | `@SpringBootTest` no longer configures MockMvc | add `@AutoConfigureMockMvc` |
| `TestRestTemplate` or `WebTestClient` not found or not injected | no longer provided by `@SpringBootTest` | `@AutoConfigureTestRestTemplate` with `spring-boot-resttestclient`, or `RestTestClient` with `@AutoConfigureRestTestClient` |
| `package com.fasterxml.jackson.databind does not exist`, or `NoSuchMethodError` in Jackson classes | Jackson 3 is the default, in `tools.jackson.*` (annotations stay in `com.fasterxml.jackson.annotation`) | move the code to Jackson 3 (`JsonMapper`, `JsonMapperBuilderCustomizer`, `@JacksonComponent`); the `spring-boot-jackson2` module is a deprecated stopgap, only with the person's agreement |
| `spring-boot-starter-web` deprecation warnings; OAuth2 starters not found | renamed starters | `spring-boot-starter-webmvc`; `spring-boot-starter-security-oauth2-resource-server` and `-client` |
| Flyway or Liquibase migrations no longer run at start-up | they need their own starter | `spring-boot-starter-flyway` or `spring-boot-starter-liquibase` |
| `spring-boot-starter-undertow` cannot be resolved | Undertow support was dropped | Tomcat (the default) or Jetty |

As a temporary step only, `spring-boot-starter-classic` and `spring-boot-starter-test-classic` bring every module back; the person decides, and the real fix stays the list above.

## Dependency resolution

| Symptom | Causes | Fix |
|---|---|---|
| `Could not find artifact g:a:v` | typo in coordinates; the version does not exist; the artifact lives in a repository the build does not declare | check the coordinates and version; declare the repository the project uses |
| `Could not transfer artifact ... status code: 401` or `403` | the private repository needs credentials | the person configures them in `~/.m2/settings.xml` (`<server>` with the repository ID) or `~/.gradle/gradle.properties`, or the CI secret; never in the project files and never in the chat |
| `Could not resolve dependencies ... offline` | the build runs offline and the cache lacks the artifact | run once online, or point to the internal mirror |
| `Non-resolvable parent POM` | the parent version does not exist, or the `relativePath` points to a wrong file | fix the parent version; `<relativePath/>` for parents from a repository |
| Gradle `Could not resolve all files for configuration ':compileClasspath'` | same as above, or a version catalog alias that does not exist | fix the coordinates or the alias in `libs.versions.toml` |

## Version conflicts

Symptoms: `NoSuchMethodError`, `NoSuchFieldError`, `NoClassDefFoundError`, `ClassNotFoundException`, `AbstractMethodError` at test or start-up time; enforcer `Dependency convergence error`; Gradle `Conflict(s) found for the following module(s)`.

1. Find who brings each version:
   - `mvn dependency:tree -Dverbose -Dincludes=<groupId>:<artifactId>`
   - `./gradlew dependencyInsight --dependency <artifactId> --configuration runtimeClasspath`
2. Fix, in this order of preference:
   1. Remove an explicit version that overrides the one the Spring Boot or Quarkus BOM manages.
   2. Align a family with its own BOM (`jackson-bom`, `netty-bom`, `testcontainers-bom`) in `dependencyManagement` or as a Gradle `platform(...)`.
   3. Pin the version in `dependencyManagement` (Maven) or with a `constraints {}` block (Gradle), with a comment saying why.
   4. Exclude the transitive dependency, as a last resort and with a comment.
3. A Spring Boot managed version changes only through its property (`<properties><jackson-bom.version>...`), and only to fix this cause (for example a security fix the person asked for).

## Plugins and lifecycle

| Symptom | Causes | Fix |
|---|---|---|
| `Plugin ... or one of its dependencies could not be resolved` | wrong plugin version or coordinates | use the version the parent manages, or a released one |
| `No plugin found for prefix 'x'` | the plugin is not declared and has no default group | use the full coordinates, or declare it in the build |
| `The packaging for this project did not assign a file to the build artifact` | `install` or `deploy` on a `pom` module, or a misconfigured jar plugin | check the module's packaging |
| Spring Boot `repackage` fails: `Unable to find main class` | several or no `main` methods | set `<mainClass>` / `springBoot { mainClass = ... }` |
| Enforcer rule fails (`requireJavaVersion`, `banDuplicatePomDependencyVersions`) | the rule found a real problem | fix the problem the rule names; never skip the enforcer |
| Gradle `Could not find method X()` or Kotlin DSL `Unresolved reference` | a plugin not applied, an API removed in a newer Gradle | apply the plugin; check the Gradle version's upgrade notes |
| Gradle configuration cache errors | a task reads the project at execution time | follow the error's link; the person decides whether to disable the cache for that task |

## Tests inside the build

| Symptom | Causes | Fix |
|---|---|---|
| `There are test failures` with assertion errors | the code or the test is wrong | read the failing assertion; fix the code if the behavior regressed, the test if the expectation is outdated by the plan |
| `Failed to load ApplicationContext` | a missing property, a bean that fails to create, a circular dependency, no database for the test | the deepest `Caused by:` names it; provide the test property, fix the bean, or use the right test slice |
| `Could not find a valid Docker environment` (Testcontainers) | Docker is not running or not reachable | environment, not code: say so; the person starts Docker or CI provides it |
| Tests pass locally and fail in CI (or the reverse) | time zone, locale, file ordering, ports, shared state between tests | pin the clock and the locale in the test; remove order dependencies |
| `ExecutionException The forked VM terminated without properly saying goodbye` | out of memory, `System.exit` in code under test | look for the crash dump; raise the fork memory only when the tests really need it |
| Surefire runs no tests (`Tests run: 0`) | JUnit 5 tests with an old surefire, or JUnit 4 and 5 mixed without the vintage engine | use the surefire version the parent manages; add `junit-vintage-engine` only for real JUnit 4 tests |
