"""R1, módulos y aristas (F6, ADR-0015): los casos difíciles de cada lenguaje."""

from __future__ import annotations

import json
from pathlib import Path

from exo.discovery import graph


def _repo(root: Path, tree: dict[str, str]) -> Path:
    for rel, text in tree.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return root


def _edges(root: Path) -> set[tuple[str, str]]:
    return {(e["from"], e["to"]) for e in graph.build(root)["edges"]}


def test_python_relativos_ciclo_alias_try_y_strings(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'app'\n",
            "src/app/__init__.py": "from .api import router  # re-export\n",
            "src/app/api/__init__.py": "",
            "src/app/api/routes.py": "from ..billing import service as svc\nfrom ..core.errors import AppError\n",
            "src/app/billing/__init__.py": "",
            "src/app/billing/service.py": "import app.payments.luhn as luhn\n",
            "src/app/payments/__init__.py": "",
            "src/app/payments/luhn.py": (
                "try:\n    from app.billing import service\nexcept ImportError:\n    service = None\n"
                "import importlib\nplugin = importlib.import_module('app.plugins.' + 'x')\n"
                "import requests\n"
            ),
            "src/app/core/__init__.py": "",
            "src/app/core/errors.py": "class AppError(Exception):\n    pass\n",
            "tests/test_routes.py": "from app.api import routes\n",
        },
    )
    assert _edges(root) == {
        ("src/app", "src/app/api"),
        ("src/app/api", "src/app/billing"),
        ("src/app/api", "src/app/core"),
        ("src/app/billing", "src/app/payments"),
        ("src/app/payments", "src/app/billing"),
    }
    data = graph.build(root)
    modules = {m["path"]: m for m in data["modules"]}
    assert "tests" not in modules
    assert modules["src/app/payments"]["external"] == ["importlib", "requests"]
    assert modules["src/app/billing"]["fan_in"] == 2 and modules["src/app/billing"]["fan_out"] == 1


PY_FILES = [
    "app/__init__.py",
    "app/main.py",
    "app/util.py",
    "app/helpers/__init__.py",
    "app/services/__init__.py",
    "app/services/billing.py",
    "app/services/users.py",
]


def test_python_from_import_resuelve_cada_nombre(tmp_path: Path) -> None:
    """M3: `from x import a, b` suma todos los destinos; si ninguno resuelve, el módulo."""
    index = graph.Index.build(tmp_path, PY_FILES)
    cases = {
        b"from app.services import billing, users, LIMIT\n": {
            "app/services/billing.py",
            "app/services/users.py",
        },
        b"from app.services import LIMIT, Client\n": {"app/services/__init__.py"},
        b"from . import util, helpers\n": {"app/util.py", "app/helpers/__init__.py"},
        b"from .services import (billing,\n    users)\n": {
            "app/services/billing.py",
            "app/services/users.py",
        },
        b"from .services import LIMIT\n": {"app/services/__init__.py"},
        # Si no parsea, el fallback con regex hace lo mismo.
        b"from app.services import billing, users\ndef broken(:\n": {
            "app/services/billing.py",
            "app/services/users.py",
        },
    }
    for source, expected in cases.items():
        assert graph.python_imports("app/main.py", source, index)[0] == expected, source


def test_ast_no_emite_avisos(tmp_path: Path) -> None:
    """L2: un escape inválido en un string del proyecto no ensucia la salida."""
    import warnings

    index = graph.Index.build(tmp_path, PY_FILES)
    source = b"import app.util\nPATTERN = '" + bytes([92]) + b"d'\n"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved, _ = graph.python_imports("app/main.py", source, index)
    assert resolved == {"app/util.py"}
    assert [str(w.message) for w in caught] == []


def test_python_que_no_parsea_cae_a_regex(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {
            "app/__init__.py": "",
            "app/a.py": "from app.b import x\ndef broken(:\n",
            "app/b/__init__.py": "x = 1\n",
        },
    )
    assert _edges(root) == {("app", "app/b")}


def test_js_ts_alias_index_workspace_dinamico_y_require_con_variable(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {
            "package.json": json.dumps({"name": "shop", "workspaces": ["packages/*"]}),
            "packages/shared/package.json": json.dumps(
                {"name": "@shop/shared", "main": "src/index.ts"}
            ),
            "packages/shared/src/index.ts": "export const price = 1;\n",
            "packages/web/package.json": json.dumps({"name": "@shop/web"}),
            "packages/web/tsconfig.json": (
                '{\n  // comments are allowed\n  "compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]},},\n}\n'
            ),
            "packages/web/src/main.tsx": (
                "import { App } from '@/pages/App';\nimport { price } from '@shop/shared';\n"
                "import React from 'react';\nimport { Link } from 'react-router';\n"
            ),
            "packages/web/src/pages/App.tsx": (
                "import Button from '../components';\n"
                "const Admin = () => import('./admin/Admin');\n"
                "// import { old } from '../legacy/old';\n"
            ),
            "packages/web/src/pages/admin/Admin.tsx": "export default 1;\n",
            "packages/web/src/components/index.ts": "export { default } from './Button';\n",
            "packages/web/src/components/Button.tsx": "export default () => null;\n",
            "packages/web/src/legacy/old.ts": "export const old = 1;\n",
            "packages/api/src/db/index.js": (
                "const name = 'pg';\nconst driver = require(name);\n"
                "const routes = require('../routes/orders');\n"
            ),
            "packages/api/src/routes/orders.js": "const { price } = require('@shop/shared');\nmodule.exports = {};\n",
            "packages/api/src/routes/orders.test.js": "require('./orders');\n",
        },
    )
    assert _edges(root) == {
        ("packages/web/src", "packages/web/src/pages"),
        ("packages/web/src", "packages/shared/src"),
        ("packages/web/src/pages", "packages/web/src/components"),
        ("packages/web/src/pages", "packages/web/src/pages/admin"),
        ("packages/api/src/db", "packages/api/src/routes"),
        ("packages/api/src/routes", "packages/shared/src"),
    }
    modules = {m["path"]: m for m in graph.build(root)["modules"]}
    assert modules["packages/web/src"]["external"] == ["react", "react-router"]


def test_tsconfig_extends_relativo_en_varios_niveles_y_sin_ciclos(tmp_path: Path) -> None:
    """M4: se siguen los `extends` relativos y se fusionan las `compilerOptions`."""
    root = _repo(
        tmp_path,
        {
            "tsconfig.paths.json": json.dumps(
                {"compilerOptions": {"baseUrl": ".", "paths": {"@shared/*": ["libs/shared/*"]}}}
            ),
            "apps/web/tsconfig.base.json": json.dumps({"extends": "../../tsconfig.paths.json"}),
            "apps/web/tsconfig.json": json.dumps(
                {"extends": "./tsconfig.base.json", "compilerOptions": {"strict": True}}
            ),
            "apps/web/src/main.ts": "import { price } from '@shared/price';\n",
            "libs/shared/price.ts": "export const price = 1;\n",
            # Un ciclo (sin `.json` en el extends): no se cuelga, y los paths son del que los
            # declara, sin baseUrl: relativos a su carpeta.
            "apps/cyc/tsconfig.json": json.dumps({"extends": "./tsconfig.cycle"}),
            "apps/cyc/tsconfig.cycle.json": json.dumps(
                {"extends": "./tsconfig.json", "compilerOptions": {"paths": {"~/*": ["src/*"]}}}
            ),
            "apps/cyc/src/a.ts": "import { b } from '~/lib/b';\n",
            "apps/cyc/src/lib/b.ts": "export const b = 1;\n",
        },
    )
    assert _edges(root) == {
        ("apps/web/src", "libs/shared"),
        ("apps/cyc/src", "apps/cyc/src/lib"),
    }


def test_un_tsconfig_sin_paths_hereda_los_del_padre_mas_cercano(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {
            "tsconfig.json": json.dumps(
                {"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}}
            ),
            "src/feature/tsconfig.json": json.dumps({"compilerOptions": {"strict": True}}),
            "src/feature/a.ts": "import { b } from '@/core/b';\n",
            "src/core/b.ts": "export const b = 1;\n",
        },
    )
    assert _edges(root) == {("src/feature", "src/core")}


def test_un_import_js_que_no_existe_prueba_ts(tmp_path: Path) -> None:
    """M4: `./x.js`, `.mjs` o `.cjs` que no existen prueban `.ts`, `.tsx`, `.mts` y `.cts`."""
    files = ["src/a.ts", "src/lib/b.ts", "src/lib/c.mts", "src/lib/d.cts", "src/lib/e.tsx"]
    index = graph.Index.build(tmp_path, files)
    text = (
        "import { b } from './lib/b.js';\nimport { c } from './lib/c.mjs';\n"
        "const d = require('./lib/d.cjs');\nimport E from './lib/e.js';\n"
    )
    resolved, external = graph.js_imports("src/a.ts", text, index)
    assert resolved == {"src/lib/b.ts", "src/lib/c.mts", "src/lib/d.cts", "src/lib/e.tsx"}
    assert external == set()


def test_workspace_cuyo_main_no_existe_cae_a_types_y_a_src_index(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {
            "package.json": json.dumps({"name": "acme", "workspaces": ["packages/*"]}),
            "packages/shared/package.json": json.dumps(
                {"name": "@acme/shared", "main": "dist/index.js", "types": "dist/index.d.ts"}
            ),
            "packages/shared/src/index.ts": "export const price = 1;\n",
            "packages/types/package.json": json.dumps(
                {"name": "@acme/types", "exports": "./dist/index.js", "typings": "lib/index.d.ts"}
            ),
            "packages/types/lib/index.d.ts": "export type Id = string;\n",
            "packages/app/src/main.ts": (
                "import { price } from '@acme/shared';\nimport type { Id } from '@acme/types';\n"
            ),
        },
    )
    assert _edges(root) == {
        ("packages/app/src", "packages/shared/src"),
        ("packages/app/src", "packages/types/lib"),
    }


def test_java_wildcard_static_mismo_paquete_y_calificado(tmp_path: Path) -> None:
    base = "src/main/java/com/example/library"
    root = _repo(
        tmp_path,
        {
            f"{base}/LibraryApplication.java": "package com.example.library;\nimport org.springframework.boot.SpringApplication;\n",
            f"{base}/loans/LoanService.java": (
                "package com.example.library.loans;\n"
                "import com.example.library.books.*;\n"
                "import static com.example.library.common.Dates.today;\n"
                "import com.example.library.members.Member;\n"
                "// import com.example.library.legacy.Old;\n"
                "class LoanService { com.example.library.notifications.Notifier n; Loan l; }\n"
            ),
            f"{base}/loans/Loan.java": "package com.example.library.loans;\n",
            f"{base}/members/Member.java": "package com.example.library.members;\nimport com.example.library.loans.Loan;\n",
            f"{base}/books/Book.java": "package com.example.library.books;\n",
            f"{base}/common/Dates.java": "package com.example.library.common;\n",
            f"{base}/notifications/Notifier.java": "package com.example.library.notifications;\n",
            "src/test/java/com/example/library/loans/LoanServiceTest.java": "import com.example.library.loans.LoanService;\n",
        },
    )
    assert _edges(root) == {
        (f"{base}/loans", f"{base}/books"),
        (f"{base}/loans", f"{base}/common"),
        (f"{base}/loans", f"{base}/members"),
        (f"{base}/members", f"{base}/loans"),
    }


class _NoScan(set):
    """Un conjunto que se puede consultar pero no recorrer."""

    def __iter__(self):  # type: ignore[override]
        raise AssertionError("index.files was scanned")


def test_el_wildcard_de_java_usa_el_indice_por_carpeta(tmp_path: Path) -> None:
    """M6: un `import x.*` no ordena todos los archivos del proyecto en cada import."""
    base = "src/main/java/com/example"
    paths = [f"{base}/books/Aaa.md", f"{base}/books/Book.java", f"{base}/loans/Loan.java"]
    index = graph.Index.build(tmp_path, paths)
    index.files = _NoScan(index.files)
    text = "import com.example.books.*;\n"
    resolved, _ = graph.java_imports(f"{base}/loans/Loan.java", text, index)
    assert resolved == {f"{base}/books/Book.java"}  # el primer .java de la carpeta


def test_strip_comments_respeta_los_strings() -> None:
    text = "const url = 'http://example.com'; // trailing\n/* block\n */ const x = `a // b`;\n"
    clean = graph.strip_comments(text)
    assert "http://example.com" in clean and "a // b" in clean
    assert "trailing" not in clean and "block" not in clean
    assert clean.count("\n") == text.count("\n")


def test_mermaid_y_escritura_idempotente(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a/x.py": "import b.y\n", "b/y.py": "", "b/__init__.py": ""})
    _, wrote = graph.write(root)
    assert wrote is True
    _, wrote = graph.write(root)
    assert wrote is False
    text = (root / ".exo" / "discovery" / graph.MERMAID).read_text(encoding="utf-8")
    assert text.startswith("graph LR\n") and '["a"]' in text and "-->" in text
