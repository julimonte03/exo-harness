"""Verdad conocida de los fixtures de ingeniería inversa (F6, ADR-0015).

Vive afuera del fixture (`tests/fixtures/ground-truth/<fixture>.md`) para que el
extractor no lea la respuesta. Cada archivo tiene prosa y un único bloque ```json
con este esquema (todas las rutas relativas a la raíz del fixture, con `/`):

- `fixture`: el nombre de la carpeta en `tests/fixtures/repos/`.
- `languages`: lenguajes que tienen que aparecer (nombres del inventario:
  `python`, `javascript`, `typescript`, `java`, ...).
- `frameworks`: frameworks y librerías que tienen que detectarse (subconjunto).
- `entrypoints`: rutas exactas de los puntos de entrada (conjunto exacto).
- `test_files`: rutas exactas de los archivos de test (conjunto exacto).
- `ci`, `migrations`, `api_contracts`, `infrastructure`: rutas exactas.
- `sensitive_files`: archivos que solo se listan por nombre (puede ser `[]`).
- `modules`: carpetas de código de producción (sin tests), conjunto exacto.
- `edges`: pares `[origen, destino]` de carpetas de producción, conjunto exacto.
- `capabilities`: `[{"name", "key_files": [...], "rules": [...]}]`; el match con
  lo que recupera la adopción es por archivos clave, no por nombre.
- `hard_cases`: lista de los casos difíciles que el fixture tiene a propósito.

**Módulo:** la carpeta (relativa, con `/`) que contiene archivos de código de
producción. **Arista:** un import de un archivo de la carpeta A que resuelve a un
archivo de la carpeta B, con A distinta de B. Los imports a paquetes externos no
son aristas (son dependencias), y los tests no son módulos ni originan aristas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent / "fixtures" / "ground-truth"
_BLOCK = re.compile(r"^```json\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)
KEYS = {
    "fixture": str,
    "languages": list,
    "frameworks": list,
    "entrypoints": list,
    "test_files": list,
    "ci": list,
    "migrations": list,
    "api_contracts": list,
    "infrastructure": list,
    "sensitive_files": list,
    "modules": list,
    "edges": list,
    "capabilities": list,
    "hard_cases": list,
}


def load(fixture: str) -> dict[str, Any]:
    text = (ROOT / f"{fixture}.md").read_text(encoding="utf-8")
    blocks = _BLOCK.findall(text)
    if len(blocks) != 1:
        raise ValueError(f"{fixture}.md needs exactly one ```json block (has {len(blocks)})")
    data = json.loads(blocks[0])
    problems = [k for k, kind in KEYS.items() if not isinstance(data.get(k), kind)]
    extra = sorted(set(data) - set(KEYS))
    if problems or extra:
        raise ValueError(f"{fixture}.md: bad keys {problems}, unknown keys {extra}")
    return data


def fixtures() -> list[str]:
    return sorted(p.stem for p in ROOT.glob("*.md") if p.name != "README.md")
