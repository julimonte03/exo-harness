---
name: springboot-security
description: >-
  Spring Security 6 for Spring Boot 3 services: the SecurityFilterChain and
  its rules (deny by default), authentication with sessions, JWT resource
  servers or OAuth2/OIDC login, roles and method security with @PreAuthorize,
  object-level authorization, CSRF and when it can be off, CORS, security
  headers, password storage and sign-in limits, Actuator exposure, and
  secrets kept out of code and config, with tests for allowed and denied
  paths. Use it when adding authentication or authorization to a Spring
  service, securing endpoints or roles, configuring JWT or OAuth2, fixing a
  401, 403 or CORS error, or reviewing a security configuration. Triggers:
  "Spring Security", "secure this endpoint", "add authentication", "only
  admins can", "JWT", "OAuth2 login", "@PreAuthorize", "CSRF", "CORS error",
  "SecurityFilterChain", "403 forbidden".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-write
---

# springboot-security

## Result

- A security configuration that denies by default, authenticates with the project's identity provider, and checks authorization on every endpoint and on every object a caller reads or changes.
- Tests that prove both sides: the allowed call works, and the anonymous, wrong-role and other-owner calls fail with the right status.
- Configuration examples are in `references/examples.md`.

## When

- Adding authentication or authorization, securing new endpoints, changing roles, configuring JWT, OAuth2 or sessions, CORS or CSRF problems, or reviewing a security configuration.
- **In SDD:** skill:backend-engineering loads it with skill:secure-coding-baseline (pack `security`) when the change touches authentication, authorization or secrets. In design, skill:threat-modeling names the threats; this skill implements their mitigations. A missing `security` pack skill degrades as `.exo/shared/skill-resolver.md` says.
- **Not for:** a security review of a whole diff (skill:security-code-review), dependency vulnerabilities (skill:security-scan-jkp).

## Read first

1. The build: `spring-boot-starter-security`, `spring-boot-starter-oauth2-resource-server`, `spring-boot-starter-oauth2-client`, `spring-security-test`. Without the security starter, every endpoint is open today: say so.
2. Existing `SecurityFilterChain` beans, method security, custom filters. A class extending `WebSecurityConfigurerAdapter` is Spring Security 5 and must move to a `SecurityFilterChain` bean.
3. **Who calls the service:** a browser with cookies (sessions, CSRF matters), other services or a single-page app with bearer tokens (stateless), or both. `.exo/context.md` names the identity provider when there is one.
4. The roles and ownership rules: the spec, the design, or the person. Never invent who may do what: ask.

## 1. The filter chain

- One `SecurityFilterChain` bean per kind of client (API, Actuator, browser), each with a `securityMatcher` and an `@Order`.
- `authorizeHttpRequests` lists the public endpoints explicitly, then the role rules, and ends with `anyRequest().authenticated()` (or `denyAll()`). Never `permitAll()` on `/**`.
- Match exact paths and methods (`requestMatchers(HttpMethod.GET, "/api/products/**")`): a rule on a path without a method also opens the other methods.
- Use the lambda DSL of Spring Security 6; the old `and()` chaining and `antMatchers` are gone.

## 2. Authentication

| Clients | Choose | Notes |
|---|---|---|
| Services, mobile apps or a single-page app with tokens from an identity provider | JWT resource server: `oauth2ResourceServer(o -> o.jwt(...))` and `spring.security.oauth2.resourceserver.jwt.issuer-uri` | the issuer from an environment variable; validate issuer, audience and expiry; map scopes or roles with a `JwtAuthenticationConverter`; never parse JWTs by hand or accept unsigned ones |
| A server-rendered web app with a corporate or social login | OAuth2/OIDC login: `oauth2Login()` with a registered client | the client secret from the environment; sessions and CSRF stay on |
| A server-rendered app with its own users | form login with sessions | passwords with a `DelegatingPasswordEncoder` (bcrypt) or Argon2; limit failed attempts |
| Machine-to-machine without an identity provider | API keys in a custom filter, or HTTP Basic over TLS | compare keys in constant time (`MessageDigest.isEqual`), store them hashed, rotate them |

Stateless APIs set `sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))`.

## 3. Authorization

- **Coarse rules in the chain** (`hasRole("ADMIN")` for `/api/admin/**`), **fine rules on methods** with `@EnableMethodSecurity` and `@PreAuthorize("hasRole('MANAGER')")` on service or controller methods.
- **Object-level checks** for every read or change of something that belongs to someone: the service loads the object and checks it against the authenticated principal (`order.customerId` equals the caller's ID), or a bean expression does (`@PreAuthorize("@orderAccess.canRead(#id, authentication)")`). This is the most common API hole (`A01:2025 Broken Access Control`, CWE-639).
- Never trust an owner ID, role or tenant sent by the client; take them from the token or the session.
- Answer 404 instead of 403 when telling the caller that the object exists would leak information.
- Roles: `hasRole('X')` expects the authority `ROLE_X`; JWT scopes arrive as `SCOPE_x`. Map them explicitly in the converter so the names match.

## 4. CSRF

- On by default, and it must stay on when browsers authenticate with cookies (sessions, OAuth2 login). For a single-page app on cookies, use a cookie token repository and send the token in a header (see `references/examples.md`).
- Off only for stateless APIs that authenticate with a bearer token and set no auth cookies. Write a comment next to `csrf(c -> c.disable())` that says why.

## 5. CORS

- `cors(Customizer.withDefaults())` with a `CorsConfigurationSource` bean: the exact allowed origins from configuration per profile, the methods and headers needed, `allowCredentials` only when cookies are used.
- Never `*` together with credentials. A CORS error in the browser is fixed in this configuration, not by disabling security.

## 6. Headers and transport

- Keep the defaults (`X-Content-Type-Options`, `X-Frame-Options: DENY`, cache control, HSTS over HTTPS). Add a Content Security Policy when the service renders HTML.
- Behind a proxy, `server.forward-headers-strategy=framework` so redirects and HSTS see HTTPS.

## 7. Secrets

- From the environment or the project's secret store (`${OAUTH_CLIENT_SECRET}`), never in code, `application*.yml`, tests or the repository (`.exo/shared/data-protection.md`). No default value for a secret.
- No `spring.security.user.password` in committed files; the generated development password is for local runs only.
- Never log tokens, `Authorization` headers, passwords or the `Authentication` object.

## 8. Actuator

- Public: `health` (and `info` if it holds nothing sensitive). Everything else behind a role, on its own chain or a management port.
- `management.endpoint.health.show-details=when-authorized`. Never expose `env`, `configprops`, `heapdump`, `threaddump` or `loggers` publicly (`A02:2025 Security Misconfiguration`).

## 9. Errors and events

- An `AuthenticationEntryPoint` for 401 and an `AccessDeniedHandler` for 403 that return the project's error body without details.
- Log security events (failed sign-ins, denied access, role changes) without tokens or personal data (`A09:2025 Security Logging and Alerting Failures`). Limit repeated failed sign-ins (`A07:2025 Authentication Failures`).

## 10. Tests

With `spring-security-test` (scope test):

- `@WebMvcTest` applies the security configuration (import it with `@Import(SecurityConfig.class)` if it is not picked up).
- For each protected endpoint, a test per case: anonymous gets 401, the wrong role gets 403, the right role succeeds, another owner's object gets 404 or 403.
- JWT: `.with(jwt().authorities(new SimpleGrantedAuthority("ROLE_MANAGER")))`; sessions: `@WithMockUser(roles = "MANAGER")`; state-changing requests with sessions add `.with(csrf())`.
- A CORS preflight test (`OPTIONS` with `Origin` and `Access-Control-Request-Method`) when CORS changes.
- Write the tests even when you cannot run them; give the command and mark it not run.

## Reactive and Quarkus

- **WebFlux:** `SecurityWebFilterChain` with `ServerHttpSecurity`, `@EnableReactiveMethodSecurity`; the same rules apply.
- **Quarkus:** `quarkus-oidc` for tokens, `@RolesAllowed` and `@Authenticated`, `quarkus.http.auth.permission.*` for path rules, `quarkus-test-security` with `@TestSecurity` in tests.

## Return

```markdown
Change: the API accepts bearer tokens from the identity provider; catalog reads stay public.
- pom.xml: spring-boot-starter-security, spring-boot-starter-oauth2-resource-server; spring-security-test (test).
- application.yml: spring.security.oauth2.resourceserver.jwt.issuer-uri: ${JWT_ISSUER_URI}.
- SecurityConfig.java (new): stateless chain; GET /api/products/** public; POST, PUT, DELETE on /api/products/** need ROLE_MANAGER; anything else authenticated; CSRF off because no cookie authenticates a request (comment at line 31); roles mapped from the `roles` claim.
- OrderService.java:52: an order is loaded by ID and caller, so customers see only their own (404 otherwise).
Tests: SecurityConfigTest (anonymous 401, customer 403 on POST /api/products, manager 201, public GET 200), OrderServiceTest (other customer's order -> NotFoundException).
Run: ./mvnw -B test -Dtest='SecurityConfigTest,OrderServiceTest' — not run: this agent cannot run Maven here.
Open question: which claim carries the roles in your identity provider? Assumed `roles`.
```

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "springboot-security", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"springboot-security"'
```

## Before you finish

- [ ] The chain denies by default; public endpoints are listed explicitly with their methods.
- [ ] Authentication fits the clients; issuer, client secrets and keys come from the environment.
- [ ] Every endpoint has its role rule, and every owned object an object-level check.
- [ ] CSRF is on for cookie authentication, or off with a comment for stateless tokens; CORS lists exact origins.
- [ ] Actuator exposes only what is safe; no secret or token is logged or committed.
- [ ] Tests cover anonymous, wrong role, right role and other owner, with the command given (run, or marked not run).
