# Insecure code patterns

Search the changed files first, then the rest of `src/main` (or the Python package). The search terms are starting points for a text search; read every hit in context, follow the value back to its source, and report it only when untrusted input (a request, a message, a file, a header) or a real secret reaches it. Test code is reported only when it ships or leaks a real secret.

## Java and Kotlin

| Pattern | Search for | CWE | OWASP Top 10:2025 | Usual severity |
|---|---|---|---|---|
| SQL or JPQL built from input | `createQuery(` or `createNativeQuery(` with `+`; `jdbcTemplate.query("...` + `; `Statement.execute` | CWE-89 | A05:2025 Injection | Critical |
| OS command from input | `Runtime.getRuntime().exec(`, `new ProcessBuilder(` with `sh -c` or concatenated strings | CWE-78 | A05:2025 Injection | Critical |
| Expression or template injection | `SpelExpressionParser().parseExpression(` on input; `StringSubstitutor.createInterpolator()` on input; template engines rendering user templates | CWE-917, CWE-94 | A05:2025 Injection | Critical |
| Unsafe deserialization | `new ObjectInputStream(`, `.readObject()`, `XMLDecoder`, `enableDefaultTyping`, `activateDefaultTyping`, `@JsonTypeInfo(use = Id.CLASS)`, `new Yaml().load(` | CWE-502 | A08:2025 Software or Data Integrity Failures | Critical with request data |
| XML external entities | `DocumentBuilderFactory.newInstance()`, `SAXParserFactory.newInstance()`, `XMLInputFactory.newInstance()`, `TransformerFactory.newInstance()` without disabling DTDs and external entities | CWE-611 | A02:2025 Security Misconfiguration | High |
| SSRF | `new URL(` or `URI.create(` on input then `openStream`/`openConnection`; `restTemplate.getForObject(` or `webClient.get().uri(` with a URL from the request | CWE-918 | A01:2025 Broken Access Control | High |
| Path traversal | `new File(` / `Paths.get(` / `Path.of(` with input, without `normalize()` and a base-directory check | CWE-22 | A01:2025 Broken Access Control | High |
| Weak hashing or ciphers | `MessageDigest.getInstance("MD5")` or `"SHA-1"` for passwords or signatures; `Cipher.getInstance("DES"`, `"AES/ECB`, `"RC4"` | CWE-327, CWE-916 | A04:2025 Cryptographic Failures | High |
| Predictable randomness for secrets | `new Random()` or `Math.random()` for tokens, codes or IDs that must not be guessed | CWE-330 | A04:2025 Cryptographic Failures | High |
| TLS validation off | `TrustManager` that accepts all, `HostnameVerifier` returning `true`, `setHostnameVerifier(NoopHostnameVerifier` | CWE-295 | A04:2025 Cryptographic Failures | High |
| Hard-coded credentials | `password =`, `secret =`, `apiKey =` with a literal; credentials in `application*.yml` or `.properties` instead of `${ENV}` | CWE-798 | A07:2025 Authentication Failures | Critical |
| Permissive security configuration | `permitAll()` on `/**`; `csrf().disable()` or `csrf(AbstractHttpConfigurer::disable)` with cookie sessions; `allowedOrigins("*")` with `allowCredentials(true)` | CWE-862, CWE-352, CWE-942 | A01:2025 Broken Access Control | High |
| Exposed management endpoints | `management.endpoints.web.exposure.include=*` (or `"*"` in YAML) on a public port; `env`, `heapdump`, `configprops` exposed | CWE-215 | A02:2025 Security Misconfiguration | High |
| Errors that leak internals | `server.error.include-stacktrace=always`, `include-message=always`; exception messages returned to clients | CWE-209 | A10:2025 Mishandling of Exceptional Conditions | Medium |
| Failing open | `catch (Exception e)` that returns `true`, a default grant or an empty result in an authorization or validation path | CWE-636, CWE-755 | A10:2025 Mishandling of Exceptional Conditions | High |
| Sensitive data in logs | `log.*(` with passwords, tokens, `Authorization` headers, card numbers, emails | CWE-532 | A09:2025 Security Logging and Alerting Failures | High |
| Log injection | logging raw request values that can contain line breaks, without neutralizing them | CWE-117 | A09:2025 Security Logging and Alerting Failures | Low |

## Python

| Pattern | Search for | CWE | OWASP Top 10:2025 | Usual severity |
|---|---|---|---|---|
| SQL built from input | `execute(f"`, `execute("..." %`, `execute("..." + `, `.raw(` or `text(` with f-strings | CWE-89 | A05:2025 Injection | Critical |
| OS command from input | `subprocess.*(..., shell=True)` with input, `os.system(`, `os.popen(` | CWE-78 | A05:2025 Injection | Critical |
| Code evaluation | `eval(`, `exec(` on input | CWE-95 | A05:2025 Injection | Critical |
| Template injection | `render_template_string(` or `Template(...)` with user-controlled templates; Jinja2 with `autoescape=False` for HTML | CWE-1336, CWE-79 | A05:2025 Injection | High |
| Unsafe deserialization | `pickle.loads(`, `pickle.load(`, `yaml.load(` without `SafeLoader`, `yaml.unsafe_load(`, `jsonpickle.decode(`, `marshal.loads(` | CWE-502 | A08:2025 Software or Data Integrity Failures | Critical with request data |
| XML external entities | `xml.etree`, `xml.dom.minidom` or `lxml.etree` parsing untrusted XML (prefer `defusedxml`); `resolve_entities=True` | CWE-611 | A02:2025 Security Misconfiguration | High |
| SSRF | `requests.get(`, `httpx.get(`, `urllib.request.urlopen(` on a URL from the request | CWE-918 | A01:2025 Broken Access Control | High |
| Path traversal | `open(` / `os.path.join(` / `send_file(` with input, without a base-directory check | CWE-22 | A01:2025 Broken Access Control | High |
| Weak hashing or randomness | `hashlib.md5(` or `sha1(` for passwords; `random.random()`, `random.choice(` for tokens (use `secrets`) | CWE-327, CWE-330 | A04:2025 Cryptographic Failures | High |
| TLS validation off | `verify=False` in `requests` or `httpx`; `ssl._create_unverified_context` | CWE-295 | A04:2025 Cryptographic Failures | High |
| Debug in production | `DEBUG = True` in Django settings that ship; `app.run(debug=True)`; FastAPI or Flask debug toolbars enabled | CWE-489 | A02:2025 Security Misconfiguration | High |
| Hard-coded credentials | `SECRET_KEY = "`, `password = "`, tokens in settings modules | CWE-798 | A07:2025 Authentication Failures | Critical |
| Bare or broad except that fails open | `except:` or `except Exception:` followed by `pass`, `return True` or a default in a security path | CWE-636, CWE-755 | A10:2025 Mishandling of Exceptional Conditions | High |
| Assert used for security checks | `assert user.is_admin` (removed with `-O`) | CWE-617 | A10:2025 Mishandling of Exceptional Conditions | Medium |

## Reporting a pattern

- `path:line` of the sink, and the source of the input when it is elsewhere (`from the X-Depot header, line 24`).
- The fix as text: the safe API (bind parameters, an argument list without a shell, `SafeConstructor`, `defusedxml`, `secrets.token_urlsafe`), never an exploit or attack payload.
- When the sink is a vulnerable library's API (Text4Shell, Log4Shell, unsafe YAML), report it next to the dependency finding as reachable.
