# py-invoices: verdad conocida

`py-invoices` es una API de facturación en Python con layout `src/`:
- clientes con límite de crédito;
- facturas con impuestos por región y categoría, códigos de descuento y un ciclo de vida de estados;
- pagos con tarjeta (solo tarjetas de prueba en el sandbox) y conciliación contra la factura;
- tokens firmados con HMAC y permisos por rol.

Declara FastAPI, pydantic, SQLAlchemy y Alembic en `[project] dependencies`, y pytest en `optional-dependencies`. No hace falta que corra. Igual, el dominio (`billing`, `payments`, `customers`, `auth`, `core`) es Python puro y sus tests pasan con solo pytest.

Tamaño: 1493 líneas en total, de las cuales 1188 son Python de producción (`src/` más `alembic/env.py`).

## Cómo se derivó

Todo sale de aplicar a mano las reglas del contrato del brief:
- **Raíces de imports:** `src/` y la raíz del fixture.
- **Destino de una arista:** la carpeta del archivo resuelto.
- **Tests y migraciones:** no son módulos ni originan aristas.

Los diez módulos son las carpetas con código de producción. `alembic/versions/` no cuenta (solo tiene migraciones) y `tests/` tampoco. Las 24 aristas salen de leer los imports de cada archivo de producción.

## Casos difíciles

1. **Ciclo `billing` ↔ `payments`.**
   - `src/invoices/billing/balance.py` importa `from ..payments.ledger import ...` para calcular el saldo.
   - `src/invoices/payments/reconciliation.py` importa `from invoices.billing.status import ...` para mover la factura de estado.

   Es el único ciclo entre dos módulos. Hay otro más largo, de tres: `billing` → `customers` → `storage` → `billing`. Pasa por las dos aristas "escondidas" de los casos 5 y 6.

2. **Módulo grande: `src/invoices/api`.** Tiene 9 archivos y 409 líneas: los routers por recurso, `deps.py`, `schemas.py`, `errors.py` y `app.py`.
   - **Casi grande:** `src/invoices/billing` tiene 6 archivos pero 185 líneas. No llega a 400, así que no hay que partirlo.

3. **Relativos de dos niveles.**
   - `src/invoices/billing/tax.py` hace `from ..core import errors`. Como existe `core/errors.py`, resuelve a ese archivo: arista `billing` → `core`.
   - Lo mismo, con alias, en `src/invoices/api/errors.py`: `from ..core import errors as domain`.
   - Otros de dos niveles: `billing/balance.py`, `customers/directory.py` y `storage/repositories.py`.
   - **Trampa de mismo nivel:** `src/invoices/__init__.py` usa relativos desde el propio paquete (`from .billing import ...`). Como el archivo es el `__init__.py` de `invoices`, el nivel 1 es `invoices` y resuelve a `billing`.
   - **Sin arista:** `src/invoices/api/app.py` hace `from . import routes_auth, ...`. Resuelve a archivos de la misma carpeta.

4. **`import x as y`.**
   - `src/invoices/api/deps.py` hace `import invoices.storage.repositories as repos`. Es la arista `api` → `storage` por la forma `import a.b.c`.
   - `src/invoices/billing/__init__.py` hace `from .discounts import lookup as lookup_discount`, de la misma carpeta, así que no da arista.

5. **Import opcional en `try/except ImportError`.** `src/invoices/customers/directory.py` importa `CustomerRepository` de `..storage.repositories` dentro de un `try`.
   - Es la única arista `customers` → `storage`.
   - Según el contrato, un import en un `try` cuenta.

6. **Import dentro de un `if`.** `src/invoices/billing/tax.py` importa `Customer` bajo `if TYPE_CHECKING:`.
   - Es la única arista `billing` → `customers`.
   - Cuenta igual que la del `try`.

7. **Import dentro de una función.** `serve()` en `src/invoices/cli.py` importa `invoices.api.app` adentro de la función, para no cargar FastAPI en cada comando.
   - Es la única arista `src/invoices` → `api`.
   - El contrato no la nombra, pero es un import de verdad (ver la última sección).

8. **Re-exports en `__init__.py`.**
   - `src/invoices/__init__.py` re-exporta `InvoiceError` (de `core`) y `compute_totals` (de `billing`).
   - Entonces `src/invoices/plugins/csv_export.py`, con `from invoices import InvoiceError`, resuelve a `src/invoices/__init__.py`. La arista va a `src/invoices`, **no** a `core`.
   - Lo mismo con `from invoices.auth import Role` en `src/invoices/api/routes_auth.py`: resuelve a `auth/__init__.py`, que está en la misma carpeta que el archivo que define `Role`.
   - Lo mismo con `from invoices.billing import ...`: resuelve a `billing/__init__.py`, porque no existe `billing/InvoiceStatus.py`.

9. **Import dinámico que no es arista.** `src/invoices/cli.py` carga plugins con `importlib.import_module("invoices.plugins." + name)`.
   - El módulo `src/invoices/plugins` existe, pero no recibe ninguna arista.
   - Si se tomara el string como import, aparecería un ciclo falso `src/invoices` ↔ `src/invoices/plugins`: la arista inversa sí existe, por el re-export del caso 8.

10. **Paquete externo con el nombre de una carpeta local.** `alembic/env.py` hace `from alembic import context`, y en la raíz hay una carpeta `alembic/`. Pero no tiene `__init__.py` ni `context.py`, así que no resuelve: es la dependencia externa y no hay arista. Las migraciones de `alembic/versions/` hacen lo mismo, pero no originan aristas.
    - **Ojo:** `alembic/env.py` no está dentro de `alembic/versions/`. Por eso es código de producción, y `alembic` es un módulo con aristas a `core` y `storage`.

11. **Entrypoints de las tres reglas.**
    - `src/invoices/__main__.py`: es un `__main__.py`.
    - `src/invoices/cli.py`: lo apunta `[project.scripts] invoices = "invoices.cli:main"`, y existe en `src/`.
    - `src/invoices/api/app.py`: tiene `if __name__ == "__main__":`.

12. **Parece credencial y no lo es.** `.env.example` está excluido de `sensitive_files` por el contrato, y no trae valores. La clave de firma se lee de `os.environ["INVOICES_SIGNING_KEY"]` en `src/invoices/auth/tokens.py`. Ni el `Dockerfile` ni el CI tienen secretos.

13. **Datos sintéticos.**
    - Las únicas tarjetas son de prueba publicadas (`4111 1111 1111 1111`, `4242...`, `5555...4444`), en `src/invoices/payments/cards.py` y en los tests.
    - El test del sandbox no escribe una tarjeta válida real: `tests/test_payments.py` arma en tiempo de ejecución un número que pasa Luhn y no es de prueba.
    - Los emails son `@example.com`.

## Capacidades y sus tests

- **`invoice-totals`:** `tests/test_billing.py` prueba el redondeo, el impuesto después del descuento, las tasas por categoría y los límites.
- **`invoice-lifecycle`:** `tests/test_billing.py` prueba las transiciones prohibidas y el saldo.
- **`card-payments`:** `tests/test_payments.py` prueba Luhn, el sandbox, la conciliación y el reembolso.
- **`access-control`:** `tests/test_auth.py` prueba los roles, la expiración, la manipulación del token y la clave desde el entorno.
- **`customer-directory`:** `tests/test_customers.py` prueba el email único y normalizado y el límite de crédito.

## Decisiones sobre el contrato

- **`alembic/env.py` es producción:** el contrato solo marca como migraciones lo que está dentro de `alembic/versions/`.
- **Imports dentro de funciones cuentan como arista**, igual que los de `try` e `if`. El contrato solo excluye los strings.
- **`languages`** lista solo los lenguajes de código (`python`). YAML, Markdown y TOML aparecen en el inventario, pero no se exigen.
- **`hard_cases`** son objetos `{case, paths, detail}`, para que cada ruta se pueda verificar.

```json
{
  "fixture": "py-invoices",
  "languages": ["python"],
  "frameworks": ["alembic", "fastapi", "pydantic", "pytest", "sqlalchemy"],
  "entrypoints": [
    "src/invoices/__main__.py",
    "src/invoices/api/app.py",
    "src/invoices/cli.py"
  ],
  "test_files": [
    "tests/conftest.py",
    "tests/test_auth.py",
    "tests/test_billing.py",
    "tests/test_customers.py",
    "tests/test_payments.py"
  ],
  "ci": [".github/workflows/ci.yml"],
  "migrations": ["alembic/versions/0001_initial.py"],
  "api_contracts": ["openapi.yaml"],
  "infrastructure": ["Dockerfile"],
  "sensitive_files": [],
  "modules": [
    "alembic",
    "src/invoices",
    "src/invoices/api",
    "src/invoices/auth",
    "src/invoices/billing",
    "src/invoices/core",
    "src/invoices/customers",
    "src/invoices/payments",
    "src/invoices/plugins",
    "src/invoices/storage"
  ],
  "edges": [
    ["alembic", "src/invoices/core"],
    ["alembic", "src/invoices/storage"],
    ["src/invoices", "src/invoices/api"],
    ["src/invoices", "src/invoices/billing"],
    ["src/invoices", "src/invoices/core"],
    ["src/invoices", "src/invoices/payments"],
    ["src/invoices/api", "src/invoices/auth"],
    ["src/invoices/api", "src/invoices/billing"],
    ["src/invoices/api", "src/invoices/core"],
    ["src/invoices/api", "src/invoices/customers"],
    ["src/invoices/api", "src/invoices/payments"],
    ["src/invoices/api", "src/invoices/storage"],
    ["src/invoices/auth", "src/invoices/core"],
    ["src/invoices/billing", "src/invoices/core"],
    ["src/invoices/billing", "src/invoices/customers"],
    ["src/invoices/billing", "src/invoices/payments"],
    ["src/invoices/customers", "src/invoices/core"],
    ["src/invoices/customers", "src/invoices/storage"],
    ["src/invoices/payments", "src/invoices/billing"],
    ["src/invoices/payments", "src/invoices/core"],
    ["src/invoices/plugins", "src/invoices"],
    ["src/invoices/plugins", "src/invoices/billing"],
    ["src/invoices/storage", "src/invoices/billing"],
    ["src/invoices/storage", "src/invoices/core"]
  ],
  "capabilities": [
    {
      "name": "invoice-totals",
      "key_files": [
        "src/invoices/billing/totals.py",
        "src/invoices/billing/tax.py",
        "src/invoices/billing/discounts.py"
      ],
      "rules": [
        "El importe de cada línea es cantidad por precio unitario, redondeado a centavos con medio hacia arriba.",
        "El descuento se reparte entre las líneas según su importe y el impuesto se cobra sobre lo ya descontado, con la tasa de la región y de la categoría de cada línea (exento paga cero).",
        "Un descuento porcentual no puede superar el 50 % y ningún descuento deja el subtotal por debajo de cero.",
        "Una factura tiene entre 1 y 200 líneas, y cada cantidad va de 1 a 10 000."
      ]
    },
    {
      "name": "invoice-lifecycle",
      "key_files": [
        "src/invoices/billing/status.py",
        "src/invoices/billing/balance.py",
        "src/invoices/api/routes_invoices.py"
      ],
      "rules": [
        "Las únicas transiciones son draft a issued o void, issued a partially_paid, paid o void, y partially_paid a paid; paid y void son finales.",
        "Una factura con dinero cobrado no se puede anular: primero se reembolsan los pagos.",
        "El saldo pendiente es el total menos lo cobrado y no reembolsado, y nunca es negativo."
      ]
    },
    {
      "name": "card-payments",
      "key_files": [
        "src/invoices/payments/cards.py",
        "src/invoices/payments/reconciliation.py",
        "src/invoices/payments/ledger.py"
      ],
      "rules": [
        "Un número de tarjeta tiene de 13 a 19 dígitos y tiene que pasar el control de Luhn.",
        "En el sandbox solo se aceptan las tarjetas de prueba publicadas.",
        "La conciliación pasa la factura a partially_paid si lo cobrado cubre una parte y a paid si cubre el total; se tolera un centavo de más, no dos.",
        "Una factura en draft o void no admite pagos.",
        "Un reembolso es positivo y no supera lo que queda del pago."
      ]
    },
    {
      "name": "access-control",
      "key_files": [
        "src/invoices/auth/permissions.py",
        "src/invoices/auth/tokens.py",
        "src/invoices/api/deps.py"
      ],
      "rules": [
        "viewer solo lee; accountant además crea, emite y cobra facturas; solo admin anula facturas, reembolsa pagos y edita clientes.",
        "Un token firmado con HMAC-SHA256 que fue alterado se rechaza.",
        "Un token vive entre 1 segundo y 12 horas, y vencido se rechaza.",
        "La clave de firma se lee de la variable de entorno INVOICES_SIGNING_KEY y tiene que tener al menos 32 caracteres."
      ]
    },
    {
      "name": "customer-directory",
      "key_files": [
        "src/invoices/customers/models.py",
        "src/invoices/customers/directory.py"
      ],
      "rules": [
        "El email de un cliente se normaliza a minúsculas y es único sin importar mayúsculas.",
        "El límite de crédito no puede ser negativo.",
        "Una factura se emite solo si lo que el cliente ya debe más el total de la factura no supera su límite de crédito.",
        "La región fiscal del cliente tiene que ser una de las soportadas (US-CA, US-NY, DE, ES)."
      ]
    }
  ],
  "hard_cases": [
    {
      "case": "cycle",
      "paths": ["src/invoices/billing/balance.py", "src/invoices/payments/reconciliation.py"],
      "detail": "billing -> payments (from ..payments.ledger) y payments -> billing (from invoices.billing.status)."
    },
    {
      "case": "large-module",
      "paths": ["src/invoices/api"],
      "detail": "9 archivos y 409 líneas. src/invoices/billing tiene 6 archivos pero 185 líneas: no es grande."
    },
    {
      "case": "relative-imports",
      "paths": [
        "src/invoices/billing/tax.py",
        "src/invoices/api/errors.py",
        "src/invoices/billing/balance.py",
        "src/invoices/__init__.py",
        "src/invoices/api/app.py"
      ],
      "detail": "from ..core import errors resuelve a core/errors.py. Los relativos del __init__.py de invoices parten del propio paquete. from . import routes_* es de la misma carpeta: no hay arista."
    },
    {
      "case": "import-as",
      "paths": ["src/invoices/api/deps.py", "src/invoices/billing/__init__.py"],
      "detail": "import invoices.storage.repositories as repos es la arista api -> storage. lookup as lookup_discount es de la misma carpeta."
    },
    {
      "case": "optional-import-try",
      "paths": ["src/invoices/customers/directory.py"],
      "detail": "from ..storage.repositories import CustomerRepository dentro de try/except ImportError: es la única arista customers -> storage."
    },
    {
      "case": "import-under-if",
      "paths": ["src/invoices/billing/tax.py"],
      "detail": "from ..customers.models import Customer bajo if TYPE_CHECKING: es la única arista billing -> customers."
    },
    {
      "case": "import-inside-function",
      "paths": ["src/invoices/cli.py"],
      "detail": "serve() importa invoices.api.app adentro de la función: es la única arista src/invoices -> src/invoices/api."
    },
    {
      "case": "init-re-exports",
      "paths": [
        "src/invoices/__init__.py",
        "src/invoices/plugins/csv_export.py",
        "src/invoices/api/routes_auth.py"
      ],
      "detail": "from invoices import InvoiceError resuelve a src/invoices/__init__.py: la arista es plugins -> src/invoices, no plugins -> core."
    },
    {
      "case": "dynamic-import-not-edge",
      "paths": ["src/invoices/cli.py", "src/invoices/plugins"],
      "detail": "importlib.import_module(\"invoices.plugins.\" + name) no es arista: plugins no recibe aristas, y src/invoices <-> plugins no es un ciclo."
    },
    {
      "case": "external-package-named-like-local-folder",
      "paths": ["alembic/env.py", "alembic/versions/0001_initial.py"],
      "detail": "from alembic import context no resuelve a la carpeta alembic/ (no tiene __init__.py ni context.py): es externo. alembic/env.py es producción, no migración."
    },
    {
      "case": "entrypoints-three-rules",
      "paths": ["src/invoices/__main__.py", "src/invoices/cli.py", "src/invoices/api/app.py", "pyproject.toml"],
      "detail": "__main__.py, el script invoices = invoices.cli:main y la guarda if __name__ == \"__main__\" de app.py."
    },
    {
      "case": "not-a-sensitive-file",
      "paths": [".env.example", "src/invoices/auth/tokens.py"],
      "detail": ".env.example está excluido de sensitive_files. La clave se lee de os.environ[\"INVOICES_SIGNING_KEY\"]."
    },
    {
      "case": "synthetic-data",
      "paths": ["src/invoices/payments/cards.py", "tests/test_payments.py", "tests/test_auth.py"],
      "detail": "Solo tarjetas de prueba publicadas y emails @example.com. La tarjeta válida que no es de prueba se arma en tiempo de ejecución."
    }
  ]
}
```
