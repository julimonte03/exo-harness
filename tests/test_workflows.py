"""Los workflows de GitHub Actions del motor, sin inyección de expresiones (threat model, M-13).

Una expresión `${{ … }}` dentro de un `run:` se expande antes de que corra la shell: un
nombre de rama o un título de PR con `$(…)` se ejecutaría. Las expresiones van en `env:`, y
la shell las lee como variables. Tampoco hay `pull_request_target`, que corre con permisos
de escritura sobre código de un fork (TM-13).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOWS = sorted((Path(__file__).resolve().parents[1] / ".github" / "workflows").glob("*.yml"))
_RUN = re.compile(r"^(?P<indent>\s*)(?:-\s+)?run:\s*(?P<rest>.*)$")


def run_blocks(text: str) -> list[tuple[int, str]]:
    """`(línea, texto)` de cada comando de `run:`, inline o en bloque `|`/`>`."""
    lines = text.splitlines()
    found: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        match = _RUN.match(lines[i])
        if not match:
            i += 1
            continue
        rest = match.group("rest").strip()
        if rest and rest[0] not in "|>":
            found.append((i + 1, rest))
            i += 1
            continue
        base = len(match.group("indent"))
        start, i = i + 1, i + 1
        while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > base):
            i += 1
        found += [(n + 1, lines[n]) for n in range(start, i) if lines[n].strip()]
    return found


def test_el_lector_de_run_encuentra_inline_y_bloques() -> None:
    text = (
        "steps:\n"
        "  - run: echo ${{ github.head_ref }}\n"
        "  - name: x\n"
        "    run: |\n"
        "      echo uno\n"
        "      echo ${{ github.event.pull_request.title }}\n"
        "    env:\n"
        "      A: ${{ github.ref_name }}\n"
    )
    blocks = run_blocks(text)
    assert [n for n, _ in blocks] == [2, 5, 6]
    assert sum("${{" in line for _, line in blocks) == 2


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_sin_expresiones_dentro_de_run(workflow: Path) -> None:
    text = workflow.read_text(encoding="utf-8")
    bad = [f"{workflow.name}:{n}: {line.strip()}" for n, line in run_blocks(text) if "${{" in line]
    assert bad == [], "move the expression to env: and read it as a variable"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_sin_pull_request_target(workflow: Path) -> None:
    assert "pull_request_target" not in workflow.read_text(encoding="utf-8")


_USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)(?P<comment>\s+#\s*\S+)?\s*$")


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_actions_fijadas_por_sha_con_su_version(workflow: Path) -> None:
    """M-5 (TM-10): un tag o una rama se pueden mover; el SHA de un commit, no. Dependabot
    (`.github/dependabot.yml`) propone las actualizaciones como PRs."""
    bad = []
    for n, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1):
        match = _USES.match(line)
        if not match:
            continue
        ref = match.group("ref")
        if ref.startswith("./"):
            continue  # una action del mismo repo
        pinned = re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref)
        if not pinned or not match.group("comment"):
            bad.append(f"{workflow.name}:{n}: {line.strip()}")
    assert bad == [], "pin `uses:` to a full commit SHA with the version in a comment"


def test_dependabot_actualiza_las_actions() -> None:
    config = Path(__file__).resolve().parents[1] / ".github" / "dependabot.yml"
    text = config.read_text(encoding="utf-8")
    assert 'package-ecosystem: "github-actions"' in text


def test_hay_workflows() -> None:
    assert {p.name for p in WORKFLOWS} >= {"ci.yml", "release.yml"}
