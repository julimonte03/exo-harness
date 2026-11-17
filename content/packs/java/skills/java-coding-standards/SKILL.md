---
name: java-coding-standards
description: >-
  Java coding standards for Spring Boot and Quarkus services on Java 17 or
  later, read-only: naming, package layout, immutability and records,
  Optional, null-safety, exceptions, logging, collections and streams,
  generics, dependency injection, time and money, and test style with JUnit 5,
  AssertJ and Mockito. The project's own formatter and conventions come first.
  Gives numbered rules (JCS-n) that code is written against, and lists the
  deviations of existing code with path:line, without editing it. Use it when
  writing Java, when asking how Java code here should look, or when checking a
  class against coding conventions only (not bugs or security). Triggers:
  "Java conventions", "coding standards", "is this idiomatic Java", "should I
  use Optional here", "record or class", "how should I name this", "Java best
  practices", "check the style of this class".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-only
---

# java-coding-standards

## Result

- **When code is being written** (the apply phase, or the person's own work): the rules below, applied by whoever writes the code (`code-generation` in SDD).
- **When code is checked against the standards:** a list of deviations, each with `path:line`, the rule ID (`JCS-n`), what deviates and how it should look. This skill never edits the code.
- Good and bad examples of each rule are in `references/examples.md`.

## When

- Writing or changing Java code, answering "how should this be written here", or checking a class or a diff for conventions only.
- **Not for:** bugs, data access, security or concurrency problems in a change (skill:java-reviewer), build failures (skill:java-build-resolver).

## Project first

Before applying any rule here, read what the project already decided, and follow it where it differs:

1. Formatter and linter configs: `.editorconfig`, Checkstyle (`checkstyle.xml`), Spotless or google-java-format / palantir-java-format in the build, PMD or Error Prone rules.
2. `.exo/context.md`, Conventions.
3. The code around the change: naming, Lombok or not, how errors and logs look, how tests are named.

A rule of the project wins over a rule here. Do not report what the project's formatter decides (indentation, import order, line length): the formatter enforces it.

## Rules

| ID | Rule |
|---|---|
| JCS-1 | **Names say what things are.** Classes and records are nouns in PascalCase; methods are verbs in camelCase; constants UPPER_SNAKE_CASE; packages lowercase. Booleans read as questions (`isActive`, `canBorrow`). No abbreviations or one-letter names outside short lambdas and loop indexes. |
| JCS-2 | **Package by feature, small public surface.** Group by feature when the project does (`orders`, `billing`); classes are package-private unless another package needs them; no `util` dumping grounds. |
| JCS-3 | **Immutable by default.** `final` fields set in the constructor; records for DTOs, value objects, events and configuration properties; `List.copyOf` for incoming collections; no setters on domain objects, but methods that state the intention (`order.cancel()`). JPA entities are not records. |
| JCS-4 | **Optional only as a return type** for "may be absent". Never as a field, a parameter or inside a collection. No `get()` without a check: use `orElseThrow`, `map`, `ifPresent`, `orElse`. A method returning `Optional` never returns `null`. |
| JCS-5 | **No nulls across boundaries.** Return empty collections, not `null`. Validate inputs at the edge (`Objects.requireNonNull`, Bean Validation). Use the nullness annotations the project uses (JSpecify, Spring's `@NonNullApi`) consistently. |
| JCS-6 | **Exceptions that mean something.** Unchecked domain exceptions with a stable code; never an empty `catch`; never catch `Exception` or `Throwable` except at the outer edge; keep the cause (`new X(message, cause)`); no exceptions for normal control flow; try-with-resources for every `AutoCloseable`; no `printStackTrace()`. |
| JCS-7 | **Logging through SLF4J.** Parameterized messages (`log.info("Order {} cancelled", id)`), never string concatenation or `System.out`/`System.err`. Log an exception once, where it is handled, with the exception as the last argument. No secrets or personal data in logs (`.exo/shared/data-protection.md`). |
| JCS-8 | **Collections and streams for clarity.** Declare interfaces (`List`, `Map`); immutable factories (`List.of`, `Map.of`); streams for transformations without side effects, `toList()` on Java 16+; a plain loop when it reads better. No parallel streams in request handling. |
| JCS-9 | **Modern Java where it helps.** `var` when the type is obvious from the right side; switch expressions; pattern matching for `instanceof` and records; sealed interfaces for closed hierarchies; text blocks for SQL, JSON and long strings. |
| JCS-10 | **Generics without holes.** No raw types; wildcards where they widen an API (`List<? extends Item>` to read); no unchecked casts without a comment saying why they are safe. |
| JCS-11 | **Constructor injection.** Dependencies are `private final` fields set through the constructor (Lombok `@RequiredArgsConstructor` when the project uses Lombok); no field `@Autowired`, no static access to beans, no mutable state in singleton beans. In Quarkus, follow its injection style. |
| JCS-12 | **Time and money done right.** `java.time` only, never `Date` or `Calendar`; the current time from an injected `Clock` or the project's time helper, so tests can pin it; money as `BigDecimal` with an explicit scale and rounding, or as a `long` of minor units (cents), never `double` or `float`; `Locale.ROOT` for case conversion of identifiers. |
| JCS-13 | **equals and hashCode on purpose.** Records get them for free; value objects implement both; JPA entities compare by identifier or a business key, and never use Lombok `@Data`, `@EqualsAndHashCode` or `@ToString` that touch lazy relations. |
| JCS-14 | **Small methods, no magic numbers.** A method does one thing at one level of abstraction; named constants instead of literals (`MAX_COPIES_PER_TITLE`, not `20`); early returns over deep nesting. |
| JCS-15 | **Tests that read as specifications.** JUnit 5 with AssertJ and Mockito; one behavior per test, named for it (`rejectsLoanWhenLimitReached`, or `@DisplayName`); arrange, act, assert; parameterized tests for tables of cases; a fixed clock, never `Thread.sleep`; mock collaborators, not value objects. |
| JCS-16 | **Comments say why.** Javadoc on public API that is not obvious; no commented-out code; a `TODO` carries a ticket or an owner. |

## Spring Boot and Quarkus specifics

- Configuration as typed records (`@ConfigurationProperties` in Spring, `@ConfigMapping` in Quarkus) instead of many scattered `@Value` fields.
- `@Transactional` on public service methods, never on private ones or on controllers.
- Controllers stay thin: map, validate, call one service method, map back.
- The detail of each framework is in skill:springboot-patterns; the Quarkus equivalences are in skill:backend-engineering.

## Checking code against the standards

1. Scope: the files the person names, or the Java files of the diff (`git diff --name-only <base>...HEAD -- '*.java'`).
2. Read each file in full. For each deviation, note the line, the rule ID and the fix.
3. Skip what the project's formatter or its own conventions decide differently; say once which project rules you followed.
4. Severity: these are convention findings, **Low** by default. **Medium** when the deviation hides a defect: a swallowed exception (JCS-6), `double` for money (JCS-12), `Optional.get()` without a check (JCS-4), mutable state in a singleton (JCS-11).
5. Do not edit. If the person wants the fixes, they ask for them, and then the code changes follow these rules.

## Return

```markdown
Followed the project's rules: palantir-java-format (build.gradle.kts:18), Lombok for constructors.

| Severity | path:line | Rule | Deviation | Should be |
|---|---|---|---|---|
| Medium | src/main/java/com/example/billing/InvoiceTotals.java:27 | JCS-12 | Totals summed as double | long cents, or BigDecimal with scale 2 and HALF_EVEN |
| Medium | src/main/java/com/example/billing/InvoiceTotals.java:40 | JCS-6 | catch (Exception e) {} hides failures | catch the specific exception and rethrow with the cause |
| Low | src/main/java/com/example/billing/InvoiceTotals.java:12 | JCS-11 | Field injection with @Autowired | private final field and constructor injection |
| Low | src/main/java/com/example/billing/InvoiceTotals.java:33 | JCS-7 | System.out.println for diagnostics | log.debug("...", value) through SLF4J |

4 deviations: 0 High, 2 Medium, 2 Low. No file changed.
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "java-coding-standards", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"java-coding-standards"'
```

## Before you finish

- [ ] You read the project's formatter, linter and conventions first, and said which ones you followed.
- [ ] Every deviation has `path:line`, a `JCS-n` rule and how it should look.
- [ ] Formatter matters (spacing, import order, line length) are not reported.
- [ ] Severities are Low unless the deviation hides a defect.
- [ ] No file was changed.
