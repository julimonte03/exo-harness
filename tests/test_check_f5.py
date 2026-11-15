"""`exo check` completo (F5): config, veredicto, gates por tier, judgment-day, diff y `--fast`."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from exo.cli import main
from exo.core import config
from exo.sdd import changes, check, fitness, speclint
from test_speclint import PROPOSAL, SPEC, TEST_SPEC, VERIFY

LOW = {d: 0 for d in fitness.DIMENSIONS}
MEDIUM = {**LOW, "blast_radius": 2}  # Tier 2
CRITICAL = {**LOW, "reversibility": 3}  # Tier 4
AWS = "AKIA" + "Q" * 16


def gate(name: str, verdict: str = "APPROVED", approval: str = "no") -> str:
    return f"""# Gate: {name}

<!-- exo-gate:{name} -->

## Verdict

{verdict}: no blocking finding.

## Findings

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| Low | src/app.py:3 | Name could be clearer | naming |

## Approval

Requires tech_lead approval: {approval}

Source: skill harness-review
"""


def _change(project: Path, slug: str, evidence: dict, files: dict[str, str]) -> Path:
    created = changes.new_change(project, slug)
    changes.record_assessment(project, slug, evidence)
    folder = project / created.path
    for rel, text in files.items():
        (folder / rel).parent.mkdir(parents=True, exist_ok=True)
        (folder / rel).write_text(text, encoding="utf-8")
    return folder


COMPLETE = {
    "proposal.md": PROPOSAL,
    "spec.md": SPEC,
    "test-spec.md": TEST_SPEC,
    "verify-record.md": VERIFY,
    "gates/code_review.md": gate("code_review"),
}


def _errors(result: check.CheckResult) -> list[str]:
    found = [f.message for c in result.changes for f in c.findings if f.severity == "error"]
    found += [f.message for f in result.config + result.diff if f.severity == "error"]
    return found


def _warnings(result: check.CheckResult) -> list[str]:
    return [f.message for c in result.changes for f in c.findings if f.severity == "warning"]


# -- plantilla y speclint del gate ---------------------------------------------------------


def test_el_gate_pasa_speclint_y_la_plantilla_vacia_no(tmp_path: Path) -> None:
    path = tmp_path / "gates" / "code_review.md"
    path.parent.mkdir()
    path.write_text(gate("code_review"), encoding="utf-8")
    assert speclint.lint_path(path).ok
    path.write_text(speclint.template_text("gate"), encoding="utf-8")
    assert not speclint.lint_path(path).ok


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("<!-- exo-gate:code_review -->", "<!-- exo-gate:security_review -->", "marker"),
        ("APPROVED: no blocking", "MAYBE: no blocking", "APPROVED or ESCALATED"),
        ("Requires tech_lead approval: no", "Needs approval", "Requires tech_lead approval"),
        ("Source: skill harness-review", "", "Source:"),
    ],
)
def test_reglas_del_gate(tmp_path: Path, old: str, new: str, fragment: str) -> None:
    path = tmp_path / "gates" / "code_review.md"
    path.parent.mkdir()
    path.write_text(gate("code_review").replace(old, new), encoding="utf-8")
    messages = [i.message for f in speclint.lint_path(path).files for i in f.errors]
    assert any(fragment in m for m in messages), messages


def test_info_del_gate_y_del_contract_check(tmp_path: Path) -> None:
    path = tmp_path / "gates" / "security_review.md"
    path.parent.mkdir()
    path.write_text(gate("security_review", "ESCALATED", "yes"), encoding="utf-8")
    info = speclint.gate_info(path)
    assert (info.name, info.verdict, info.needs_approval) == ("security_review", "ESCALATED", True)
    verify = tmp_path / "verify-record.md"
    verify.write_text(VERIFY, encoding="utf-8")
    contract = speclint.contract_gate(verify)
    assert (contract.name, contract.verdict, contract.needs_approval) == (
        "contract_check",
        "APPROVED",
        False,
    )


# -- exo check (criterio 3 de F5) ----------------------------------------------------------


def test_criterio_3_tier_2_completo_pasa(tmp_path: Path) -> None:
    _change(tmp_path, "medio", MEDIUM, COMPLETE)
    result = check.check(tmp_path)
    assert result.ok, _errors(result)


@pytest.mark.parametrize(
    ("missing", "fragment"),
    [
        ("test-spec.md", "Tier 2 requires test-spec.md"),
        ("gates/code_review.md", "Tier 2 requires the gate code_review"),
    ],
)
def test_criterio_3_tier_2_incompleto_falla(tmp_path: Path, missing: str, fragment: str) -> None:
    files = {k: v for k, v in COMPLETE.items() if k != missing}
    _change(tmp_path, "medio", MEDIUM, files)
    result = check.check(tmp_path)
    assert not result.ok
    assert any(fragment in m for m in _errors(result)), _errors(result)


def test_criterio_3_sin_registro_falla(tmp_path: Path) -> None:
    folder = _change(tmp_path, "medio", MEDIUM, COMPLETE)
    (folder / "ai-usage-record.json").unlink()
    assert any("ai-usage-record.json" in m for m in _errors(check.check(tmp_path)))


@pytest.mark.parametrize("verdict", ["blocked: the build fails", "needs-rework: S-2 fails"])
def test_criterio_3_veredicto_no_listo_falla(tmp_path: Path, verdict: str) -> None:
    files = {
        **COMPLETE,
        "verify-record.md": VERIFY.replace("## Verdict\nready", f"## Verdict\n{verdict}"),
    }
    _change(tmp_path, "medio", MEDIUM, files)
    assert any("the verify says" in m for m in _errors(check.check(tmp_path)))


def test_gate_escalado_pide_tech_lead(tmp_path: Path) -> None:
    files = {**COMPLETE, "gates/code_review.md": gate("code_review", "ESCALATED", "yes")}
    _change(tmp_path, "medio", MEDIUM, files)
    result = check.check(tmp_path)
    assert result.ok
    assert any("tech_lead" in w for w in _warnings(result))


def test_los_gates_se_piden_recien_despues_del_verify(tmp_path: Path) -> None:
    files = {
        k: v for k, v in COMPLETE.items() if k not in ("verify-record.md", "gates/code_review.md")
    }
    _change(tmp_path, "medio", MEDIUM, files)
    assert check.check(tmp_path).ok


def test_tier_4_exige_judgment_day(tmp_path: Path) -> None:
    tier4 = {
        **COMPLETE,
        "design.md": "x",
        "tasks.md": "- [x] 1. a\n",
        **{f"gates/{g}.md": gate(g) for g in config.DEFAULT_GATES["4"] if g != "contract_check"},
    }
    tier4.pop("design.md")
    _change(tmp_path, "grande", CRITICAL, tier4)
    messages = _errors(check.check(tmp_path))
    assert any("judgment-day" in m for m in messages)
    changes.update_record(
        tmp_path, "grande", add=[("judges_invoked", {"name": "judgment-day", "result": "approved"})]
    )
    assert not any("judgment-day" in m for m in _errors(check.check(tmp_path)))
    # Revisión de cierre: cuenta la última entrada; un judgment-day posterior escalado manda.
    later = {"name": "judgment-day", "result": "escalated: JSEC-3 (High) open after 3 rounds"}
    changes.update_record(tmp_path, "grande", add=[("judges_invoked", later)])
    assert any("judgment-day" in m for m in _errors(check.check(tmp_path)))
    from exo.sdd import observability

    approved = {"name": "judgment-day", "result": "approved"}
    assert observability.judgment_approved([approved]) is True
    assert observability.judgment_approved([approved, later]) is False
    assert observability.judgment_approved([later, approved]) is True


def test_los_gates_configurados_mandan(tmp_path: Path) -> None:
    cfg = config.defaults()
    cfg["governance"]["gates"]["2"] = ["contract_check", "my_gate"]
    config.save(tmp_path, cfg)
    _change(tmp_path, "medio", MEDIUM, COMPLETE)
    assert any("my_gate" in m for m in _errors(check.check(tmp_path)))


def test_config_invalida_es_error(tmp_path: Path) -> None:
    folder = tmp_path / ".exo"
    folder.mkdir()
    (folder / "config.json").write_text(
        json.dumps({"schema": 3, "review": {"host": "nada"}}), encoding="utf-8"
    )
    result = check.check(tmp_path)
    assert not result.ok
    assert any("review.host" in f.message for f in result.config)


def test_fast_no_pide_artefactos_ni_gates(tmp_path: Path) -> None:
    _change(tmp_path, "medio", MEDIUM, {"proposal.md": PROPOSAL})
    assert not check.check(tmp_path).ok
    assert check.check(tmp_path, fast=True).ok


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
def test_el_diff_contra_la_base_se_escanea(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feat/x")
    (tmp_path / "app.py").write_text(f"KEY = '{AWS}'\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "feat: app")
    (tmp_path / "nuevo.py").write_text(f"OTHER = '{AWS}'\n", encoding="utf-8")  # sin trackear
    result = check.check(tmp_path, base="main")
    messages = [f.message for f in result.diff if f.severity == "error"]
    assert any(m.startswith("app.py:1:") and "aws-access-key" in m for m in messages), messages
    assert any(m.startswith("nuevo.py:1:") for m in messages), messages
    assert not result.ok


def test_cli_fast_y_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _change(tmp_path, "medio", MEDIUM, {"proposal.md": PROPOSAL})
    assert main(["check", "--project", str(tmp_path), "--fast"]) == 0
    capsys.readouterr()
    assert main(["check", "--project", str(tmp_path), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["config"] == [] and payload["diff"] == []


@pytest.mark.skipif(shutil.which("git") is None, reason="requiere git")
def test_criterio_5_el_paso_de_ci_da_verde_y_rojo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """El paso que ponen los ejemplos de CI (`exo check --base main`) en un repo temporal."""
    contract = Path(__file__).resolve().parents[1] / "content/packs/core/shared/ci-and-review.md"
    assert "exo check --base origin/<target branch>" in contract.read_text(encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "chore: base")

    _git(tmp_path, "checkout", "-q", "-b", "feat/completo")
    _change(tmp_path, "completo", MEDIUM, COMPLETE)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "feat: cambio completo")
    assert main(["check", "--base", "main", "--project", str(tmp_path)]) == 0

    _git(tmp_path, "checkout", "-q", "main")
    _git(tmp_path, "checkout", "-q", "-b", "feat/incompleto")
    files = {k: v for k, v in COMPLETE.items() if k != "gates/code_review.md"}
    _change(tmp_path, "incompleto", MEDIUM, files)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "feat: cambio incompleto")
    capsys.readouterr()
    assert main(["check", "--base", "main", "--project", str(tmp_path)]) == 1
    out = capsys.readouterr()
    assert "incompleto" in out.out + out.err
    assert "completo" not in (out.out + out.err).replace("incompleto", "")
