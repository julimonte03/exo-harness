# Spring Boot examples

Spring Boot 3, Java 21. The domain is a fictional shop; adapt names and packages to the project.

## Typed, validated configuration

```java
@Validated
@ConfigurationProperties(prefix = "shop.cancellation")
public record CancellationProperties(
        @Positive int windowHours,
        @NotBlank String supportEmail,
        @NotNull Duration refundTimeout) {
}
```

```java
@SpringBootApplication
@EnableConfigurationProperties(CancellationProperties.class)
public class ShopApplication { ... }
```

```yaml
shop:
  cancellation:
    window-hours: 24
    support-email: support@example.com
    refund-timeout: 5s
```

A missing or invalid value stops the application at start-up with a message that names the property. `@Validated` needs `spring-boot-starter-validation` on the classpath.

## Profiles and secrets

```yaml
# application.yml
spring:
  datasource:
    url: ${DB_URL:jdbc:postgresql://localhost:5432/shop}
    username: ${DB_USER:shop}
    password: ${DB_PASSWORD}
```

```yaml
# application-local.yml (local development only)
logging:
  level:
    org.hibernate.SQL: debug
```

The active profile comes from `SPRING_PROFILES_ACTIVE` in the environment. Secrets have no default, so a missing one fails at start-up instead of running with a wrong value.

## Thin controller with validation

```java
public record PlaceOrderRequest(
        @NotNull Long customerId,
        @NotEmpty List<@Valid LineRequest> lines) {
}

public record LineRequest(@NotNull Long productId, @Positive int quantity) {}

@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
class OrderController {

    private final OrderService orders;

    @PostMapping
    ResponseEntity<OrderResponse> place(@Valid @RequestBody PlaceOrderRequest request) {
        Order order = orders.place(request);
        return ResponseEntity.created(URI.create("/api/orders/" + order.getId()))
                .body(OrderResponse.from(order));
    }
}
```

## One error handler with problem details

```java
@RestControllerAdvice
class ApiErrors {

    private static final Logger log = LoggerFactory.getLogger(ApiErrors.class);

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ProblemDetail invalid(MethodArgumentNotValidException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Invalid request");
        problem.setProperty("code", "invalid_request");
        problem.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
                .map(error -> Map.of("field", error.getField(), "message", error.getDefaultMessage()))
                .toList());
        return problem;
    }

    @ExceptionHandler(NotFoundException.class)
    ProblemDetail notFound(NotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setProperty("code", "not_found");
        return problem;
    }

    @ExceptionHandler(BusinessRuleException.class)
    ProblemDetail rule(BusinessRuleException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        problem.setProperty("code", ex.getCode());
        return problem;
    }

    @ExceptionHandler(Exception.class)
    ProblemDetail unexpected(Exception ex) {
        log.error("Unexpected error", ex);
        return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, "Unexpected error");
    }
}
```

When the project already has its own error record (for example `ApiError(code, message)`), add the validation handler in the same style and add the field list to that record or a sibling, instead of switching formats in one endpoint.

## After-commit side effects

```java
@Transactional
public Order cancel(long id) {
    Order order = get(id);
    order.cancel(clock.instant());
    events.publishEvent(new OrderCancelled(order.getId()));
    return order;
}

@Component
@RequiredArgsConstructor
class RefundOnCancel {

    private final PaymentClient payments;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    void on(OrderCancelled event) {
        payments.refund(event.orderId());
    }
}
```

## HTTP client with timeouts

```java
@Configuration
class PaymentClientConfig {

    @Bean
    RestClient paymentRestClient(RestClient.Builder builder, PaymentProperties properties) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(2));
        factory.setReadTimeout(Duration.ofSeconds(5));
        return builder.baseUrl(properties.baseUrl()).requestFactory(factory).build();
    }
}
```

## Scheduled job

```java
@Scheduled(cron = "${shop.reminders.cron}")
public void sendCartReminders() {
    // idempotent: reminders already sent today are skipped
}
```

## Actuator

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
  endpoint:
    health:
      probes:
        enabled: true
      show-details: when-authorized
```
