"""AI Usage Record de un change (`<change-root>/ai-usage-record.json`, §7.7 del reporte).

El esquema vive en `sdd/schemas/` y se instala en `shared/schemas/`, dentro
de la carpeta del motor del proyecto, para que los agentes lo lean.

Adaptaciones al reporte (definición propia): `ticket_key` y `epic_key` en lugar
de `jira_key` (ADR-0012), sin `playbook` (el plan descartó los playbooks) y
`activation` con `requested|auto`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from exo.core import jsonschema

FILENAME = "ai-usage-record.json"
SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMA_FILE = SCHEMAS_DIR / "ai-usage-record.schema.json"
ATTRIBUTION_SCHEMA_VERSION = 1


@lru_cache(maxsize=1)
def _schema_text() -> str:
    return SCHEMA_FILE.read_text(encoding="utf-8")


def schema() -> dict[str, Any]:
    return json.loads(_schema_text())


def validate(data: Any) -> list[str]:
    return jsonschema.validate(data, schema())
