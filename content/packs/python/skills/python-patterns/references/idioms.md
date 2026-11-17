# Python idioms and their anti-patterns

Defaults for `python-patterns`. The project's code wins: if the neighbors do it another way on purpose, follow them.

## Collections and iteration

| Instead of | Write | Why |
|---|---|---|
| `for i in range(len(items)): item = items[i]` | `for i, item in enumerate(items):` | No index arithmetic |
| Two lists walked by index | `for a, b in zip(xs, ys, strict=True):` (3.10) | `strict` fails loudly on different lengths |
| `result = []` plus `append` in a loop with no side effects | `[transform(x) for x in xs if keep(x)]` | One expression, one purpose |
| A comprehension with two `if` and a nested `for` | A plain loop, or a helper function | Readability beats brevity |
| `if len(items) > 0:` | `if items:` | Only when an empty and a missing collection mean the same |
| `found = False` plus a loop and `break` | `any(pred(x) for x in xs)` | Says what it checks |
| `dict.keys()` in a membership test | `if key in mapping:` | Same result, less noise |
| `d[key] if key in d else default` | `d.get(key, default)` | One lookup |
| Building a dict of lists by hand | `collections.defaultdict(list)` | No missing-key branch |
| Counting by hand | `collections.Counter(xs)` | Built for it |
| Reading a whole large file to iterate | `for line in file:` or a generator | Constant memory |

## Values and records

- **Records:** `@dataclass(frozen=True, slots=True)` (`slots` from 3.10) for values; `@dataclass` when the object changes; pydantic or attrs when the project uses them, mainly at the edges (requests, settings).
- **Closed sets:** `enum.Enum` (or `StrEnum` from 3.11) for values that travel through the code; `Literal["draft", "issued"]` for a parameter.
- **Money:** `decimal.Decimal`, built from strings (`Decimal("19.99")`), with an explicit rounding (`quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`). Never `float`.
- **Time:** `datetime.now(timezone.utc)`; store and compare aware datetimes; convert to local time only to display. Inject the clock (a parameter or a callable) so tests control it.
- **Identity:** `is None`, `is True` only for singletons; `==` for values.
- **Constants:** module-level `UPPER_CASE`, typed with `Final` when the project uses it.

## Functions

- **No mutable defaults:**

  ```python
  def add_tags(task: Task, tags: list[str] | None = None) -> Task:
      tags = [] if tags is None else tags
      ...
  ```

- **Keyword-only flags:** `def list(self, *, include_done: bool = True)`, so callers write the name.
- **Early return** instead of deep nesting; one level of `if` inside a loop at most.
- **Late binding in closures:** a lambda created in a loop sees the last value of the loop variable; bind it as a default argument (`lambda x=x: ...`) or use `functools.partial`.
- **Small and pure where possible:** effects (disk, network, clock) at the edges, logic in functions that take values and return values.

## Strings

- f-strings for building text; `%`-style arguments only in logging calls (`logger.info("saved %s", name)`).
- `"".join(parts)` instead of `+=` in a loop.
- `str.removeprefix` and `str.removesuffix` (3.9) instead of slicing by length.
- Never build SQL, shell commands or HTML with f-strings: use parameters, argument lists and the template engine's escaping.

## Files and paths

- `Path(base) / name`, never string concatenation.
- `path.read_text(encoding="utf-8")` and `write_text(..., encoding="utf-8")`: the default encoding changes between platforms.
- Writes that must not leave a half-written file: write to a temporary file in the same folder, then `os.replace`.
- A path built from user input must stay inside its base: `resolved = (base / name).resolve()` and check `resolved.is_relative_to(base.resolve())` (3.9).

## EAFP and LBYL

- Prefer EAFP (try the operation, catch the specific error) when the check and the use could race (files, dict keys shared between threads) or the failure is rare.
- Prefer LBYL (check first) when the check is cheap and the failure is common, or when the operation has side effects you cannot undo.
- Either way, catch the narrowest exception: `except KeyError`, not `except Exception`.

## Performance without guessing

- Measure before optimizing (`python -m cProfile`, `timeit`); keep the clear version unless the numbers say otherwise.
- `set` or `dict` for membership tests in loops, not `list`.
- Database access in loops (N+1) is the usual culprit: load in one query.
- `functools.cache` or `lru_cache` only on pure functions with hashable arguments; never on methods that capture `self` without thinking about memory.
