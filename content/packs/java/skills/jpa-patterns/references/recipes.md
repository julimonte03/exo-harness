# JPA recipes

Spring Data JPA with Hibernate 6 and Jakarta Persistence. The domain is a fictional shop; adapt the names to the project.

## Entity with invariants

```java
@Entity
@Table(name = "products")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "products_seq")
    @SequenceGenerator(name = "products_seq", sequenceName = "products_seq", allocationSize = 50)
    private Long id;

    @Column(nullable = false, length = 120)
    private String name;

    @Column(name = "stock", nullable = false)
    private int stock;

    @Version
    private long version;

    public Product(String name, int stock) {
        if (stock < 0) {
            throw new IllegalArgumentException("Stock cannot be negative");
        }
        this.name = name;
        this.stock = stock;
    }

    public void take(int quantity) {
        if (quantity > stock) {
            throw new BusinessRuleException("out_of_stock", "Only " + stock + " left");
        }
        stock -= quantity;
    }
}
```

## N+1: entities referenced by ID

Before: one query for the orders, then one per order.

```java
for (Order order : orders.findOpen()) {
    Customer customer = customers.findById(order.getCustomerId()).orElseThrow();
    mailer.remind(customer, order);
}
```

After: two queries in total.

```java
List<Order> open = orders.findOpen();
Map<Long, Customer> byId = customers.findAllById(
                open.stream().map(Order::getCustomerId).collect(Collectors.toSet()))
        .stream()
        .collect(Collectors.toMap(Customer::getId, Function.identity()));
for (Order order : open) {
    mailer.remind(byId.get(order.getCustomerId()), order);
}
```

## N+1: lazy relation

```java
public interface OrderRepository extends JpaRepository<Order, Long> {

    @Query("select o from Order o join fetch o.customer where o.status = :status")
    List<Order> findWithCustomer(@Param("status") OrderStatus status);

    @EntityGraph(attributePaths = {"lines", "lines.product"})
    Optional<Order> findWithLinesById(Long id);
}
```

## Projection for a read model

```java
public record OrderSummary(long id, String customerName, long totalCents) {}

@Query("""
        select new com.example.shop.orders.OrderSummary(o.id, c.name, o.totalCents)
        from Order o join o.customer c
        where o.status = :status
        order by o.createdAt desc, o.id desc
        """)
Page<OrderSummary> summaries(@Param("status") OrderStatus status, Pageable pageable);
```

## Optimistic lock and the 409

```java
@Transactional
public Product take(long productId, int quantity) {
    Product product = products.findById(productId)
            .orElseThrow(() -> new NotFoundException("Product", productId));
    product.take(quantity);
    return product;  // the version check runs at flush, on commit
}
```

```java
@ExceptionHandler(ObjectOptimisticLockingFailureException.class)
@ResponseStatus(HttpStatus.CONFLICT)
public ApiError lostRace(ObjectOptimisticLockingFailureException ex) {
    return new ApiError("concurrent_update", "Someone else changed this item; reload and try again");
}
```

The version check happens when Hibernate flushes, usually at commit, after the service method returns: the exception surfaces from the transactional proxy. Map it in the error handler, or retry the whole use case a bounded number of times.

## Atomic conditional update

```java
@Modifying(clearAutomatically = true)
@Query("update Product p set p.stock = p.stock - :quantity where p.id = :id and p.stock >= :quantity")
int takeIfAvailable(@Param("id") long id, @Param("quantity") int quantity);
```

```java
@Transactional
public void take(long id, int quantity) {
    if (products.takeIfAvailable(id, quantity) == 0) {
        throw new BusinessRuleException("out_of_stock", "Not enough stock");
    }
}
```

## Pessimistic lock

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@QueryHints(@QueryHint(name = "jakarta.persistence.lock.timeout", value = "3000"))
@Query("select p from Product p where p.id = :id")
Optional<Product> findForUpdate(@Param("id") long id);
```

Keep the transaction short, and always lock rows in the same order to avoid deadlocks.

## Testing a race

```java
@Test
void secondConcurrentTakeOfTheLastItemFails() {
    long id = tx.execute(s -> products.save(new Product("Mug", 1)).getId());

    Product first = tx.execute(s -> products.findById(id).orElseThrow());
    Product second = tx.execute(s -> products.findById(id).orElseThrow());

    tx.executeWithoutResult(s -> { first.take(1); products.save(first); });

    assertThatThrownBy(() -> tx.executeWithoutResult(s -> { second.take(1); products.save(second); }))
            .isInstanceOf(ObjectOptimisticLockingFailureException.class);
}
```

`tx` is a `TransactionTemplate`; the two loads read the same version, and the second save fails. Run it with `@DataJpaTest` plus `@Transactional(propagation = Propagation.NOT_SUPPORTED)` on the class, so each `execute` commits for real.

## Counting queries in a test

With Hibernate statistics enabled for the test (`spring.jpa.properties.hibernate.generate_statistics=true`):

```java
Statistics stats = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
stats.clear();
job.run();
assertThat(stats.getPrepareStatementCount()).isLessThanOrEqualTo(2);
```

## Batch inserts

```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc.batch_size: 50
        order_inserts: true
        order_updates: true
```

```java
for (int i = 0; i < rows.size(); i++) {
    entityManager.persist(rows.get(i));
    if (i % 50 == 49) {
        entityManager.flush();
        entityManager.clear();
    }
}
```
