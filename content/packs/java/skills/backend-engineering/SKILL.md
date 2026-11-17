---
name: backend-engineering
description: >-
  Backend engineering router for Java and Spring services: decides where new
  code belongs (layers or hexagonal ports and adapters), applies the
  technology-agnostic principles (DDD where the domain earns it, SOLID,
  transaction boundaries, idempotency, error handling) and loads the skill of
  the java pack that fits the task: API design, Spring Boot structure, JPA,
  Spring Security, Java standards, code review, build failures, verification
  or the dependency scan. It is the stack router that the SDD design and apply
  phases load. Use it when starting backend work on a Java or Kotlin service,
  when deciding where logic should live, or when unsure which java skill
  applies. Triggers: "where should this logic go", "add a feature to the
  service", "design the backend for", "layered or hexagonal", "which pattern
  should I use", "plan this backend change", "backend task".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: write-code
---

# backend-engineering

## Result

- A short routing decision for the task: the stack you detected, where each piece of the change goes, the principles that apply, and the java skills you loaded, each read in full.
- The work itself then follows those skills: design.md in the design phase, code and tests in the apply phase, or an answer outside the SDD cycle.
- The project's own conventions win over the defaults here: `.exo/context.md` and the code that already exists.

## When

- **SDD design and apply:** this is the stack router of `.exo/shared/phase-skill-map.md`, Required in both phases when the `java` pack is installed. `sdd-design` and `code-generation` load it.
- **Outside the cycle:** any backend task on a JVM service (Spring Boot, Quarkus, plain Java or Kotlin) where you need to decide where code goes or which skill applies.
- **Not for:** frontend work, infrastructure (Dockerfiles, pipelines) or questions that only read the code. When the task already names one java skill's job (a failing build, a review of a diff), load that skill directly.

## 1. Read the project

Read these before deciding anything, and cite `path:line` for what you rely on:

1. `.exo/context.md`: Stack, Commands, Conventions, Architecture and Risks. Without it, read the build file and the README.
2. **Build:** `pom.xml` (Maven) or `build.gradle(.kts)` with `settings.gradle(.kts)` (Gradle); the wrapper (`mvnw`, `gradlew`); the Java version (`java.version`, `maven.compiler.release`, a toolchain block).
3. **Framework:** Spring Boot (`spring-boot-starter-parent` or the `org.springframework.boot` plugin) or Quarkus (`io.quarkus` platform BOM or plugin). For Quarkus, use the equivalences in `references/principles.md`.
4. **Persistence and security:** `spring-boot-starter-data-jpa`, Hibernate, Panache, MongoDB; `spring-boot-starter-security` or OAuth2 starters; the migration tool (Flyway `db/migration`, Liquibase changelogs).
5. **Structure:** package by feature (`books`, `loans`) or by layer (`controller`, `service`, `repository`); a hexagonal layout (`domain`, `application`, `adapter`, `port`); the error handler (`@RestControllerAdvice`); how tests are written.

## 2. Route the task

Load only what the task needs: usually one skill, at most three. Read each `SKILL.md` in full before working.

| The task is about | Load |
|---|---|
| Endpoints, resources, status codes, error bodies, pagination, versioning, the OpenAPI contract | skill:backend-and-api |
| Spring configuration, profiles, beans, layers, validation, exception handling, scheduling, Actuator, test slices | skill:springboot-patterns |
| Entities, relationships, queries, N+1, transactions, locking, Flyway or Liquibase migrations | skill:jpa-patterns |
| Authentication, authorization, the filter chain, CSRF, CORS, JWT, OAuth2, secrets | skill:springboot-security, with skill:secure-coding-baseline when installed |
| Writing Java: naming, records, Optional, exceptions, logging, tests | skill:java-coding-standards |
| Reviewing a Java diff or pull request | skill:java-reviewer |
| A build that fails: compile errors, dependencies, plugins, tests in the build | skill:java-build-resolver |
| Checking a change before a PR or a release | skill:springboot-verification |
| A changed dependency or lockfile, or a request for a vulnerability scan | skill:security-scan-jkp |

- **They count toward the limit.** Inside an SDD phase, the skills this router loads count toward the limit of 5 skills per delegation of `.exo/shared/phase-skill-map.md`, after the Required and Conditional skills of the phase. When the limit is reached, keep the ones the task needs most and say which ones you left out.
- **A skill that is not installed** degrades as `.exo/shared/skill-resolver.md` says: say `<pack>/<skill> not installed — applying inline criteria` (for example `security/secure-coding-baseline`), apply its inline criteria from the last table of `.exo/shared/phase-skill-map.md`, and record it. A skill of this pack missing while this router is installed means an incomplete install: say so, and suggest `exo doctor` and `exo sync`.

## 3. Decide where the code goes

Follow the structure the project already has. The defaults below apply only where it has none; the detail and examples are in `references/principles.md`.

- **Layered:** controller (HTTP, validation, mapping to DTOs) → service (one use case per public method, the transaction boundary) → repository. Controllers never call repositories, and entities never leave the service as API responses.
- **Hexagonal:** the domain and the use cases do not import web, persistence or messaging frameworks. Ports are interfaces owned by the core; adapters implement them at the edge. Dependencies point inward.
- **Package by feature:** new behavior goes in the feature it belongs to. A new concept with its own lifecycle (a reservation, an invoice) gets its own package. Do not add a dependency between features that would close a cycle; depend on an interface or an identifier instead.
- **DDD where the domain earns it:** invariants live in the entity's methods, not in the services around it; value objects for concepts with rules (an ISBN, an amount of money); aggregates are the consistency boundary, and they reference other aggregates by identifier. A plain CRUD feature does not need this ceremony.
- **SOLID in practice:** one reason to change per class; depend on interfaces at the boundaries (a notifier, a payment gateway); extend with a new strategy class rather than a new boolean flag; no god services.

## 4. Apply the principles

- **Transactions:** the service method is the boundary; one aggregate per transaction where possible; read-only transactions for queries. No remote call inside a database transaction: send messages and notifications after commit, or through an outbox.
- **Idempotency:** GET, PUT and DELETE are idempotent by definition. A POST that charges, books or sends something takes an idempotency key or relies on a natural key with a unique constraint. Message consumers deduplicate by message ID. Retries are safe only on idempotent operations.
- **Concurrency:** an aggregate that two requests can change at once (stock, balances, seats) needs optimistic locking or an atomic conditional update. Never check-then-act without one.
- **Errors:** domain failures are exceptions with a stable, machine-readable code, mapped once at the edge to HTTP. Validation errors are 400; not found is 404; a conflict with the current state is 409 or the project's existing choice (some projects use 422 for broken business rules). Never swallow an exception, and never send stack traces or SQL to a client.
- **Security and data:** authorization on every entry point and every object; secrets from the environment; no personal data in logs (`.exo/shared/data-protection.md`).
- **Observability:** structured logs with a correlation ID, metrics for the use case, health checks for each dependency.

## 5. Hand off to the phase

- **Design:** the decisions go into design.md, which `sdd-design` owns: Architecture Overview and Modules / Files (where the code goes), Data Shapes, Error Handling (codes and statuses), Risks & Mitigations (concurrency, idempotency). This skill does not write design.md on its own.
- **Apply:** `code-generation` writes the code and the tests by the frozen plan, following the skills you loaded. Anything outside the plan is a follow-up, not code.
- **Outside the cycle:** give the routing decision and the plan in the answer; write code only when the person asked for it.

## Return

Start the answer, or the notes of the phase envelope, with the routing block:

```markdown
Routing: Spring Boot 3.4 (Gradle, Java 21), JPA with Liquibase, package by layer, JWT resource server.
Skills: jpa-patterns (locking, migration), backend-and-api (endpoint, errors), springboot-security (who may cancel).
Where: OrderController POST /orders/{id}/cancellation -> OrderService.cancel (transaction boundary);
the refund goes through the PaymentGateway port after commit (@TransactionalEventListener), never inside the transaction.
Principles: @Version on Order so a cancel and a shipment cannot both win; the cancellation is idempotent
(cancelling a cancelled order returns it unchanged); order_not_cancellable -> 409 problem details.
```

Then the work the task asked for.

## Record

Inside an SDD change, an inline phase records the router and every skill it loaded (`.exo/shared/capability-attribution.md`); a subagent lists them in its envelope notes instead:

```bash
exo change record <change> --add capabilities_used '{"name": "backend-engineering", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add skills_used '"backend-engineering"'
exo change record <change> --add capabilities_used '{"name": "jpa-patterns", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'`, with the quotes (`.exo/shared/sdd-phase-common.md`, section I). Outside a change, record nothing.

## Before you finish

- [ ] You read `.exo/context.md` (or the build file and README) and followed the existing structure.
- [ ] The routing block names the stack, where each piece goes and the skills loaded.
- [ ] Each loaded skill was read in full; a missing one was declared with its degradation sentence.
- [ ] Transaction boundary, concurrency, idempotency and error codes are decided for the change, or marked not applicable.
- [ ] No code was written outside the plan or without the person asking for it.
