# Testing Spring Boot code

Pick the smallest context that proves the behavior. Each step up the table starts more of the application and runs slower.

| Level | Annotation | Starts | Use for |
|---|---|---|---|
| Unit | none (`@ExtendWith(MockitoExtension.class)`) | nothing | domain rules, services with mocked collaborators |
| Web slice | `@WebMvcTest(OrderController.class)` | MVC, Jackson, validation, the advice, filters | mapping, validation, status codes, error bodies, security rules |
| Data slice | `@DataJpaTest` | JPA, repositories, Flyway or Liquibase, a database | queries, mappings, constraints, migrations, locks |
| JSON | `@JsonTest` | Jackson | the serialized shape of DTOs |
| Configuration | `ApplicationContextRunner` | the configuration you give it | property binding and validation, conditional beans |
| Full | `@SpringBootTest` | everything | a few end-to-end checks of the wiring |

## Web slice

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired MockMvc mvc;
    @MockitoBean OrderService orders;   // @MockBean before Boot 3.4

    @Test
    void rejectsAnOrderWithoutLines() throws Exception {
        mvc.perform(post("/api/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"customerId": 7, "lines": []}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors[0].field").value("lines"));
        verifyNoInteractions(orders);
    }
}
```

With Spring Security on the classpath, the web slice applies the security configuration too: add `@WithMockUser` or the `jwt()` post-processor, and `csrf()` for state-changing requests with sessions.

## Data slice with the real database

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class OrderRepositoryTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired OrderRepository orders;

    @Test
    void findsOpenOrdersOldestFirst() { ... }
}
```

- `@ServiceConnection` (Boot 3.1+) wires the datasource to the container; the migrations run on start.
- An embedded database (H2) differs from PostgreSQL in SQL dialect, partial indexes and locking: use it only when the project already does and the query is portable.
- Testcontainers needs Docker. When it is not available, the test cannot run: say so instead of switching the test to H2.

## Configuration binding

```java
class CancellationPropertiesTest {

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withUserConfiguration(Config.class);

    @EnableConfigurationProperties(CancellationProperties.class)
    static class Config {}

    @Test
    void rejectsAZeroWindow() {
        runner.withPropertyValues("shop.cancellation.window-hours=0",
                        "shop.cancellation.support-email=support@example.com",
                        "shop.cancellation.refund-timeout=5s")
                .run(context -> assertThat(context).hasFailed());
    }
}
```

The context fails only when a Bean Validation provider is on the test classpath (`spring-boot-starter-validation`). Add `ValidationAutoConfiguration` to the runner if the property validation does not trigger.

## Time

Inject a `Clock` bean (or use the project's time helper) and pin it in tests: `Clock.fixed(Instant.parse("2025-03-10T08:00:00Z"), ZoneOffset.UTC)`. Never sleep to wait for time to pass.

## Commands

| Build | All tests | One class |
|---|---|---|
| Maven | `./mvnw -B test` (unit) or `./mvnw -B verify` (with integration tests) | `./mvnw -B test -Dtest=OrderControllerTest` |
| Gradle | `./gradlew test` or `./gradlew check` | `./gradlew test --tests 'com.example.shop.orders.OrderControllerTest'` |
