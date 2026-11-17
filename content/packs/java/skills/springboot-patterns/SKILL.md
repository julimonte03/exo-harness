---
name: springboot-patterns
description: >-
  Spring Boot 3 architecture and patterns: typed configuration with
  @ConfigurationProperties records and profiles, constructor injection and
  bean design, controller-service-repository layers with DTOs, request
  validation with Bean Validation, centralized error handling with problem
  details, scheduling, async work and after-commit events, caching, HTTP
  clients with timeouts, observability with Actuator and Micrometer, and
  tests with slices (@WebMvcTest, @DataJpaTest) and Testcontainers. Use it
  when building or changing a Spring Boot feature, binding settings from
  application.yml, wiring beans, adding validation or error handling,
  exposing health and metrics, or choosing how to test a Spring component.
  Triggers: "Spring Boot", "@ConfigurationProperties", "make this
  configurable", "profiles", "bean validation", "@ControllerAdvice",
  "@WebMvcTest", "Actuator", "how do I structure this Spring service".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-write
---

# springboot-patterns

## Result

- Spring Boot code that follows the project's structure and these patterns: typed configuration, constructor injection, thin controllers, validated input, one error handler, observable behavior.
- Every change comes with a test at the smallest level that proves it (a plain unit test or a slice), and the command to run it.
- Code examples are in `references/examples.md`; the test slices in `references/testing.md`.

## When

- Building or changing a feature in a Spring Boot service: configuration, beans, controllers, validation, errors, scheduled or async work, caching, outbound HTTP, health and metrics, tests.
- **In SDD:** skill:backend-engineering loads it in design and apply for Spring work.
- **Not for:** JPA mappings and queries (skill:jpa-patterns), Spring Security (skill:springboot-security), API contract decisions (skill:backend-and-api). In Quarkus, use the equivalences in skill:backend-engineering.

## Read first

1. The Boot version (the parent or the plugin) and the starters in the build: some features below need a minimum version, noted where they apply.
2. `application.yml` or `.properties`, the profile files, and how secrets arrive (`${ENV}` placeholders).
3. One existing feature end to end: controller, service, repository, error handler, and its tests. Copy its style.
4. `.exo/context.md`: commands and conventions.

## 1. Configuration

- **Group related settings in a record** with `@ConfigurationProperties(prefix = "...")`, register it (`@EnableConfigurationProperties` or `@ConfigurationPropertiesScan`), and inject the record. Scattered `@Value` fields are fine only for a single, isolated value.
- **Fail at start-up, not at the first request:** `@Validated` on the record with constraints (`@NotBlank`, `@Min`, `@Positive`); Bean Validation must be on the classpath (`spring-boot-starter-validation`).
- **Profiles:** defaults in `application.yml`, overrides in `application-<profile>.yml`, the active profile from the environment. Secrets never in files: `${DB_PASSWORD}`, with no default for secrets.
- Defaults that are safe in production; document each property next to it.

## 2. Beans and injection

- Constructor injection with `final` fields (Lombok `@RequiredArgsConstructor` when the project uses it). No field `@Autowired`.
- Third-party objects as `@Bean` methods in a `@Configuration` class; a `Clock` bean so time can be pinned in tests.
- Adapters behind interfaces (a notifier, a payment client); choose the implementation with `@ConditionalOnProperty` or a profile, not with `if` statements.
- No circular bean dependencies (Boot forbids them by default): extract the shared part or publish an event.
- Singleton beans hold no request state.

## 3. Layers

- **Controller:** maps HTTP to a call, validates input (`@Valid`), maps the result to a response DTO. No business rules, no repositories.
- **Service:** one public method per use case, the transaction boundary (`@Transactional`, `readOnly = true` for queries), domain rules through the entities.
- **Repository:** Spring Data interfaces; see skill:jpa-patterns.
- DTOs are records; mapping by hand or with the mapper the project uses. Entities never go out through the API.

## 4. Validation

- `spring-boot-starter-validation` in the build (Boot 3 starters do not include it).
- Constraints on request records (`@NotBlank`, `@Size`, `@Positive`, `@Email`, `@Pattern`), `@Valid @RequestBody` in the controller; `@Validated` on the controller class for constraints on `@RequestParam` and `@PathVariable`.
- Custom rules as a `ConstraintValidator`. Rules that depend on the state of the system (limits, duplicates) stay in the domain or the service, not in annotations.
- Imports are `jakarta.validation.*` on Boot 3.

## 5. Errors

- **One `@RestControllerAdvice`** maps exceptions to responses. Keep the project's error body if it has one; otherwise use `ProblemDetail` (RFC 9457) and `spring.mvc.problemdetails.enabled=true`.
- Map, at least: `MethodArgumentNotValidException` and `HandlerMethodValidationException` (Boot 3.2+) to 400 with the invalid fields; not found to 404; business rules to the project's status (409 or 422); optimistic lock failures to 409; anything else to 500 with a generic message, logged once with its stack trace.
- `server.error.include-stacktrace=never` and `include-message=never` outside development.

## 6. Scheduled and async work

- `@EnableScheduling`; `@Scheduled(cron = "${...}")` with the expression in configuration; jobs idempotent, so a retry or a second run does no harm. With several instances, a lock (ShedLock or the project's choice) so one runs.
- `@Async` and `@EnableAsync` with a configured `ThreadPoolTaskExecutor`, not the default; on Java 21 and Boot 3.2+, `spring.threads.virtual.enabled=true` is an option for blocking I/O.
- Side effects after the transaction commits: publish an event and handle it with `@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)`.

## 7. Caching

- `@EnableCaching` with a real provider (Caffeine, Redis) and a time to live per cache; `@Cacheable` with explicit cache names and keys; `@CacheEvict` or `@CachePut` on writes.
- Never cache per-user or authorization-dependent data under a shared key. Calls from the same class skip the cache proxy, like transactions.

## 8. Outbound HTTP

- `RestClient` (Boot 3.2+) or `WebClient`, built from the auto-configured builder; declarative clients with `@HttpExchange` when the project uses them.
- Connect and read timeouts always (`spring.http.client` settings on Boot 3.4+, or the request factory); retries with backoff only for idempotent calls; a circuit breaker when the project uses Resilience4j.
- Base URLs and credentials from configuration; map remote errors to the project's exceptions.

## 9. Observability

- Actuator: expose only what is needed (`management.endpoints.web.exposure.include=health,info,prometheus`); never `*` on a public port. Health probes for Kubernetes (`management.endpoint.health.probes.enabled=true`); a `HealthIndicator` per critical dependency. Who may see what is in skill:springboot-security.
- Metrics with Micrometer: a timer or counter per use case, low-cardinality tags (no IDs or emails).
- Logs: SLF4J, one line per event, a correlation or trace ID (Micrometer Tracing adds it); structured JSON when the project ships logs to a collector (`logging.structured.format.console` on Boot 3.4+). No personal data or secrets (`.exo/shared/data-protection.md`).

## 10. Tests

| What | Use |
|---|---|
| Domain and service logic | a plain JUnit test with Mockito, no Spring context |
| A controller: mapping, validation, status codes, error bodies | `@WebMvcTest(XController.class)` with `MockMvc` (or `MockMvcTester` on Boot 3.4+), services mocked with `@MockitoBean` (Boot 3.4+) or `@MockBean` |
| Repositories, mappings, migrations | `@DataJpaTest` with Testcontainers and `@ServiceConnection` (Boot 3.1+) for the real engine |
| JSON shape of a DTO | `@JsonTest` |
| Configuration binding and validation | `ApplicationContextRunner` with the properties |
| Wiring across layers | a few `@SpringBootTest` tests, not one per feature |

- A fixed `Clock`, no `Thread.sleep`, no real network. Avoid `@DirtiesContext`: it restarts the context and slows the suite.
- Write the test even when you cannot run it, give the exact command (`./mvnw -B test -Dtest=<Class>` or `./gradlew test --tests <Class>`), and mark it not run.

## Return

```markdown
Change: order cancellation settings are configurable and validated at start-up.
- CancellationProperties.java (new): record bound to `shop.cancellation`, @Validated, window @Positive.
- ShopApplication.java:14: registered with @EnableConfigurationProperties.
- application.yml:22: `shop.cancellation.window-hours: 24`.
- OrderService.java:40: reads the window from the record instead of the constant.
- pom.xml: spring-boot-starter-validation (version from the parent).
Tests: CancellationPropertiesTest (ApplicationContextRunner: binds; rejects 0), OrderServiceTest updated.
Run: ./mvnw -B test -Dtest='CancellationPropertiesTest,OrderServiceTest' — not run: this agent cannot run Maven here.
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "springboot-patterns", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"springboot-patterns"'
```

## Before you finish

- [ ] The change follows the structure and style of an existing feature of the project.
- [ ] Settings are typed, validated at start-up, and secrets come from the environment.
- [ ] Controllers are thin, input is validated, and errors go through the one error handler.
- [ ] Side effects run after commit; outbound calls have timeouts.
- [ ] Each change has a test at the smallest level, and the answer gives the command (run, or marked not run).
