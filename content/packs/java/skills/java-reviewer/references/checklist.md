# Java review checklist

Go category by category over the changed files and the code they call. Report only what applies, with its rule ID.

## JR-CORR Correctness

- [ ] The change does what the spec, the ticket or the person says, including its error cases.
- [ ] A new code path does not bypass a rule that the existing service or entity enforces (limits, states, ownership): the new code calls the domain method instead of changing fields itself.
- [ ] `Optional.get()`, unboxing of a nullable `Integer`, and values from maps or repositories that can be null are handled.
- [ ] Boundaries: `<` versus `<=`, empty collections, first and last page, zero and negative amounts.
- [ ] Arithmetic: `int` overflow on multiplication (`Math.multiplyExact` or `long`), division by zero, money in `double`.
- [ ] `BigDecimal` compared with `compareTo`, not `equals` (`2.0` and `2.00` are not equal).
- [ ] Time: the project's clock or an injected `Clock`, not `LocalDate.now()` scattered around; time zones explicit at the boundaries.
- [ ] `equals` and `hashCode` consistent; no mutable fields in a hash key.
- [ ] Strings compared with `equals`, case-insensitive comparisons with `Locale.ROOT`.

## JR-LAYER Layering

- [ ] Controllers map and delegate; they do not call repositories or hold business rules.
- [ ] Entities do not leave the service as API responses: DTOs or records instead (avoids leaking fields, lazy-loading errors and mass assignment).
- [ ] Request bodies are validated (`@Valid` with constraints) before reaching the service.
- [ ] A new import between feature packages does not create a dependency cycle.

## JR-DATA Data access

### JPA and Hibernate

- [ ] No repository call or lazy relation access inside a loop over results (N+1): use a fetch join, an `@EntityGraph`, `findAllById` or a projection.
- [ ] No `findAll()` without paging or a bound on a table that grows.
- [ ] `@ManyToOne` and `@OneToOne` are `fetch = LAZY`; collections are not `EAGER`.
- [ ] JPQL and native queries use named or positional parameters; nothing user-controlled is concatenated (`CWE-89`). Sort fields from the request are allow-listed.
- [ ] `@Modifying` bulk queries clear or refresh the persistence context when entities are used after them.
- [ ] A new query has the index it needs, in a new migration.
- [ ] New or changed columns have their migration, and the entity mapping matches it (`ddl-auto=validate` would pass).
- [ ] No applied migration is edited: Flyway checksums and Liquibase changesets break on databases that already ran it. Add a new migration instead.
- [ ] `@Enumerated(EnumType.STRING)`, never ordinal.

### Panache (Quarkus)

- [ ] `find("field = ?1", value)` or named parameters; never a query string built with `+`.
- [ ] Writes inside `@Transactional` (`jakarta.transaction.Transactional`).
- [ ] `listAll()` and `streamAll()` bounded or paged on large tables.

### MongoDB

- [ ] Queries built with `Criteria`/`Query` or typed repositories; no JSON query text built from input; no `$where` or server-side JavaScript with input (`CWE-943`).
- [ ] Regex from user input is quoted (`Pattern.quote`) and bounded.
- [ ] Indexes declared for new query patterns; unbounded `find` avoided.
- [ ] Multi-document transactions only where the deployment supports them (replica set).

## JR-TX Transactions

- [ ] Every write runs inside a transaction: a public `@Transactional` method called from another bean. Changes to a managed entity outside one are never flushed.
- [ ] `@Transactional` is not on a private method, and not called from the same class (self-invocation skips the proxy).
- [ ] Checked exceptions that must roll back are declared in `rollbackFor`.
- [ ] Read paths use `readOnly = true` where the project does.
- [ ] No HTTP call, message send or email inside a database transaction; side effects after commit.
- [ ] Contended entities have `@Version`, or the update is atomic (`where available > 0`), and the conflict becomes a 409 or a retry.

## JR-SEC Security

| Look for | CWE | OWASP Top 10:2025 |
|---|---|---|
| A new endpoint without authentication, or without an ownership check on the object it reads or changes | CWE-862, CWE-639 | A01:2025 Broken Access Control |
| `RestTemplate`, `WebClient` or `URL.openStream` on a URL from the request (SSRF) | CWE-918 | A01:2025 Broken Access Control |
| `permitAll()` on broad patterns, Actuator endpoints exposed, CSRF disabled with cookie sessions, CORS `*` with credentials | CWE-16, CWE-352 | A02:2025 Security Misconfiguration |
| `MessageDigest` MD5 or SHA-1 for passwords or signatures, `Cipher` with ECB or DES, `new Random()` for tokens | CWE-327, CWE-330 | A04:2025 Cryptographic Failures |
| Query, command or expression built from input: JPQL, SQL, `Runtime.exec`, `ProcessBuilder` with a shell, SpEL from input, LDAP filters | CWE-89, CWE-78, CWE-917 | A05:2025 Injection |
| Credentials compared with `equals` (timing), no lockout on sign-in | CWE-208, CWE-307 | A07:2025 Authentication Failures |
| `ObjectInputStream.readObject`, Jackson default typing, `XMLDecoder` on untrusted input | CWE-502 | A08:2025 Software or Data Integrity Failures |
| Tokens, passwords or personal data in logs; security events not logged | CWE-532, CWE-778 | A09:2025 Security Logging and Alerting Failures |
| `catch (Exception e)` that returns a default or grants access; stack traces in responses | CWE-755, CWE-209 | A10:2025 Mishandling of Exceptional Conditions |
| `DocumentBuilderFactory`, `SAXParserFactory` or `XMLInputFactory` without disabling external entities | CWE-611 | A02:2025 Security Misconfiguration |
| `Paths.get(base, input)` or `new File(input)` without normalizing and checking the base | CWE-22 | A01:2025 Broken Access Control |
| Secrets in code, `application*.yml` or tests | CWE-798 | A07:2025 Authentication Failures |

## JR-CONC Concurrency

- [ ] Singleton beans hold no mutable request state (fields assigned in methods).
- [ ] Check-then-act sequences (`exists` then `save`, read then decrement) are protected by a unique constraint, a lock or an atomic update.
- [ ] No shared `SimpleDateFormat`, `HashMap` written from several threads, or lazy singletons without safe publication.
- [ ] `@Async` and `CompletableFuture.supplyAsync` use a configured executor, not the common pool; security and transaction context are not assumed to cross threads.
- [ ] On virtual threads (Java 21), long `synchronized` blocks around I/O are avoided where the JDK still pins.

## JR-RES Resources

- [ ] `InputStream`, `Reader`, JDBC objects, `Stream` from `Files.lines` closed with try-with-resources.
- [ ] HTTP clients have connect and read timeouts; retries only on idempotent calls.
- [ ] Thread pools and schedulers are beans with a bounded size, shut down with the context.

## JR-ERR Errors

- [ ] No empty `catch`, no `catch (Exception)` returning a default value or `null`.
- [ ] Exceptions are rethrown with their cause; logged once, where they are handled.
- [ ] Business errors map to 4xx through the error handler, not to 500.
- [ ] Error responses carry no stack trace, SQL or internal names.

## JR-TEST Tests

- [ ] Each new behavior and each new error path has a test that fails without the change.
- [ ] Assertions check the behavior, not only that no exception was thrown.
- [ ] No `Thread.sleep`, real clock, real network or shared mutable state between tests.
- [ ] The smallest Spring context that proves it: plain unit test, `@WebMvcTest`, `@DataJpaTest`, then `@SpringBootTest`.
- [ ] Repository queries are tested against the real database engine (Testcontainers) when the query uses vendor features.
