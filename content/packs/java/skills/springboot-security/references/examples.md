# Spring Security examples

Spring Boot 3 with Spring Security 6, and Spring Boot 4 with Spring Security 7; where they differ, the text says so. The domain is a fictional shop; adapt paths, roles and claims to the project.

## Stateless API with a JWT resource server

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-oauth2-resource-server</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.security</groupId>
    <artifactId>spring-security-test</artifactId>
    <scope>test</scope>
</dependency>
```

On Boot 4 the starter is `spring-boot-starter-security-oauth2-resource-server`, and the test dependency is `spring-boot-starter-security-test`; both without a version, from the Boot BOM.

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: ${JWT_ISSUER_URI}
          audiences: shop-api
```

```java
@Configuration
@EnableMethodSecurity
class SecurityConfig {

    @Bean
    SecurityFilterChain api(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/api/**")
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(HttpMethod.GET, "/api/products", "/api/products/*").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/products", "/api/products/*/stock").hasRole("MANAGER")
                .requestMatchers(HttpMethod.DELETE, "/api/products/*").hasRole("MANAGER")
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.jwtAuthenticationConverter(rolesFromClaim())))
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // No cookie authenticates a request: every call carries a bearer token, so CSRF does not apply.
            .csrf(csrf -> csrf.disable())
            .cors(Customizer.withDefaults());
        return http.build();
    }

    private static JwtAuthenticationConverter rolesFromClaim() {
        JwtGrantedAuthoritiesConverter roles = new JwtGrantedAuthoritiesConverter();
        roles.setAuthoritiesClaimName("roles");
        roles.setAuthorityPrefix("ROLE_");
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(roles);
        return converter;
    }
}
```

- The claim that carries roles depends on the identity provider (`roles`, `groups`, `realm_access.roles`, `scp`): ask, or read it from `.exo/context.md`. A nested claim needs a custom converter.
- `audiences` rejects tokens issued for another API; on Boot versions without the property, add a `JwtClaimValidator` for `aud` to a custom `JwtDecoder`.

## Object-level authorization

```java
@Transactional(readOnly = true)
public Order getForCaller(long orderId, Jwt caller) {
    long customerId = Long.parseLong(caller.getSubject());
    return orders.findByIdAndCustomerId(orderId, customerId)
            .orElseThrow(() -> new NotFoundException("Order", orderId));
}
```

Or with a bean in a method security expression:

```java
@PreAuthorize("hasRole('MANAGER') or @orderAccess.isOwner(#orderId, authentication)")
public Order get(long orderId) { ... }

@Component("orderAccess")
@RequiredArgsConstructor
class OrderAccess {
    private final OrderRepository orders;

    boolean isOwner(long orderId, Authentication authentication) {
        return orders.existsByIdAndCustomerId(orderId, Long.parseLong(authentication.getName()));
    }
}
```

## Browser app with sessions and a single-page front end

Spring Security 7 (Boot 4):

```java
@Bean
SecurityFilterChain web(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/", "/assets/**", "/login/**").permitAll()
            .anyRequest().authenticated())
        .oauth2Login(Customizer.withDefaults())
        .csrf(csrf -> csrf.spa())
        .logout(logout -> logout.logoutSuccessUrl("/"));
    return http.build();
}
```

Spring Security 6 (Boot 3) has no `spa()`: the same chain with a cookie repository and a request handler that renders the deferred token on every request (so the cookie is written) and accepts the raw token the front end sends in the header:

```java
        .csrf(csrf -> csrf
            .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
            .csrfTokenRequestHandler(new SpaCsrfTokenRequestHandler()))
```

```java
final class SpaCsrfTokenRequestHandler implements CsrfTokenRequestHandler {

    private final CsrfTokenRequestHandler plain = new CsrfTokenRequestAttributeHandler();
    private final CsrfTokenRequestHandler xor = new XorCsrfTokenRequestAttributeHandler();

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response, Supplier<CsrfToken> csrfToken) {
        xor.handle(request, response, csrfToken);   // BREACH protection when the token is rendered in a page
        csrfToken.get();                            // load the deferred token, so the cookie is written
    }

    @Override
    public String resolveCsrfTokenValue(HttpServletRequest request, CsrfToken csrfToken) {
        String header = request.getHeader(csrfToken.getHeaderName());
        return (StringUtils.hasText(header) ? plain : xor).resolveCsrfTokenValue(request, csrfToken);
    }
}
```

This is the handler of the Spring Security 6.5 reference. Older guides for Spring Security 6 add a `CsrfCookieFilter` that calls `getToken()` on every request instead, with the plain attribute handler: it does the same loading. The front end reads the `XSRF-TOKEN` cookie and sends it back in the `X-XSRF-TOKEN` header on state-changing requests; the cookie is cleared at sign-in and sign-out, so it reads it again after them. The OAuth2 client secret comes from `${OAUTH_CLIENT_SECRET}`.

## CORS from configuration

```java
@Bean
CorsConfigurationSource corsConfigurationSource(@Value("${shop.cors.allowed-origins}") List<String> origins) {
    CorsConfiguration config = new CorsConfiguration();
    config.setAllowedOrigins(origins);
    config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
    config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/api/**", config);
    return source;
}
```

## Actuator on its own chain

```java
@Bean
@Order(1)
SecurityFilterChain actuator(HttpSecurity http) throws Exception {
    http
        .securityMatcher(EndpointRequest.toAnyEndpoint())
        .authorizeHttpRequests(auth -> auth
            .requestMatchers(EndpointRequest.to(HealthEndpoint.class)).permitAll()
            .anyRequest().hasRole("OPS"))
        // A role rule needs a way to sign in on this chain too: here the same bearer tokens as the API.
        .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.jwtAuthenticationConverter(rolesFromClaim())))
        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        // No cookie authenticates a request on this chain, so CSRF does not apply.
        .csrf(csrf -> csrf.disable());
    return http.build();
}
```

It lives in the same `SecurityConfig` as the API chain, so it reuses `rolesFromClaim()`. Without an identity provider, HTTP Basic for an operations account (`.httpBasic(Customizer.withDefaults())` with its password hashed, from the secret store) is the alternative.

## Passwords

```java
@Bean
PasswordEncoder passwordEncoder() {
    return PasswordEncoderFactories.createDelegatingPasswordEncoder();  // bcrypt by default
}
```

## Tests

```java
@WebMvcTest(ProductController.class)
@Import(SecurityConfig.class)
class ProductSecurityTest {

    @Autowired MockMvc mvc;
    @MockitoBean ProductService products;
    @MockitoBean JwtDecoder jwtDecoder;  // no call to the real issuer in tests

    @Test
    void anyoneCanReadTheCatalog() throws Exception {
        mvc.perform(get("/api/products")).andExpect(status().isOk());
    }

    @Test
    void anonymousCannotCreate() throws Exception {
        mvc.perform(post("/api/products").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void customersCannotCreate() throws Exception {
        mvc.perform(post("/api/products").with(jwt().authorities(new SimpleGrantedAuthority("ROLE_CUSTOMER")))
                        .contentType(MediaType.APPLICATION_JSON).content(validProductJson()))
                .andExpect(status().isForbidden());
    }

    @Test
    void managersCanCreate() throws Exception {
        mvc.perform(post("/api/products").with(jwt().authorities(new SimpleGrantedAuthority("ROLE_MANAGER")))
                        .contentType(MediaType.APPLICATION_JSON).content(validProductJson()))
                .andExpect(status().isCreated());
    }
}
```

`@MockitoBean` is Boot 3.4+ and the only option on Boot 4, where `@MockBean` was removed; use `@MockBean` before 3.4. On Boot 4, `@WebMvcTest` comes from `spring-boot-starter-webmvc-test`.
