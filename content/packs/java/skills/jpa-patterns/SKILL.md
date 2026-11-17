---
name: jpa-patterns
description: >-
  JPA and Hibernate patterns for Spring Data and Quarkus Panache: entity and
  value object mapping, relationships and fetch strategies, finding and fixing
  N+1 queries, transaction boundaries, optimistic and pessimistic locking
  against lost updates, projections and pagination, batch writes, indexes,
  and schema migrations with Flyway or Liquibase that never edit an applied
  script. Each change comes with its test. Use it when designing or changing
  entities, repositories or queries, when a query or a job gets slow or runs
  too many queries, on LazyInitializationException, lost updates or two users
  taking the same item, or when writing a migration. Triggers: "N+1",
  "LazyInitializationException", "JPA entity", "Hibernate mapping",
  "optimistic locking", "add a migration", "Flyway", "Liquibase", "the query
  is slow", "fetch join", "race condition on update".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: write-code
---

# jpa-patterns

## Result

- Mappings, queries, locks and migrations that keep the data correct and the number of queries bounded, in the style of the project's existing entities and with its migration tool.
- Each change with a test that proves it (a repository slice against the real database engine when possible), and the command to run it.
- Code recipes are in `references/recipes.md`; migration rules and examples in `references/migrations.md`.

## When

- Designing or changing entities, relationships, repositories or queries; a slow query or job; `LazyInitializationException`; lost updates or double booking; a new or changed column or index.
- **In SDD:** skill:backend-engineering loads it in design (Data Shapes, Migration / Backwards Compatibility, Risks & Mitigations) and in apply.
- **Not for:** the API shape (skill:backend-and-api), Spring wiring in general (skill:springboot-patterns).

## Read first

1. The entities and repositories the task touches, and one or two neighbours, to copy their style (Lombok or not, ID strategy, how invariants are enforced).
2. The migrations folder and tool: Flyway (`src/main/resources/db/migration/V<n>__<description>.sql`) or Liquibase (`db/changelog/`). The last version number.
3. Persistence config: `spring.jpa.hibernate.ddl-auto` (should be `validate` or `none` outside local runs), `spring.jpa.open-in-view` (should be `false`), batch settings, the database vendor.
4. How tests reach the database: Testcontainers, an embedded database, or none.

## 1. Entities

- A protected no-argument constructor for JPA, a public constructor or factory that creates a valid object, and methods that keep the invariants (`order.cancel()`, `book.checkOutCopy()`). No public setters for fields with rules.
- `@Enumerated(EnumType.STRING)`, never ordinal. Column definitions (`nullable`, `length`, `unique`) match the migration.
- Value objects as `@Embeddable` or through an `AttributeConverter`. Money as `long` minor units or `BigDecimal` with a column scale.
- IDs: `IDENTITY` is simple but disables JDBC insert batching; `SEQUENCE` (with an allocation size that matches the database sequence) allows it.
- No Lombok `@Data`, `@EqualsAndHashCode` or `@ToString` over relations. `equals` by identifier with a constant `hashCode`, or by a natural business key.

## 2. Relationships and fetching

- `@ManyToOne(fetch = FetchType.LAZY)` always (the JPA default is eager); collections stay lazy.
- One owning side; `mappedBy` on the other; helper methods keep both sides in sync.
- Cascade only from an aggregate root to its own parts; `orphanRemoval = true` for composition. Never cascade REMOVE across aggregates or on `@ManyToMany`.
- A many-to-many with attributes is an entity of its own.
- **Referencing another aggregate by ID** (a `Long customerId` instead of a `@ManyToOne Customer`) is a valid design: it keeps aggregates apart, at the cost of loading the other side explicitly. Respect the project's choice.

## 3. N+1 queries

**Detect:** a repository call or a lazy relation access inside a loop over query results; SQL logging (`logging.level.org.hibernate.SQL=debug`) or Hibernate statistics showing one query per row; a job that gets slower as data grows.

**Fix,** choosing the smallest that works:

| Situation | Fix |
|---|---|
| Entities with a lazy relation you always need here | `join fetch` in a JPQL query, or `@EntityGraph(attributePaths = ...)` on the repository method |
| Entities referenced by ID (no relation) | collect the IDs, load them once with `findAllById(ids)`, and map by ID |
| Many parents each with a collection | `@BatchSize` on the collection or `hibernate.default_batch_fetch_size` |
| A read model (a report, a list screen) | a projection: an interface or a record with a constructor expression, selecting only the columns needed |

- Do not fetch-join a collection and paginate in the same query: Hibernate paginates in memory (warning HHH90003004). Page the parent IDs first, then fetch.
- Prove it with a test that counts queries, or at least with the SQL log, before and after.

## 4. Transactions

- The boundary is the public service method of the use case; `readOnly = true` for queries.
- Writes to managed entities are saved at commit only inside a transaction; outside one, the change is lost.
- `@Transactional` does not apply to private methods or to calls from the same class (self-invocation skips the proxy).
- Checked exceptions do not roll back unless listed in `rollbackFor`.
- `LazyInitializationException` means the service did not load what the caller needs: fetch it in the query. Never fix it with `open-in-view: true` or `FetchType.EAGER`.
- No remote calls inside a database transaction; side effects after commit.
- Quarkus uses `jakarta.transaction.Transactional`.

## 5. Locking and lost updates

When two requests can change the same row (stock, seats, balances, counters), a plain read-modify-write loses one update or breaks an invariant. Pick one:

| Option | How | Fits |
|---|---|---|
| Optimistic lock | a `@Version` field (`long`), its column in a migration (`NOT NULL DEFAULT 0`), and the failure (`ObjectOptimisticLockingFailureException` in Spring, `OptimisticLockException` in JPA) mapped to 409 or retried a bounded number of times | most cases: conflicts are rare |
| Atomic conditional update | `update Product p set p.stock = p.stock - 1 where p.id = :id and p.stock > 0` with `@Modifying`; zero rows updated means the item is gone | a hot counter; no entity logic needed |
| Pessimistic lock | `@Lock(LockModeType.PESSIMISTIC_WRITE)` with a lock timeout hint, in a short transaction | conflicts are frequent and retries are expensive |
| Unique constraint | a unique index on the natural key, and the violation mapped to 409 | preventing duplicates (one active reservation per member and title) |

A check constraint in the database (`stock >= 0`) is a safety net, not a lock: two transactions can both write a valid value computed from the same old one. Test the race with two transactions or two threads.

## 6. Queries

- Derived queries for simple lookups; `@Query` with named parameters for the rest; Specifications or Criteria for dynamic filters. Never concatenate input into JPQL or SQL.
- Projections for read models; entities only when you will change them.
- `Pageable` with a stable sort (a unique tie-breaker such as the ID); `Slice` instead of `Page` when the count query is expensive.
- Large exports stream (`Stream<T>` with a read-only transaction, or keyset pages), never `findAll()`.
- `@Modifying(clearAutomatically = true)` for bulk updates when managed entities are used afterwards.

## 7. Batch writes

`spring.jpa.properties.hibernate.jdbc.batch_size` (for example 50), `order_inserts` and `order_updates`, `SEQUENCE` IDs, and `flush()` plus `clear()` every batch in long loops.

## 8. Migrations

The full rules are in `references/migrations.md`. The ones that matter most:

- **Never edit a migration that may have run anywhere** (merged, deployed, or shared): Flyway fails validation on the checksum and Liquibase on the changeset. Add the next version: `V<next>__<what_it_does>.sql`.
- The entity change and its migration go in the same change; `ddl-auto=validate` in tests catches drift.
- Changes are backwards compatible with the running version (expand, migrate, contract): add a nullable column or one with a default, backfill, then add the constraint in a later migration; rename in two releases.
- Every new query predicate or foreign key gets its index. On large PostgreSQL tables, create it concurrently, which must run outside a transaction (the tool's per-script setting).

## 9. Tests

- `@DataJpaTest` for repositories and mappings; against the real engine with Testcontainers (`@ServiceConnection`) when queries use vendor features. Flyway runs in the slice, so the migration is tested too.
- A test for each fix: the query count for an N+1, two concurrent updates for a lock, the rejected duplicate for a unique constraint.
- When you cannot run the tests, write them, give the command (`./mvnw -B test -Dtest=<Class>` or `./gradlew test --tests <Class>`), and mark it not run.

## Panache and MongoDB

- **Panache:** the same rules apply. Active record (`PanacheEntity`) or repository (`PanacheRepository`), as the project does; `find("status = ?1", status)` with parameters; `@Version` works the same; writes inside `@Transactional`.
- **MongoDB (Spring Data):** no joins, so model aggregates as documents and reference other aggregates by ID; avoid N+1 by loading referenced documents in one `findAllById`; `@Version` gives optimistic locking; indexes with `@Indexed` or migrations (Mongock); no query text built from input.

## Return

```markdown
Problem: CancelOverdueOrdersJob loads every open order, then one customer per order (N+1): 1 + N queries, N = open orders (OrderJob.java:31-38).
Change:
- OrderRepository: findOverdue(cutoff) with `join fetch o.customer` (one query).
- OrderJob.java:31: uses it; no repository call inside the loop.
- V14__orders_due_on_index.sql: index on orders(due_on) where status = 'OPEN'.
Test: OrderRepositoryTest.findsOverdueWithCustomersInOneQuery (Testcontainers PostgreSQL, counts statements).
Run: ./mvnw -B test -Dtest=OrderRepositoryTest — not run: this agent cannot run Maven here.
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "jpa-patterns", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"jpa-patterns"'
```

## Before you finish

- [ ] Mappings match the migrations, and enums are stored as strings.
- [ ] No query runs inside a loop over results; collections that grow are paged or streamed.
- [ ] Every write runs in a transaction; contended rows have a lock, an atomic update or a constraint.
- [ ] No applied migration was edited; the new one is the next version and is backwards compatible.
- [ ] Each change has a test, and the answer gives the command (run, or marked not run).
