# Schema migrations

## Rules

1. **Use the project's tool** (Flyway or Liquibase) and its folder. Never rely on `ddl-auto=update` or `create` outside a throwaway local database.
2. **Never edit an applied migration.** Once a script may have run on any shared database (merged to the main branch, deployed, or pulled by teammates), it is history. Flyway stores a checksum per version and fails `validate` when a script changes; Liquibase does the same per changeset. Fix mistakes with the next migration.
3. **Next version, descriptive name:** Flyway `V<next>__<what_it_does>.sql` (two underscores; `V3__add_product_version.sql`). Check the highest existing version first, including other branches you know about; two branches with the same version collide.
4. **Entity and migration in the same change.** The mapping (`nullable`, `length`, types) matches the DDL; tests with `ddl-auto=validate` catch drift.
5. **Backwards compatible with the running version.** During a rolling deploy the old code runs against the new schema. Expand first, contract later:
   - add a column as nullable or with a default; backfill; add `NOT NULL` or the constraint in a later migration;
   - rename by adding the new column, writing both, migrating reads, and dropping the old one in a later release;
   - drop a column only after no deployed code reads it.
6. **Indexes for every new predicate,** foreign key and unique rule. On large PostgreSQL tables use `CREATE INDEX CONCURRENTLY`, which cannot run inside a transaction: Flyway needs the script-level setting that disables the transaction for that script (a `.conf` file next to it or the `executeInTransaction` option, depending on the version); Liquibase uses `runInTransaction="false"` on the changeset.
7. **Data migrations** are idempotent where possible, run in bounded batches on large tables, and never contain personal data or secrets.
8. **Repeatable migrations** (`R__<name>.sql`) only for objects that are recreated as a whole (views, functions).

## Examples (Flyway, PostgreSQL)

Optimistic locking for an existing table:

```sql
-- V3__add_product_version.sql
ALTER TABLE products ADD COLUMN version BIGINT NOT NULL DEFAULT 0;
```

```java
@Version
private long version;
```

A new nullable column, backfilled, then constrained in the next release:

```sql
-- V4__add_order_channel.sql
ALTER TABLE orders ADD COLUMN channel VARCHAR(20);
UPDATE orders SET channel = 'WEB' WHERE channel IS NULL;
```

```sql
-- V5__order_channel_not_null.sql (a later release)
ALTER TABLE orders ALTER COLUMN channel SET NOT NULL;
```

One active reservation per customer and product:

```sql
-- V6__reservations.sql
CREATE TABLE reservations (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT      NOT NULL REFERENCES products (id),
    customer_id BIGINT      NOT NULL REFERENCES customers (id),
    status      VARCHAR(10) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX reservations_one_active
    ON reservations (product_id, customer_id) WHERE status = 'ACTIVE';
CREATE INDEX reservations_product_created ON reservations (product_id, created_at);
```

## Liquibase equivalent

```yaml
databaseChangeLog:
  - changeSet:
      id: 3-add-product-version
      author: <author>
      changes:
        - addColumn:
            tableName: products
            columns:
              - column:
                  name: version
                  type: BIGINT
                  defaultValueNumeric: 0
                  constraints:
                    nullable: false
```

## Checking a migration without running it

When you cannot run the build or a database:

- the version is the next free one and the name follows the convention;
- the SQL is valid for the project's database (types, syntax of partial indexes and constraints);
- the entity mapping matches each new column;
- no existing migration file changed (`git diff --name-only <base> -- <migrations folder>` lists only new files);
- give the command that applies it in tests (`./mvnw -B test -Dtest=<RepositoryTest>`, or the project's Flyway task) and mark it not run.
