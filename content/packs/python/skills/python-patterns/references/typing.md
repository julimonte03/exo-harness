# Type hints

How `python-patterns` types code. Use only what the project's `requires-python` supports (the table in `SKILL.md`, section 1).

## What to annotate

| Element | Annotate | Notes |
|---|---|---|
| Public functions and methods | Every parameter and the return type | `-> None` too, so the checker sees the function |
| Private helpers | When the type is not obvious | The checker infers simple ones |
| Module-level constants | When the type is not obvious from the literal | `Final` when the project uses it |
| Local variables | Only an empty collection or a `None` start | `items: list[Task] = []` |
| Tests | As the project does | Many projects skip hints in tests |

## Choosing the type

- **Parameters accept the widest type you need:** `Iterable[str]` if you only loop, `Sequence[str]` if you index, `Mapping[str, int]` if you only read.
- **Return the concrete type:** `list[str]`, `dict[str, int]`, so callers can use every method.
- **Optional:** `Task | None` (3.10, or any version with `from __future__ import annotations` in the module). A function that returns `None` on "not found" says so in its type; prefer raising when callers always expect a value.
- **Closed sets:** `Literal["pending", "done"]`; an `Enum` when the value travels through several modules.
- **Records:** a frozen dataclass; `TypedDict` only for dicts that must stay dicts (JSON payloads, kwargs).
- **Collaborators:** `Protocol` for what a function needs from an object (`class Clock(Protocol): def now(self) -> datetime: ...`), so tests pass a fake without inheritance.
- **Callables:** `Callable[[int], str]`; `ParamSpec` for decorators that keep the signature.
- **Generics:** a `TypeVar` (or 3.12 generic syntax) only when it links two places, such as an input and an output: `def first(items: Sequence[T]) -> T`. A type variable used once is just `object`.
- **New names for clarity:** `InvoiceNumber = NewType("InvoiceNumber", str)` when two strings must not be mixed up.

## What to avoid

| Avoid | Instead |
|---|---|
| `Any` on a value whose shape you know | The real type, a `TypedDict`, or `object` plus narrowing |
| `cast(Foo, x)` to silence the checker | Narrow with `isinstance`, or fix the source type; `cast` only with a comment on why it is safe |
| `# type: ignore` without a code | `# type: ignore[attr-defined]  # <reason>` |
| `Optional[X]` and `List[X]` in new code on 3.10+ | `X \| None` and `list[X]`, unless the module already uses the old style |
| `dict` passed across modules with known keys | A dataclass or a `TypedDict` |
| Mutable class attributes as defaults | `field(default_factory=list)` in dataclasses |

## Narrowing

```python
def total_of(value: Decimal | str) -> Decimal:
    if isinstance(value, str):
        value = Decimal(value)
    return value.quantize(Decimal("0.01"))
```

- `isinstance`, `is None` checks and `match` statements narrow; the checker follows them.
- A function that checks a type can declare it: `def is_task(x: object) -> TypeGuard[Task]` (3.10), or `TypeIs` (3.13, or `typing_extensions`).

## Imports for types and cycles

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from invoices.customers.models import Customer


def tax_for(customer: Customer) -> Decimal: ...
```

The import runs only for the type checker, so it adds no runtime dependency and breaks no cycle at import time. Keep the real dependency direction in mind: a type-only import from a higher layer is still a design smell.

## Running the checker

- Use the project's checker and config (`mypy`, `pyright`, `pyrefly` or `ty`); `strict` settings when the project has them.
- New code passes with no new errors; do not fix unrelated old errors in the same change.
- Without a checker in the project, keep the hints correct anyway and say that nothing checked them.
