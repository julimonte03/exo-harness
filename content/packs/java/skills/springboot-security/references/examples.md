# Spring Security examples

Spring Boot 3 with Spring Security 6. The domain is a fictional shop; adapt paths, roles and claims to the project.

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

```java
@Bean
SecurityFilterChain web(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/", "/assets/**", "/login/**").permitAll()
            .anyRequest().authenticated())
        .oauth2Login(Customizer.withDefaults())
        .csrf(csrf -> csrf
            .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
            .csrfTokenRequestHandler(new CsrfTokenRequestAttributeHandler()))
        .logout(logout -> logout.logoutSuccessUrl("/"));
    return http.build();
}
```

The front end reads the `XSRF-TOKEN` cookie and sends it back in the `X-XSRF-TOKEN` header on state-changing requests. The OAuth2 client secret comes from `${OAUTH_CLIENT_SECRET}`.

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
            .anyRequest().hasRole("OPS"));
    return http.build();
}
```

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

`@MockitoBean` is Boot 3.4+; use `@MockBean` on earlier versions.
