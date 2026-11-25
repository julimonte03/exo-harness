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


_ITEM = re.compile(r"^(?P<indent>\s*)-\s+\S")


def steps(text: str) -> list[tuple[int, str]]:
    """`(línea, texto)` de cada elemento `- ...` de una lista en bloque, con sus claves."""
    lines = text.splitlines()
    found: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        match = _ITEM.match(line)
        if not match:
            continue
        base = len(match.group("indent"))
        end = i + 1
        while end < len(lines) and (
            not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > base
        ):
            end += 1
        found.append((i + 1, "\n".join(lines[i:end])))
    return found


def jobs(text: str) -> dict[str, str]:
    """Nombre -> texto de cada job de `jobs:` (claves con dos espacios de sangría)."""
    body = text.split("\njobs:\n", 1)[1]
    found: dict[str, str] = {}
    name = None
    for line in body.splitlines():
        match = re.match(r"^  (?P<name>[\w-]+):\s*$", line)
        if match:
            name = match.group("name")
            found[name] = ""
        elif name and (not line.strip() or line.startswith("   ")):
            found[name] += line + "\n"
        elif line.strip() and not line.startswith(" "):
            name = None
    return found


def _uses(step: str, action: str) -> bool:
    return re.search(rf"^\s*(?:-\s+)?uses:\s*{re.escape(action)}@", step, re.M) is not None


def test_el_lector_de_steps_y_jobs() -> None:
    text = (
        "on: push\n"
        "jobs:\n"
        "  uno:\n"
        "    steps:\n"
        "      - uses: actions/checkout@abc # v4\n"
        "        with:\n"
        "          persist-credentials: false\n"
        "\n"
        "      - name: x\n"
        "        run: echo\n"
        "  dos:\n"
        "    needs: uno\n"
    )
    found = steps(text)
    assert [n for n, _ in found] == [5, 9]
    assert "persist-credentials: false" in found[0][1] and "run:" not in found[0][1]
    assert _uses(found[0][1], "actions/checkout") and not _uses(found[1][1], "actions/checkout")
    assert set(jobs(text)) == {"uno", "dos"} and "needs: uno" in jobs(text)["dos"]


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_checkout_sin_credenciales_persistidas(workflow: Path) -> None:
    """F8R2-16: con las credenciales por defecto, el token queda en `.git/config` para todo
    lo que corre después en el job. Ningún job empuja con git; el release usa `gh` con
    `GH_TOKEN`."""
    found = [s for s in steps(workflow.read_text(encoding="utf-8")) if _uses(s[1], "actions/checkout")]
    assert found, "no checkout"
    bad = [f"{workflow.name}:{n}" for n, step in found if "persist-credentials: false" not in step]
    assert bad == [], "add `with: persist-credentials: false` to actions/checkout"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_upload_artifact_falla_sin_archivos(workflow: Path) -> None:
    """F8R2-15: un artefacto vacío no pasa en silencio."""
    text = workflow.read_text(encoding="utf-8")
    found = [s for s in steps(text) if _uses(s[1], "actions/upload-artifact")]
    bad = [f"{workflow.name}:{n}" for n, step in found if "if-no-files-found: error" not in step]
    assert bad == [], "add `if-no-files-found: error` to actions/upload-artifact"


def _workflow(name: str) -> str:
    return next(p for p in WORKFLOWS if p.name == name).read_text(encoding="utf-8")


def test_el_build_de_la_ci_revisa_el_paquete_con_twine() -> None:
    """F8R2-15: lo mismo que el release, así un README o metadatos rotos fallan en el PR."""
    build = jobs(_workflow("ci.yml"))["build"]
    assert "twine check --strict dist/*" in build
    assert re.search(r"pip install[^\n]*\btwine\b", build)


def test_el_release_corre_los_tests_antes_del_build() -> None:
    """F8R2-11: un tag no publica un build cuya suite falla."""
    found = jobs(_workflow("release.yml"))
    assert re.search(r"^\s*run:\s*pytest\b", found["tests"], re.M)
    assert re.search(r"^    needs:\s*\[?\s*tests\b", found["build"], re.M)


def test_dependabot_actualiza_las_actions() -> None:
    config = Path(__file__).resolve().parents[1] / ".github" / "dependabot.yml"
    text = config.read_text(encoding="utf-8")
    assert 'package-ecosystem: "github-actions"' in text


def test_hay_workflows() -> None:
    assert {p.name for p in WORKFLOWS} >= {"ci.yml", "release.yml"}
