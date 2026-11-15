"""El host del repo, detectado desde el remoto (D-30, ADR-0014).

El motor no se integra con ninguna plataforma: el host solo sirve para que los
contratos y las notas muestren el ejemplo que corresponde. Se guarda en
`review.host` la primera vez y después manda lo que diga la config.
"""

from __future__ import annotations

from pathlib import Path

from exo.governance import git
from exo.memory.projects import normalize_remote


def from_remote(remote: str) -> str | None:
    """`github`, `azure-devops`, `gitlab` u `other`; None si no parece un remoto."""
    name = normalize_remote(remote)
    if name is None:
        return None
    host = name.split("/", 1)[0]
    if host == "github.com":
        return "github"
    if host == "dev.azure.com":
        return "azure-devops"
    if "gitlab" in host:
        return "gitlab"
    return "other"


def detect(project: Path) -> str | None:
    result = git.run(project, "remote", "get-url", "origin")
    return from_remote(result.out.strip()) if result.ok and result.out.strip() else None
