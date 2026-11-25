"""`fitness-assessment.json`: leerlo, escribirlo y migrarlo de la 1.0 (D-52).

Módulo liviano a propósito: `exo sync` y `exo update` lo usan para migrar los
assessments sin cargar el registro, el validador ni speclint (F8R1-16). La lógica
de clasificar y registrar vive en `changes`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exo.core import fsutil
from exo.sdd import fitness

# 2 desde D-52 (tres tiers). El 1 es de la 1.0: puede traer un tier 4 (ver `migrate`).
SCHEMA = 2


def stamp(now: datetime | None) -> str:
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def read(path: Path) -> dict[str, Any] | None:
    """El assessment como dict, o None si falta o no se puede leer."""
    try:
        data = json.loads(fsutil.read_bytes(Path(path)).decode("utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def dump(data: dict[str, Any]) -> bytes:
    """Los bytes con los que el motor escribe un assessment."""
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def migrate(data: Any, *, now: datetime | None = None) -> dict[str, Any] | None:
    """Lleva un assessment del esquema 1 (la 1.0, cuatro tiers) al actual.

    D-52: un Tier 4 pasa a 3 y registra `migrated_from: 4`; un Tier 3 adopta las
    reglas nuevas (`judgment-day` siempre). Los dos suman una entrada `migrated` a la
    historia, sin reescribir las anteriores. Un Tier 1 o 2 solo cambia de esquema.
    Devuelve None si no hay nada que migrar: ya es del esquema actual, o no se puede
    leer (eso lo informa `exo check`, no se adivina).
    """
    if not isinstance(data, dict):
        return None
    schema = data.get("schema", 1)
    tier = data.get("tier")
    if isinstance(schema, bool) or schema != 1:
        return None
    if isinstance(tier, bool) or not isinstance(tier, int) or not 1 <= tier <= 4:
        return None
    out = {**data, "schema": SCHEMA}
    if tier >= 3:
        new = fitness.normalize_tier(tier)
        out.update(tier=new, ceremony=fitness.CEREMONIES[new], judgment_day=True)
        if tier != new:
            out["migrated_from"] = tier
        history = data.get("history")
        entry = {"tier": new, "rule": data.get("rule"), "at": stamp(now), "change": "migrated"}
        entry["from"] = tier
        out["history"] = [*(history if isinstance(history, list) else []), entry]
    return out
