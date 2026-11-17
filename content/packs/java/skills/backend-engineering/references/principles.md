# Backend principles: detail and examples

The router (`SKILL.md`) gives the rules; this file shows what they look like in a Java service. Always follow the project's existing structure first.

## Layered or hexagonal

| | Layered | Hexagonal (ports and adapters) |
|---|---|---|
| Shape | controller → service → repository | adapters → ports → use cases → domain |
| Fits | CRUD-heavy services, small teams, one database | rich domain rules, several integrations, long life |
| Framework in the core | allowed (annotations on services and entities) | not in `domain`; tolerated in `application` if the project accepts it |
| Test focus | services with mocked repositories, slices for web and data | domain and use cases without Spring; adapters with slices |

Layered, packaged by feature:

```text
com.example.shop.orders/
  OrderController.java      HTTP, @Valid, DTO mapping
  OrderService.java         use cases, @Transactional
  OrderRepository.java      Spring Data
  Order.java                entity with its invariants
  OrderRequest.java, OrderResponse.java   records
```

Hexagonal:

```text
com.example.shop.orders/
  domain/        Order, OrderLine, Money, OrderCancelled (event), no framework imports
  application/   CancelOrder (use case), ports: OrderStore, PaymentGateway
  adapter/in/web/        OrderController -> CancelOrder
  adapter/out/persistence/ JpaOrderStore implements OrderStore
  adapter/out/payments/    HttpPaymentGateway implements PaymentGateway
```

Rules that hold in both: dependencies point toward the domain; the API speaks DTOs, never entities; one feature does not reach into another feature's repository, it calls that feature's service or port.

## DDD building blocks

| Block | Use it for | Example |
|---|---|---|
| Entity | identity and a lifecycle; methods that keep its invariants | `Order.cancel()` throws when the order already shipped |
| Value object | a concept with rules and no identity; immutable | `Money(amountCents, currency)`, `Isbn.parse(text)` |
| Aggregate | the consistency boundary: one transaction changes one aggregate | `Order` with its `OrderLine`s; other aggregates by ID (`customerId`) |
| Domain service | a rule that spans aggregates and belongs to none | `PricingPolicy.priceFor(order, customer)` |
| Domain event | something that happened, for other parts to react to | `OrderCancelled(orderId, at)` |
| Repository | loads and saves whole aggregates | `OrderRepository.findById` |

Signs you do not need DDD here: the feature is a form over a table, there are no rules beyond validation, and no other part reacts to its changes.

## SOLID, briefly

- **Single responsibility:** `InvoiceService` computes and stores invoices; rendering a PDF is `InvoiceRenderer`.
- **Open/closed:** a new shipping method is a new `ShippingRate` implementation picked by a map of strategies, not a new `if (type == ...)` branch in every method.
- **Liskov:** an implementation of a port honors its contract: a `PaymentGateway` that cannot refund throws the declared exception, it does not return a fake success.
- **Interface segregation:** a `Notifier` with `send(to, subject, body)` rather than a `CommunicationsService` with twenty methods.
- **Dependency inversion:** the use case depends on `PaymentGateway`; the HTTP client lives in the adapter.

## Transactions and side effects

- Put `@Transactional` on the public service method that runs the use case; `readOnly = true` on queries.
- A side effect that must not happen if the transaction rolls back (an email, a message, a call to another service) runs after commit:

```java
@Transactional
public Order cancel(long id) {
    Order order = orders.findById(id).orElseThrow(() -> new NotFoundException("Order", id));
    order.cancel(clock.instant());
    events.publishEvent(new OrderCancelled(order.getId()));
    return order;
}

@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
void refund(OrderCancelled event) {
    payments.refund(event.orderId());
}
```

- When the side effect must not be lost either, use an **outbox**: write the event to an `outbox` table in the same transaction, and a separate job publishes and marks it sent. Consumers deduplicate by event ID.

## Idempotency key

For a POST with side effects (a payment, a booking):

1. The client sends `Idempotency-Key: <uuid>`.
2. The server stores the key, a hash of the request and the response, with a unique constraint on the key and a time to live.
3. The same key with the same request returns the stored response; with a different request, 422 (or the project's choice); while the first request is still running, 409.

A natural key with a unique constraint (one reservation per member and title) gives the same protection for simpler cases.

## Errors

| Situation | Exception (example) | HTTP |
|---|---|---|
| Malformed or invalid input | `MethodArgumentNotValidException`, `IllegalArgumentException` | 400 |
| Not authenticated / not allowed | handled by the security layer | 401 / 403 |
| Unknown resource, or one the caller may not see | `NotFoundException` | 404 |
| Conflict with the current state, duplicate, lost race | `ConflictException`, optimistic lock failure | 409 |
| Well-formed request that breaks a business rule | `BusinessRuleException(code, message)` | 422, or 409 if that is the project's convention |
| Anything else | unexpected exception, logged once with its stack trace | 500, generic body |

Keep the code stable (`order_not_cancellable`): clients branch on it. The body format is the project's (RFC 9457 problem details by default, see skill:backend-and-api).

## Quarkus equivalences

The skills of this pack are written for Spring Boot. In a Quarkus service, apply them with these equivalences:

| Spring Boot | Quarkus |
|---|---|
| `@Service`, `@Component` (singleton) | `@ApplicationScoped` (CDI) |
| constructor injection | constructor injection, or package-private `@Inject` fields as Quarkus recommends |
| `@ConfigurationProperties` record | `@ConfigMapping` interface; `@ConfigProperty` for a single value |
| profiles `application-<profile>.yml` | `%dev.`, `%test.`, `%prod.` prefixes in `application.properties` |
| Spring MVC `@RestController` | Quarkus REST (`@Path`, `@GET`), `ExceptionMapper` or `@ServerExceptionMapper` for errors |
| Spring Data JPA | Hibernate ORM with Panache (`PanacheEntity`, `PanacheRepository`) |
| `org.springframework.transaction.annotation.Transactional` | `jakarta.transaction.Transactional` |
| Actuator health and metrics | SmallRye Health (`/q/health`), Micrometer extension |
| Spring Security | `quarkus-oidc`, `@RolesAllowed`, `quarkus.http.auth.permission.*` |
| `@WebMvcTest`, `@DataJpaTest` | `@QuarkusTest`, `@QuarkusComponentTest`, Dev Services for the database |
