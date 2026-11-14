"""Contenido canónico sintético para los golden tests de los adaptadores.

Los goldens prueban cómo se instala el contenido, no qué dice. Con el contenido
real crecerían con cada skill nueva y cambiarían con cada edición. Este árbol es
chico y fijo, y se arma en código, como los proyectos de `_projects.py`.

Tiene lo que los adaptadores distinguen: dos packs, `sdd` (que trae las
plantillas de speclint) y `core`, una skill con `references/`, un subagente y
contratos compartidos con un esquema en una subcarpeta.
"""

from __future__ import annotations

import json
from pathlib import Path

RULES = """# Engine rules

- Cite evidence with `path:line`.
- Use `exo` commands with `--json`.
"""

HELLO = """---
name: hello-exo
description: >-
  Test skill. Use it when the user says hello to the engine.
metadata:
  exo-pack: core
  exo-execution: inline
---

# hello-exo

Reply with a greeting and read [the guide](references/guide.md).
"""

GUIDE = "# Guide\n\nKeep the greeting short.\n"

DEMO_PHASE = """---
name: demo-phase
description: >-
  Test phase skill. Use it when the user asks for the demo phase.
metadata:
  exo-pack: sdd
  exo-execution: subagent
  exo-subagent: demo-explorer
---

# demo-phase

Read `.exo/shared/demo-contract.md` and delegate to the explorer.
"""

EXPLORER = """---
name: demo-explorer
description: Test subagent that only reads.
tools: Read, Grep, Glob
---

Read only. Return a short summary.
"""

CONTRACT = "# Demo contract\n\nEvery phase returns an envelope.\n"
SCHEMA = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}


def _pack(name: str, requires: list[str]) -> str:
    manifest = {
        "name": name,
        "version": "0.1.0",
        "description": f"Synthetic {name} pack.",
        "requires": requires,
        "optional": [],
    }
    return json.dumps(manifest, indent=2) + "\n"


FILES = {
    "rules/AGENTS.base.md": RULES,
    "packs/core/pack.json": _pack("core", []),
    "packs/core/skills/hello-exo/SKILL.md": HELLO,
    "packs/core/skills/hello-exo/references/guide.md": GUIDE,
    "packs/sdd/pack.json": _pack("sdd", ["core"]),
    "packs/sdd/skills/demo-phase/SKILL.md": DEMO_PHASE,
    "packs/sdd/agents/demo-explorer.md": EXPLORER,
    "packs/sdd/shared/demo-contract.md": CONTRACT,
    "packs/sdd/shared/schemas/demo.schema.json": json.dumps(SCHEMA, indent=2) + "\n",
}


def build(root: Path) -> Path:
    for rel, text in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return root
