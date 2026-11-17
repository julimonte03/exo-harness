# Examples of the JCS rules

Each pair shows a deviation and the version that follows the rule. The domain is a fictional shop.

## JCS-1 Names

```java
// Deviation
List<Ord> getL(long c) { ... }
boolean flag;

// Follows
List<Order> openOrdersOf(long customerId) { ... }
boolean isPaid;
```

## JCS-3 Immutability and records

```java
// Deviation: a mutable DTO with setters
public class OrderResponse {
    private Long id;
    private String status;
    public void setId(Long id) { this.id = id; }
    public void setStatus(String status) { this.status = status; }
}

// Follows
public record OrderResponse(long id, OrderStatus status, List<LineResponse> lines) {
    public OrderResponse {
        lines = List.copyOf(lines);
    }
}
```

## JCS-4 Optional

```java
// Deviation
public Customer find(Optional<Long> id) {
    return repository.findById(id.get()).get();
}

// Follows
public Customer get(long id) {
    return repository.findById(id).orElseThrow(() -> new NotFoundException("Customer", id));
}
```

## JCS-6 Exceptions

```java
// Deviation: the failure disappears, and so does its cause
try {
    gateway.charge(order);
} catch (Exception e) {
    e.printStackTrace();
}

// Follows: catch what you can handle, keep the cause
try {
    gateway.charge(order);
} catch (PaymentDeclinedException e) {
    throw new BusinessRuleException("payment_declined", "The card was declined", e);
}
```

```java
// Follows: resources always closed
try (InputStream in = Files.newInputStream(path)) {
    return parser.parse(in);
}
```

## JCS-7 Logging

```java
// Deviation
System.out.println("charging " + order.getId() + " for " + customer.getEmail());
log.info("charged order " + order.getId());

// Follows: parameterized, no personal data
log.info("Charging order {}", order.getId());
log.warn("Charge failed for order {}", order.getId(), exception);
```

## JCS-8 Streams

```java
// Deviation: a stream used for side effects on outside state
List<String> names = new ArrayList<>();
orders.stream().forEach(o -> names.add(o.customerName()));

// Follows
List<String> names = orders.stream().map(Order::customerName).toList();
```

## JCS-9 Modern Java

```java
// Follows: switch expression and pattern matching
String label = switch (status) {
    case PAID -> "Paid";
    case SHIPPED -> "On its way";
    case CANCELLED -> "Cancelled";
};

if (event instanceof OrderCancelled cancelled) {
    refunds.start(cancelled.orderId());
}

String query = """
        select o from Order o
        where o.status = :status
        order by o.createdAt desc, o.id
        """;
```

## JCS-11 Injection

```java
// Deviation
@Service
public class OrderService {
    @Autowired
    private OrderRepository orders;
}

// Follows
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orders;
    private final Clock clock;
}
```

## JCS-12 Time and money

```java
// Deviation
double total = 0;
for (Line line : lines) {
    total += line.price() * line.quantity();
}
Date now = new Date();

// Follows
long totalCents = lines.stream().mapToLong(line -> line.priceCents() * line.quantity()).sum();
Instant now = clock.instant();

// Or with BigDecimal
BigDecimal total = lines.stream()
        .map(line -> line.price().multiply(BigDecimal.valueOf(line.quantity())))
        .reduce(BigDecimal.ZERO, BigDecimal::add)
        .setScale(2, RoundingMode.HALF_EVEN);
```

## JCS-13 Entities and Lombok

```java
// Deviation: @Data generates equals, hashCode and toString over lazy relations
@Data
@Entity
public class Order {
    @OneToMany(mappedBy = "order")
    private List<OrderLine> lines;
}

// Follows
@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Order {
    @Id @GeneratedValue
    private Long id;

    @Override
    public boolean equals(Object other) {
        return other instanceof Order that && id != null && id.equals(that.id);
    }

    @Override
    public int hashCode() {
        return getClass().hashCode();
    }
}
```

## JCS-15 Tests

```java
// Deviation: several behaviors, a vague name, a real clock and a sleep
@Test
void test1() throws Exception {
    Order order = service.place(cart);
    Thread.sleep(1000);
    assertTrue(order.getStatus().equals("PLACED"));
    assertNotNull(service.cancel(order.getId()));
}

// Follows
@Test
void cancelsAPlacedOrder() {
    Order order = aPlacedOrder();
    when(orders.findById(order.getId())).thenReturn(Optional.of(order));

    Order cancelled = service.cancel(order.getId());

    assertThat(cancelled.getStatus()).isEqualTo(OrderStatus.CANCELLED);
}

@ParameterizedTest(name = "{0} items -> {1} cents shipping")
@CsvSource({"1, 500", "3, 500", "4, 0"})
void chargesShippingBelowFourItems(int items, long cents) {
    assertThat(shipping.costFor(items)).isEqualTo(cents);
}
```
