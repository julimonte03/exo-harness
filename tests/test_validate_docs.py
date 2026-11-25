"""validate --docs (F8, D-48): conteos con marcadores y subcomandos citados en los docs.

Los conteos salen de lo que `exo validate` ya calcula sobre el contenido; los
subcomandos, de la tabla del CLI (`commands.MODULES`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from exo import _meta, commands
from exo.adapters import ADAPTERS
from exo.cli import main
from exo.validate import doc_counts, doc_files, validate, validate_docs

NAME = _meta.NAME
COMMANDS = {name for names in commands.MODULES.values() for name in names}
COUNTS = {"packs": 2, "skills": 3, "subagents": 1, "shared": 4, "agents": 2, "skills:core": 1}


def _marker(key: str, value: str) -> str:
    return f"<!-- {_meta.BLOCK_PREFIX}-count:{key} -->{value}<!-- /{_meta.BLOCK_PREFIX}-count -->"


def _doc(tmp_path: Path, text: str, name: str = "README.md") -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _errors(tmp_path: Path, text: str) -> list[str]:
    report = validate_docs([_doc(tmp_path, text)], COUNTS, COMMANDS)
    return [f"{f.line}: {f.message}" for f in report.errors]


# -- conteos ---------------------------------------------------------------------------------


def test_conteos_que_coinciden_no_dan_error(tmp_path: Path) -> None:
    text = (
        f"# Title\n\nIt ships {_marker('skills', '3')} skills in {_marker('packs', '2')} packs,\n"
        f"with {_marker('subagents', ' 1 ')} subagent and {_marker('skills:core', '1')} in core.\n"
    )
    report = validate_docs([_doc(tmp_path, text)], COUNTS, COMMANDS)
    assert report.errors == []
    assert report.markers == 4
    assert report.files == [tmp_path / "README.md"]


def test_un_numero_distinto_es_error_con_archivo_y_linea(tmp_path: Path) -> None:
    path = _doc(tmp_path, f"# Title\n\nIt ships {_marker('skills', '106')} skills.\n")
    report = validate_docs([path], COUNTS, COMMANDS)
    assert [(f.path, f.line) for f in report.errors] == [(path.as_posix(), 3)]
    message = report.errors[0].message
    assert "skills" in message and "106" in message and "3" in message


def test_una_clave_desconocida_es_error(tmp_path: Path) -> None:
    errors = _errors(tmp_path, f"{_marker('skils', '3')}\n{_marker('skills:nope', '0')}\n")
    assert len(errors) == 2
    assert errors[0].startswith("1: ") and "skils" in errors[0] and "packs" in errors[0]
    assert errors[1].startswith("2: ") and "skills:nope" in errors[1]


@pytest.mark.parametrize("value", ["many", "²", "-3", "3.0", ""])
def test_un_valor_que_no_es_un_numero_es_error(tmp_path: Path, value: str) -> None:
    errors = _errors(tmp_path, f"{_marker('skills', value)}\n")
    assert len(errors) == 1 and repr(value) in errors[0] and "whole number" in errors[0]


def test_un_marcador_sin_cerrar_en_la_linea_es_error(tmp_path: Path) -> None:
    errors = _errors(tmp_path, f"<!-- {_meta.BLOCK_PREFIX}-count:skills -->3 skills\n")
    assert len(errors) == 1 and "not closed" in errors[0]


def test_un_marcador_sin_cerrar_no_toma_el_cierre_del_siguiente(tmp_path: Path) -> None:
    opening = f"<!-- {_meta.BLOCK_PREFIX}-count:skills -->"
    errors = _errors(tmp_path, f"{opening}3 skills in {_marker('packs', '2')} packs\n")
    assert len(errors) == 1 and "not closed" in errors[0] and "skills" in errors[0]


def test_marcadores_dentro_de_codigo_no_cuentan(tmp_path: Path) -> None:
    text = (
        f"Write `{_marker('skills', '106')}` to cite a count.\n\n"
        f"```markdown\n{_marker('skills', '999')}\n```\n\n"
        f"~~~\n{_marker('nope', 'x')}\n~~~\n"
    )
    report = validate_docs([_doc(tmp_path, text)], COUNTS, COMMANDS)
    assert report.errors == []
    assert report.markers == 0


def test_varios_marcadores_en_una_linea(tmp_path: Path) -> None:
    errors = _errors(tmp_path, f"{_marker('packs', '2')} and {_marker('skills', '4')}\n")
    assert len(errors) == 1 and "skills" in errors[0]


def test_las_claves_salen_de_validate_y_de_los_adaptadores(synthetic_content: Path) -> None:
    counts = doc_counts(validate(synthetic_content))
    assert counts == {
        "packs": 2,
        "skills": 2,
        "subagents": 1,
        "shared": 2,
        "agents": len(ADAPTERS),
        "skills:core": 1,
        "skills:sdd": 1,
    }


def test_un_pack_sin_skills_cuenta_cero(synthetic_content: Path) -> None:
    pack = synthetic_content / "packs" / "vacio"
    pack.mkdir()
    (pack / "pack.json").write_text(
        json.dumps(
            {"name": "vacio", "version": "0.1.0", "description": "x", "requires": [], "optional": []}
        ),
        encoding="utf-8",
    )
    counts = doc_counts(validate(synthetic_content))
    assert counts["skills:vacio"] == 0
    assert counts["packs"] == 3


# -- subcomandos citados ---------------------------------------------------------------------


def test_subcomandos_que_existen_no_dan_error(tmp_path: Path) -> None:
    text = (
        "```bash\n"
        f"{NAME} init --yes\n"
        f"$ {NAME} update --apply\n"
        f"uvx --from git+https://example.invalid/{_meta.DIST_NAME} {NAME} init\n"
        f"python -m {NAME} validate && {NAME} --version\n"
        "```\n\n"
        f"Then run `{NAME} sync` or `{NAME} persona set dev`.\n"
    )
    report = validate_docs([_doc(tmp_path, text)], COUNTS, COMMANDS)
    assert report.errors == []
    assert report.commands == 6


def test_un_subcomando_que_no_existe_es_error(tmp_path: Path) -> None:
    text = f"# Title\n\n```sh\n{NAME} init\n{NAME} upgrade --apply\n```\n\nOr `{NAME} instal`.\n"
    errors = _errors(tmp_path, text)
    assert len(errors) == 2
    assert errors[0].startswith("5: ") and "upgrade" in errors[0]
    assert errors[1].startswith("8: ") and "instal" in errors[1]


@pytest.mark.parametrize(
    "line",
    [
        f"  {NAME} upgrade",
        f"$ {NAME} upgrade",
        f"PS C:\\code> {NAME} upgrade",
        f"cd app && {NAME} upgrade",
        f"echo hi; {NAME} upgrade",
        f"{NAME} --version | {NAME} upgrade",
        f"x=$({NAME} upgrade)",
        f"python -m {NAME} upgrade",
        f"uvx --from {_meta.DIST_NAME} {NAME} upgrade",
        f"- run: {NAME} upgrade",
        f"  script: {NAME} upgrade",
        f"  - {NAME} upgrade",
        f"the lock is old; run `{NAME} upgrade` first",
    ],
)
def test_un_subcomando_en_posicion_de_comando_se_revisa(tmp_path: Path, line: str) -> None:
    errors = _errors(tmp_path, f"```\n{line}\n```\n")
    assert len(errors) == 1 and "'upgrade'" in errors[0], errors


@pytest.mark.parametrize(
    "line",
    [
        f"the lock uses a newer schema (a newer {NAME} wrote it); upgrade {NAME} and retry",
        f"{NAME} commit-msg: blocked",
        f"Exo is a {NAME} engine",
    ],
)
def test_un_mensaje_que_nombra_al_motor_no_es_un_comando(tmp_path: Path, line: str) -> None:
    report = validate_docs([_doc(tmp_path, f"```text\n{line}\n```\n")], COUNTS, COMMANDS)
    assert report.errors == []
    assert report.commands == 0


def test_lo_que_no_es_un_comando_no_se_revisa(tmp_path: Path) -> None:
    text = (
        f"The {NAME} engine is great, and {NAME} init in prose is not checked.\n\n"
        "```text\n"
        f"{_meta.PROJECT_DIR}/config is here\n"
        f"pip install {_meta.DIST_NAME} now\n"
        f"/{NAME}-adopt quick please\n"
        f"echo hi  # {NAME} is not a command here\n"
        f"{NAME} <command> --help\n"
        "```\n"
    )
    report = validate_docs([_doc(tmp_path, text)], COUNTS, COMMANDS)
    assert report.errors == []
    assert report.commands == 0


# -- archivos ----------------------------------------------------------------------------------


def test_una_carpeta_da_sus_markdown_sin_recursion(tmp_path: Path) -> None:
    _doc(tmp_path, "a\n", "b.md")
    _doc(tmp_path, "a\n", "a.md")
    _doc(tmp_path, "a\n", "notes.txt")
    _doc(tmp_path, "a\n", "sub/c.md")
    assert doc_files(tmp_path) == [tmp_path / "a.md", tmp_path / "b.md"]
    assert doc_files(tmp_path / "b.md") == [tmp_path / "b.md"]


# -- CLI ---------------------------------------------------------------------------------------


def test_cli_validate_docs(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docs = tmp_path / "docs"
    _doc(docs, f"It has {_marker('skills', '2')} skills. Run `{NAME} init`.\n")
    assert main(["validate", "--docs", str(docs)]) == 0
    out = capsys.readouterr().out
    assert "docs: 1 file, 1 count marker, 1 command: all valid" in out

    _doc(docs, f"Line one.\nIt has {_marker('skills', '5')} skills.\n", "guide.md")
    assert main(["validate", "--docs", str(docs)]) == 1
    out = capsys.readouterr().out
    assert f"{(docs / 'guide.md').as_posix()}:2: error:" in out

    assert main(["validate", "--docs", str(docs), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["errors"] == []
    assert payload["docs"]["errors"][0]["line"] == 2
    assert len(payload["docs"]["files"]) == 2


def test_cli_validate_docs_se_puede_repetir_y_acepta_archivos(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = _doc(tmp_path / "a", f"{_marker('packs', '2')}\n")
    other = _doc(tmp_path / "b", f"{_marker('agents', str(len(ADAPTERS)))}\n", "guide.md")
    assert main(["validate", "--docs", str(good), "--docs", str(other.parent)]) == 0
    assert "docs: 2 files, 2 count markers" in capsys.readouterr().out


@pytest.mark.parametrize("make", ["missing", "empty"])
def test_cli_validate_docs_sin_markdown_es_error(
    tmp_path: Path, synthetic_content: Path, capsys: pytest.CaptureFixture[str], make: str
) -> None:
    target = tmp_path / "docs"
    if make == "empty":
        target.mkdir()
    assert main(["validate", "--docs", str(target)]) == 1
    err = capsys.readouterr().err
    assert str(target) in err
    assert ("does not exist" if make == "missing" else "no Markdown files") in err


def test_cli_validate_sin_docs_no_cambia(
    synthetic_content: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["validate", "--json"]) == 0
    assert "docs" not in json.loads(capsys.readouterr().out)


# -- los docs del repo -----------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]
DOC_FOLDERS = (REPO, REPO / "docs" / "guides")
# El destino de un link de Markdown, sin el ancla: `[texto](destino)` o `(destino#ancla)`.
_LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)\s]*)?\)")
_URL = re.compile(r"^[a-z][a-z0-9+.-]*:")
# El README usa links absolutos al repo, porque PyPI no resuelve los relativos.
_BLOB = "https://github.com/julimonte03/exo-harness/blob/main/"


def _local_target(doc: Path, target: str) -> Path | None:
    """El archivo del repo al que apunta un link, o None si es externo."""
    if target.startswith(_BLOB):
        return REPO / target[len(_BLOB) :]
    return None if _URL.match(target) else doc.parent / target


def test_los_docs_del_repo_coinciden_con_el_motor(capsys: pytest.CaptureFixture[str]) -> None:
    """D-48: los conteos y los comandos de README, QUICK-START, CONTRIBUTING y las guías."""
    argv = ["validate"] + [arg for folder in DOC_FOLDERS for arg in ("--docs", str(folder))]
    code = main(argv)
    out = capsys.readouterr().out
    assert code == 0, out
    assert "count marker" in out


def test_los_links_a_archivos_del_repo_existen() -> None:
    checked, broken = 0, []
    for folder in DOC_FOLDERS:
        for path in doc_files(folder):
            for target in _LINK.findall(path.read_text(encoding="utf-8")):
                local = _local_target(path, target)
                if local is None:
                    continue
                checked += 1
                if not local.exists():
                    broken.append(f"{path.relative_to(REPO).as_posix()}: {target}")
    assert broken == []
    assert checked > 10


def test_la_guia_de_copilot_permite_los_subcomandos_del_permiso_de_claude_code() -> None:
    """F8R3-6: `shell(exo:*)` reabre TM-21; la guía da una regla por subcomando, las mismas
    que el adaptador de Claude Code deja correr sin preguntar."""
    from exo.adapters import claude_code

    text = (REPO / "docs" / "guides" / "copilot.md").read_text(encoding="utf-8")
    rules = set(re.findall(rf"shell\({NAME} ([a-z][a-z0-9 ]*?):\*\)", text))
    assert rules == set(claude_code.AGENT_COMMANDS)
    assert "throwaway sandbox" in text and "check your Copilot version's rule syntax" in text
