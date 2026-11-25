"""`exo update`: lleva los archivos del proyecto a esta versión del motor (F8, criterio 7).

Muestra una vista previa por defecto y escribe solo con `apply`. Es `project.sync`
con tres diferencias:

- **Parcial:** lo que la persona editó queda como está (el conflicto se informa) y
  el resto se aplica. `force` lo pisa, con snapshot.
- **Huérfanas:** las skills y los subagentes que el contenido ya no trae se informan
  (un renombre conocido, como tal) y solo se borran con `prune`.
- **Config:** si se migró al leerla, se guarda migrada, en la misma transacción y con
  el mismo snapshot que el resto.

Un lock escrito por un motor más nuevo no se lleva hacia atrás sin `force`: lo frena
`project.sync`, igual que en `init`, `sync`, `add-agent` y `remove-agent`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from exo import _meta
from exo.core import lock
from exo.installer import engine, project

# Detalle de las acciones sobre archivos fuera del lock (la config del proyecto).
OUTSIDE_THE_LOCK = "outside the lock"


@dataclass
class UpdateResult:
    sync: project.SyncResult
    from_version: str | None  # la versión que escribió el lock antes de actualizar
    to_version: str

    @property
    def engine(self) -> engine.Result:
        return self.sync.engine

    def paths(self, action: str) -> list[str]:
        """Archivos con esa acción, sin repetir y sin la config (que va aparte)."""
        found = (
            a.path
            for a in self.engine.actions
            if a.action == action and a.detail != OUTSIDE_THE_LOCK
        )
        return list(dict.fromkeys(found))

    @property
    def up_to_date(self) -> bool:
        """Nada que escribir, ni huérfanas, ni conflictos, ni config por migrar."""
        result = self.engine
        pending_config = self.sync.config_migration is not None and not self.sync.config_written
        return not (result.changed or result.orphans or result.conflicts or pending_config)


def update(
    root: Path, *, apply: bool = False, force: bool = False, prune: bool = False
) -> UpdateResult:
    root = Path(root).resolve()
    previous = lock.read(root)
    if previous is None:
        raise project.ProjectError(
            f"the engine is not installed in {root}; run `{_meta.NAME} init`"
        )
    written_by = previous.engine_version or None
    # `project.sync` se niega a llevar hacia atrás un lock más nuevo sin `force`.
    result = project.sync(
        root,
        force=force,
        dry_run=not apply,
        prune=prune,
        partial=True,
        save_migrated=True,
    )
    return UpdateResult(result, written_by, _meta.VERSION)
