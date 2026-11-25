"""Gates como texto publicable: uno por gate, con su marcador (D-30, ADR-0014).

Cada gate vive en `<change-root>/gates/<gate>.md`; `contract_check` sale del Gate
summary de `verify-record.md`. `publish` arma un texto por gate y:

- si el proyecto configuró `review.publish_command`, lo corre una vez por gate,
  con las variables `GATE`, `GATE_MARKER`, `GATE_BODY` (la ruta a un archivo con
  el texto) y `CHANGE`, con el prefijo de variables del motor. El comando se
  encarga de crear o editar el único comentario del PR que tiene ese marcador;
- si no, o con `--dry-run`, lo imprime.

Publicar sale a un servicio remoto: por eso necesita el comando configurado
(invariante 11). El motor no conoce ninguna plataforma.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from exo import _meta
from exo.core import config
from exo.governance import approvals
from exo.sdd import observability, speclint

_TIMEOUT = 120


class GateError(ValueError):
    """Change inexistente o gates que no se pueden leer."""


@dataclass(frozen=True)
class GateText:
    name: str
    marker: str
    body: str
    path: str  # relativa al proyecto


@dataclass(frozen=True)
class Published:
    name: str
    status: str  # printed | sent | failed
    detail: str
    body: str
    path: str


def marker(name: str) -> str:
    return f"<!-- {_meta.BLOCK_PREFIX}-gate:{name} -->"


def collect(project: Path, change: str) -> list[GateText]:
    project = Path(project)
    try:
        found = observability.get_change(project, change)
    except observability.ObservabilityError as exc:
        raise GateError(str(exc)) from exc
    folder = project / found.path
    texts: list[GateText] = []
    verify = folder / "verify-record.md"
    summary = speclint.section_text(verify, "Gate summary") if verify.is_file() else None
    if summary and marker(speclint.CONTRACT_GATE) in summary:
        body = f"## Gate: {speclint.CONTRACT_GATE}\n\n{summary.strip()}\n"
        texts.append(
            GateText(
                speclint.CONTRACT_GATE,
                marker(speclint.CONTRACT_GATE),
                body,
                f"{found.path}/verify-record.md",
            )
        )
    gates_dir = folder / speclint.GATES_DIR
    for path in sorted(gates_dir.glob("*.md")) if gates_dir.is_dir() else []:
        try:
            body = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise GateError(f"{path}: {exc}") from exc
        name = speclint.gate_info(path).name
        rel = f"{found.path}/{speclint.GATES_DIR}/{path.name}"
        if name != path.stem:
            raise GateError(
                f"{rel}: its marker names the gate {name}, but the file is {path.stem}.md; fix "
                f"the marker (`{_meta.NAME} speclint {rel}`): one comment per gate needs one name"
            )
        if any(t.name == name for t in texts):
            raise GateError(f"{rel}: the gate {name} already comes from the verify record")
        texts.append(GateText(name, marker(name), body, rel))
    return sorted(texts, key=lambda t: t.name)


class CommandNotApproved(GateError):
    """El `publish_command` de la config no está aprobado en esta máquina para este proyecto,
    o cambió un archivo que corre (TM-20, TM-21)."""

    def __init__(self, decision: approvals.Decision) -> None:
        super().__init__(approvals.explain(decision))
        self.decision = decision
        self.command = decision.command


class CommandMismatch(GateError):
    """El texto que la persona aprobó no es el `publish_command` de la config (M-1)."""


def _check_approval(command: str | None, approve: str) -> None:
    if not command:
        raise GateError(
            f"--approve-command was given, but review.publish_command is not set in "
            f"{_meta.PROJECT_DIR}/{config.FILENAME}: there is nothing to approve or run. Without "
            f"it, `{_meta.NAME} gate publish` prints the texts; set it with `{_meta.NAME} init "
            '--publish-command "<command>"` or in the config'
        )
    if approve != command:
        raise CommandMismatch(
            "--approve-command does not match review.publish_command; nothing was approved "
            f"or run. The configured command is:\n  {command}"
        )


def publish(
    project: Path, change: str, *, dry_run: bool = False, approve: str | None = None
) -> list[Published]:
    """Publica o imprime los gates. El comando corre solo si está aprobado en esta máquina
    para este proyecto; si no, `CommandNotApproved` y no se ejecuta nada.

    `approve` es el texto que la persona aprobó (`--approve-command`, o el que vio en la
    terminal): se aprueba solo si coincide con el de la config, que se lee una sola vez acá,
    así lo que se compara es lo que corre (`CommandMismatch` si no)."""
    project = Path(project)
    texts = collect(project, change)
    command = config.load(project).config["review"]["publish_command"]
    if dry_run:
        return [Published(t.name, "printed", "", t.body, t.path) for t in texts]
    if approve is not None:
        _check_approval(command, approve)
    if not command:
        return [Published(t.name, "printed", "", t.body, t.path) for t in texts]
    if texts:
        if approve is not None:
            approvals.approve(project, command)
        else:
            decision = approvals.check(project, command)
            if not decision.approved:
                raise CommandNotApproved(decision)
    results: list[Published] = []
    for text in texts:
        handle, body_path = tempfile.mkstemp(prefix=f"{_meta.NAME}-gate-", suffix=".md")
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(text.body.encode("utf-8"))
            env = {
                **os.environ,
                f"{_meta.ENV_PREFIX}GATE": text.name,
                f"{_meta.ENV_PREFIX}GATE_MARKER": text.marker,
                f"{_meta.ENV_PREFIX}GATE_BODY": body_path,
                f"{_meta.ENV_PREFIX}CHANGE": change,
            }
            try:
                done = subprocess.run(
                    command, shell=True, cwd=project, env=env, capture_output=True, timeout=_TIMEOUT
                )
            except (OSError, subprocess.SubprocessError) as exc:
                results.append(Published(text.name, "failed", str(exc), text.body, text.path))
                continue
            if done.returncode == 0:
                results.append(Published(text.name, "sent", "", text.body, text.path))
            else:
                tail = (done.stderr or done.stdout or b"").decode("utf-8", errors="replace").strip()
                detail = f"exit {done.returncode}" + (f": {tail[-300:]}" if tail else "")
                results.append(Published(text.name, "failed", detail, text.body, text.path))
        finally:
            Path(body_path).unlink(missing_ok=True)
    return results
