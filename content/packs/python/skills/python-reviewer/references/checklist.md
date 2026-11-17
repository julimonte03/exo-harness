# Python review checklist

The rule IDs that `python-reviewer` cites. Each item says what to look for, the usual signal in a diff, and what is not a finding. Security items carry their CWE; cite it next to the ID.

## PY-COR Correctness

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-COR-1 | Mutable default argument shared between calls | `def f(x=[])`, `def f(x={})`, `def f(x=set())` | A default that is never mutated and is documented as such (still Low) |
| PY-COR-2 | Late-binding closure captures the last loop value | `lambda` or nested function defined in a loop that uses the loop variable | The loop variable bound as a default argument or with `functools.partial` |
| PY-COR-3 | Floating point for money or exact quantities | `float(...)` or float literals in prices, totals, tax | `Decimal` built from strings, or integer cents |
| PY-COR-4 | Naive datetimes compared with aware ones, or local time stored | `datetime.now()` or `datetime.utcnow()` stored or compared; mixing `date` and `datetime` | Aware datetimes (`datetime.now(timezone.utc)`), or a project that is local-time only by design |
| PY-COR-5 | Iterator or generator consumed twice | A generator passed to two loops, `len()` on a generator, `map` result reused | A `list` built once on purpose |
| PY-COR-6 | Identity instead of equality, or the reverse | `is` with strings or numbers; `== None` | `is None`, `is True` on singletons |
| PY-COR-7 | Off-by-one and boundary errors | `range(len(x) - 1)`, `<` vs `<=` at a limit the spec states, slicing that drops the last item | Boundaries the tests prove |
| PY-COR-8 | Feature or library above the project's floor | `match`, `except*`, `Self`, `tomllib`, `StrEnum` with `requires-python` below their version; imports of packages not in the dependencies | Guarded imports with a fallback |
| PY-COR-9 | Shadowed builtins or names that change meaning | A variable called `list`, `id`, `type`, `input` used later as the builtin | A method named `list` on a class (it does not shadow the builtin in callers) |
| PY-COR-10 | Equality and hashing out of sync | `__eq__` defined without `__hash__` on objects used in sets or as dict keys; mutable dataclass used as a key | `frozen=True` dataclasses |
| PY-COR-11 | Shared mutable state across requests or threads | Module-level lists or dicts modified per request; class attributes used as per-instance state | Read-only module constants |

## PY-TYPE Types

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-TYPE-1 | Public function without hints | `def` at module level or public method with unannotated parameters or return | Tests and private helpers in a project that does not type them |
| PY-TYPE-2 | `Any` where the shape is known | `-> Any`, `dict[str, Any]` passed between modules for a known record | Truly arbitrary data (a JSON blob forwarded as is) |
| PY-TYPE-3 | `cast` or `# type: ignore` without a reason | Bare `# type: ignore`, `cast()` with no comment | `# type: ignore[code]  # reason` |
| PY-TYPE-4 | `None` not handled | Optional return used without a check; attribute access on a value typed `X \| None` | A preceding `if x is None: raise` |
| PY-TYPE-5 | Hints that lie | A function annotated `-> str` that can return `None`; `list[int]` that holds strings | — |

## PY-EXC Exceptions

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-EXC-1 | Bare `except:` or `except BaseException` | Catches `KeyboardInterrupt` and `SystemExit` too | A top-level handler that logs and re-raises |
| PY-EXC-2 | Swallowed error | `except Exception: pass`, `except ...: return None` with no log, so a failure looks like success | `contextlib.suppress(SpecificError)` with a comment |
| PY-EXC-3 | Cause lost | `raise NewError(...)` inside `except` without `from exc`; `str(exc)` replacing the traceback | `raise ... from None` when hiding the cause is deliberate and commented |
| PY-EXC-4 | `try` block too wide | Many statements in `try` for an error only one of them raises | — |
| PY-EXC-5 | `return`, `break` or `continue` in `finally` | Silently discards the exception | — |
| PY-EXC-6 | Broad catch outside a boundary | `except Exception` in domain code instead of the request handler, worker loop or `main` | At a boundary that logs and converts |
| PY-EXC-7 | Generic exceptions raised | `raise Exception("...")` where callers need to tell cases apart | The project's base error or a specific subclass |

## PY-RES Resources

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-RES-1 | Resource not closed on error | `open()`, sockets, database sessions, locks, `zipfile`, `tempfile` objects without `with` or `try/finally` | Framework-managed sessions (a FastAPI dependency with `yield`) |
| PY-RES-2 | Outbound call without a timeout | `requests.get(url)`, `httpx.Client()` without `timeout`, `urllib.request.urlopen(url)` without `timeout`, `socket` without `settimeout` | A client created once with a timeout the call inherits |
| PY-RES-3 | Unbounded growth | Caches without a size limit, lists that grow per request, `lru_cache(maxsize=None)` on unbounded keys | Bounded caches |
| PY-RES-4 | Encoding left to the platform | `open(path)` or `read_text()` without `encoding` on text files | Binary mode |

## PY-SEC Security

| ID | What | Signal | CWE | Not a finding |
|---|---|---|---|---|
| PY-SEC-1 | SQL injection | f-strings, `%` or `.format` inside `execute`, `text()`, `raw()`, `extra()`, `cursor.execute(query % args)` | CWE-89 | Bound parameters (`execute(sql, params)`, `text(":name")` with a dict), ORM query builders |
| PY-SEC-2 | OS command injection | `subprocess.*(..., shell=True)` with input, `os.system`, `os.popen`, a command string built with input | CWE-78 | An argument list without `shell=True` (`subprocess.run(["git", "log", ref], check=True)`) |
| PY-SEC-3 | Code injection | `eval`, `exec`, `compile` on input; `__import__` or `importlib` with an input name | CWE-94, CWE-95 | `ast.literal_eval` for literals |
| PY-SEC-4 | Unsafe deserialization | `pickle`, `cPickle`, `dill`, `marshal`, `shelve`, `jsonpickle` loading data from a request, a file the user controls, a queue or a cache; `yaml.load` without `SafeLoader`; `torch.load` without `weights_only=True` | CWE-502 | `json`, `yaml.safe_load`, pickles the process wrote and only it reads |
| PY-SEC-5 | XML external entities | `xml.etree`, `lxml` or `xml.dom` parsing untrusted XML with entity resolution | CWE-611 | `defusedxml` |
| PY-SEC-6 | Path traversal | `open(base / user_value)`, `send_file(user_path)`, archive extraction without checking member paths (`extractall`) | CWE-22 | Resolved path checked with `is_relative_to(base)`; `tarfile` with `filter="data"` (3.12) |
| PY-SEC-7 | Server-side request forgery | `requests.get(user_url)` or `httpx` with a URL or host from input, no allow list | CWE-918 | A fixed host with a user-supplied path segment that is encoded |
| PY-SEC-8 | Template injection and XSS | `render_template_string(input)`, Jinja2 `Environment(autoescape=False)` for HTML, `Markup(input)`, Django `mark_safe(input)` or the `safe` filter on input | CWE-1336, CWE-79 | Autoescaped templates |
| PY-SEC-9 | Weak randomness for secrets | `random` for tokens, passwords, reset codes, session IDs | CWE-330 | `secrets.token_urlsafe`, `secrets.compare_digest` |
| PY-SEC-10 | Weak password storage or hashing | `md5`, `sha1` or a plain `sha256` for passwords; no salt | CWE-916, CWE-327 | `argon2`, `bcrypt`, `scrypt`, `hashlib.pbkdf2_hmac` with a high iteration count |
| PY-SEC-11 | Secrets in code, config or logs | Literal keys, tokens or passwords; secrets logged or put in exception messages | CWE-798, CWE-532 | Values read from the environment or a secret store; placeholders in examples |
| PY-SEC-12 | Timing-unsafe comparison of secrets | `==` on tokens, signatures, HMACs | CWE-208 | `hmac.compare_digest`, `secrets.compare_digest` |
| PY-SEC-13 | `assert` used as a security or validation check | `assert user.is_admin` (removed under `python -O`) | CWE-617 | Asserts in tests and for internal invariants |
| PY-SEC-14 | TLS verification off | `verify=False`, `ssl._create_unverified_context()`, `CERT_NONE` | CWE-295 | Tests against a local server, clearly scoped |
| PY-SEC-15 | Debug or permissive settings that ship | `debug=True`, Django `DEBUG = True` without an environment switch, CORS `allow_origins=["*"]` with credentials | CWE-489, CWE-942 | Development-only settings files |
| PY-SEC-16 | Missing authorization on a new entry point | A FastAPI route without the project's auth dependency; a Django view without the permission decorator the neighbors use; object loaded by ID without an ownership check | CWE-862, CWE-639 | Routes that are public on purpose (health checks) |
| PY-SEC-17 | Insecure temporary files | `tempfile.mktemp`, predictable names in shared folders | CWE-377 | `NamedTemporaryFile`, `mkstemp`, `TemporaryDirectory` |

## PY-ASYNC Async

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-ASYNC-1 | Blocking call in `async def` | `requests`, `time.sleep`, sync database drivers, large file reads inside a coroutine | `await asyncio.to_thread(...)`, async clients |
| PY-ASYNC-2 | Coroutine never awaited | Calling an `async def` without `await` (the call returns a coroutine object) | — |
| PY-ASYNC-3 | Fire-and-forget task | `asyncio.create_task(...)` result not stored; the task can be garbage-collected | Tasks kept in a set or a `TaskGroup` |
| PY-ASYNC-4 | Shared state without a lock across awaits | Read-modify-write on shared data with an `await` in between | `asyncio.Lock` |

## PY-PERF Performance

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-PERF-1 | Queries in a loop (N+1) | A repository or ORM call inside a loop over rows; lazy relationships accessed per row | One query with a join or `IN`, eager loading |
| PY-PERF-2 | Quadratic work on data that can be large | `x in list` inside a loop, nested loops over two large collections | Small, bounded collections |
| PY-PERF-3 | Whole files or result sets in memory | `read()` of an upload, `.all()` of a large table, `list()` of a big generator | Bounded sizes the code enforces |
| PY-PERF-4 | String building with `+=` in a loop | Repeated concatenation | `"".join(parts)`, `io.StringIO` |

## PY-STYLE Style

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-STYLE-1 | Breaks the project's formatter or linter config | What `ruff`, `flake8` or `black` would flag with the project's settings | Rules the project disables |
| PY-STYLE-2 | `print` in library code | `print` for diagnostics outside CLI output | CLI output meant for the person |
| PY-STYLE-3 | Unclear names or dead code | Single-letter names outside short loops, commented-out code, unused functions or imports | — |
| PY-STYLE-4 | Missing docstring on public API | Public module, class or function without a docstring, in a project that writes them | — |
| PY-STYLE-5 | Logging anti-patterns | f-strings in log calls, `logging.basicConfig` in library modules, `logger.error` without the traceback inside `except` | — |

## PY-TEST Tests

| ID | What | Signal | Not a finding |
|---|---|---|---|
| PY-TEST-1 | New behavior without a test | New function, branch, endpoint or CLI command with no test that exercises it | Pure refactors covered by existing tests |
| PY-TEST-2 | Test that cannot fail | No assert, asserts on mocks only, `assert True`, catching the error the test should see | — |
| PY-TEST-3 | Network, real time or sleeps in tests | Real HTTP calls, `datetime.now()` in assertions, `time.sleep` | Fakes, injected clocks, mock transports |
| PY-TEST-4 | Order-dependent or shared-state tests | Module globals mutated by tests, files written outside `tmp_path` | Fixtures with function scope |
| PY-TEST-5 | Scenario of the spec without its test | In an SDD change, a scenario `S-n` with no test named for it | — |
