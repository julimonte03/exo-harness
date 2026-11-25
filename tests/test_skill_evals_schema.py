"""Evals de skills (F7, criterio 3): el formato, la cobertura y la lectura de la salida.

Corre en la suite normal. Las corridas con Claude Code real están en
`test_skill_evals.py` (`agent_e2e`).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import _skill_evals as evals
from exo import content, packs

COLLECTION = packs.load_collection(content.content_root())
PACK_OF = {skill.name: skill.pack for skill in COLLECTION.skills}
SKILLS = set(PACK_OF)
FOLDERS = (
    sorted(p for p in evals.EVALS_DIR.iterdir() if p.is_dir()) if evals.EVALS_DIR.is_dir() else []
)


@pytest.mark.parametrize("folder", FOLDERS, ids=lambda p: p.name)
def test_cada_evals_json_es_valido(folder) -> None:
    found = evals.problems(evals.load(folder), folder.name, PACK_OF, set(COLLECTION.packs))
    assert found == [], found


def test_las_skills_de_prioridad_1_y_2_existen() -> None:
    """F7R1-28: un typo en `REQUIRED` no se filtra en silencio."""
    assert set(evals.REQUIRED) <= SKILLS, sorted(set(evals.REQUIRED) - SKILLS)


def test_criterio_3_las_skills_de_prioridad_1_y_2_tienen_sus_tres_casos() -> None:
    """Toda skill de prioridad 1 o 2 tiene su evals.json."""
    present = {p.name for p in FOLDERS}
    missing = [s for s in evals.REQUIRED if s not in present]
    assert missing == [], missing


def test_la_lista_de_prioridades_no_tiene_repetidas() -> None:
    assert len(set(evals.REQUIRED)) == len(evals.REQUIRED) == 38


def _event(**fields) -> str:
    return json.dumps(fields)


def _tool(name: str, args: dict) -> str:
    content_ = [{"type": "tool_use", "id": "t1", "name": name, "input": args}]
    return _event(type="assistant", message={"content": content_})


def test_parse_stream_ve_la_tool_skill_y_la_lectura_del_skill_md() -> None:
    lines = [
        _event(type="system", subtype="init"),
        _tool("Skill", {"skill": "accessibility-audit"}),
        _tool("Read", {"file_path": "C:\\p\\.claude\\skills\\judge-product\\SKILL.md"}),
        _tool("Read", {"file_path": "/p/.claude/skills/zod/references/x.md"}),
        _tool("Skill", {"skill": "accessibility-audit"}),
        "not json",
        _event(type="result", subtype="success", result="Done: WCAG 2.2 AA.", num_turns=4),
    ]
    run = evals.parse_stream(lines)
    assert run.used == ["accessibility-audit", "judge-product"]
    assert run.answer == "Done: WCAG 2.2 AA." and run.turns == 4 and run.error is None


def test_parse_stream_marca_el_error() -> None:
    run = evals.parse_stream([_event(type="result", subtype="error_max_turns", is_error=True)])
    assert run.error == "error_max_turns"


def test_parse_stream_guarda_las_skills_visibles_del_init() -> None:
    """F7R1-7: el informe dice qué skills veía el agente, para auditar el aislamiento."""
    init = _event(type="system", subtype="init", skills=["zod", "sdd-new"], tools=["Read"])
    assert evals.parse_stream([init]).visible == ["zod", "sdd-new"]
    assert evals.parse_stream([_event(type="system", subtype="init")]).visible is None
    assert evals.parse_stream([]).visible is None


def _case(checks: dict) -> evals.Case:
    return evals.Case(
        skill="x",
        id="output",
        expect="trigger",
        prompt="audit the form please",
        fixture="empty",
        packs=("core",),
        checks=checks,
    )


def test_check_output() -> None:
    case = _case(
        {
            "answer_contains": ["wcag"],
            "answer_matches": [r"2\.2"],
            "files_written": ["docs/*.md"],
        }
    )
    run = evals.Run(answer="Checked against WCAG 2.2 AA.")
    assert evals.check_output(case, run, ["docs/a11y.md"]) == []
    failed = evals.check_output(case, evals.Run(answer="ok"), [])
    assert len(failed) == 3


def test_file_contains_pide_un_archivo_escrito_con_todas_las_regex(tmp_path: Path) -> None:
    """F7R2-28: algún archivo escrito que coincide con el glob contiene cada regex."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("Verdict: APPROVED\n", encoding="utf-8")
    (tmp_path / "docs" / "b.md").write_text(
        "verdict: escalated\nSource: skill x\n", encoding="utf-8"
    )
    (tmp_path / "notes.md").write_text("ESCALATED Source: skill x\n", encoding="utf-8")
    written = ["docs/a.md", "docs/b.md", "notes.md"]
    case = _case({"file_contains": {"docs/*.md": [r"^verdict: ESCALATED", r"Source: skill \w+"]}})
    assert evals.check_output(case, evals.Run(), written, tmp_path) == []
    # Las dos regex tienen que estar en el mismo archivo, y entre los escritos.
    case = _case({"file_contains": {"docs/*.md": ["APPROVED", "Source"]}})
    [failure] = evals.check_output(case, evals.Run(), written, tmp_path)
    assert "docs/*.md" in failure and ("'Source'" in failure or "'APPROVED'" in failure)
    case = _case({"file_contains": {"docs/*.md": ["APPROVED"]}})
    assert evals.check_output(case, evals.Run(), ["notes.md"], tmp_path) == [
        "no written file matches 'docs/*.md'"
    ]
    with pytest.raises(ValueError, match="project"):
        evals.check_output(case, evals.Run(), written)


def test_files_unchanged_falla_si_la_corrida_creo_modifico_o_borro(tmp_path: Path) -> None:
    case = _case({"answer_contains": ["ok"], "files_unchanged": ["src/*", "pom.xml"]})
    run = evals.Run(answer="ok")
    assert evals.check_output(case, run, ["docs/report.md"], tmp_path) == []
    failed = evals.check_output(case, run, ["src/app.py", "docs/r.md"], tmp_path, ["pom.xml"])
    assert len(failed) == 2 and "src/app.py" in failed[0] and "pom.xml" in failed[1], failed


def test_removed_lista_lo_que_la_corrida_borro() -> None:
    before = {"a.py": 1, "b.py": 2, "c.py": 3}
    after = {"a.py": 1, "b.py": 5, "d.py": 4}
    assert evals.changed(before, after) == ["b.py", "d.py"]
    assert evals.removed(before, after) == ["c.py"]


def test_setup_valido_y_rutas_que_escapan() -> None:
    assert evals._setup_problems({"files": {"src/a.py": "x = 1\n"}, "stage": True}) == []
    found = evals._setup_problems({"files": {"../evil.py": "x", "/abs.py": "y", "ok.py": 3}})
    assert len(found) == 3, found
    assert evals._setup_problems({"files": {}}) and evals._setup_problems({"other": 1})


@pytest.mark.parametrize(
    "rel",
    [
        "C:/x.py",
        "C:\\x.py",
        "C:x.py",
        "..\\x.py",
        "src\\..\\..\\x.py",
        "src/../../x.py",
        "\\x.py",
        "\\\\server\\share\\x.py",
        "/etc/x",
        "src/a:stream",
        "src\\a.py",  # con `\` la misma ruta es otra en POSIX: siempre `/`
        "",
        ".",
        "src/",
    ],
)
def test_setup_rechaza_las_rutas_que_escapan_en_windows_y_posix(rel: str, tmp_path: Path) -> None:
    """F7R1-27: `C:/x` y `..\\x` escapaban en Windows."""
    assert evals._setup_problems({"files": {rel: "x"}}), rel
    with pytest.raises(ValueError):
        evals.setup_target(tmp_path, rel)


def test_setup_target_queda_dentro_del_proyecto(tmp_path: Path, make_dir_link) -> None:
    assert evals.setup_target(tmp_path, "src/a.py") == (tmp_path / "src" / "a.py").resolve()
    assert evals.setup_target(tmp_path, "./b.py") == (tmp_path / "b.py").resolve()
    (tmp_path / "elsewhere").mkdir()
    make_dir_link(tmp_path / "project" / "out", tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="outside"):
        evals.setup_target(tmp_path / "project", "out/x.py")  # un link que sale del proyecto


def test_el_comando_de_claude_aisla_la_config_de_usuario() -> None:
    """F7R1-7: sin la config, skills, plugins, hooks ni MCP de usuario."""
    command = evals.claude_command("claude", "do the thing please", "Read Skill", 40)
    assert command[:3] == ["claude", "-p", "do the thing please"]
    sources = command.index("--setting-sources")
    assert command[sources + 1] == "project,local"
    assert "--strict-mcp-config" in command and "--mcp-config" not in command
    assert command[command.index("--allowedTools") + 1] == "Read Skill"
    assert command[command.index("--max-turns") + 1] == "40"
    assert command[command.index("--output-format") + 1] == "stream-json"
    # M-17: el agente no publica nada, aunque `Bash(git:*)` lo permitiría.
    denied = command[command.index("--disallowedTools") + 1]
    assert "Bash(git push:*)" in denied and "PowerShell(git push:*)" in denied


def test_el_entorno_aisla_la_config_global_de_git(tmp_path: Path) -> None:
    """M-17 (threat model, TM-47): un `git config --global` del agente no toca el de la persona."""
    env = evals.runner_env(tmp_path / "data", {"PATH": "/usr/bin"})
    gitconfig = Path(env["GIT_CONFIG_GLOBAL"])
    assert gitconfig.parent == tmp_path / "data" and gitconfig.is_file()
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"


def _cubre(allowed: str, rule: str) -> bool:
    """Si alguna regla `Tool(prefijo:*)` de `allowed` cubre `rule` (`Tool(prefijo resto:*)`)."""
    tool, _, arg = rule.partition("(")
    for item in allowed.split():
        name, _, prefix = item.partition("(")
        if name == tool and prefix.endswith(":*)"):
            base = prefix[: -len(":*)")]
            if arg == prefix or arg.startswith(base + " "):
                return True
    return False


def test_el_permiso_del_proyecto_no_suma_tools_a_las_corridas() -> None:
    """F8R2-20: `--setting-sources project,local` carga `.claude/settings.json`, con el
    `permissions.allow` que escribe exo. Sea que Claude Code lo aplique o no en `-p`, no
    suma nada: cada regla está dentro de las tools de los evals y de los escenarios."""
    from exo.adapters import claude_code

    import _agents as agents
    from test_skill_evals import TOOLS

    assert claude_code.PERMISSIONS
    for allowed in (TOOLS, agents.claude_tools(python=False)):
        assert [r for r in claude_code.PERMISSIONS if not _cubre(allowed, r)] == []
    assert not _cubre("Bash(git:*)", "Bash(exo change:*)")
    assert not _cubre("Bash(exo:*)", "Bash(exotic:*)")


def _git_en(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], env=env, capture_output=True, text=True, timeout=60, check=False
    )


def test_el_entorno_bloquea_el_transporte_de_git(tmp_path: Path) -> None:
    """F8R2-6 (TM-47): `--disallowedTools "Bash(git push:*)"` es por prefijo y `git -C . push`
    lo saltea; el entorno corta el transporte: solo `file` (los repos locales de la corrida),
    también con `-c protocol.allow=always`, y ssh con un comando que no existe."""
    env = evals.runner_env(tmp_path / "data", os.environ)
    assert env["GIT_ALLOW_PROTOCOL"] == "file"
    assert env["GIT_SSH_COMMAND"] == evals.NO_SSH
    bare = tmp_path / "remoto.git"
    assert _git_en(env, "init", "-q", "--bare", str(bare)).returncode == 0
    assert _git_en(env, "ls-remote", str(bare)).returncode == 0  # file anda
    for url in ("https://127.0.0.1:9/x.git", "http://127.0.0.1:9/x.git", "ssh://git@127.0.0.1/x.git"):
        for extra in ((), ("-c", "protocol.allow=always")):
            done = _git_en(env, *extra, "ls-remote", url)
            assert done.returncode != 0
            assert "not allowed" in done.stderr, (url, extra, done.stderr)
    # Si algo dejara pasar ssh, git corre GIT_SSH_COMMAND, que no existe: no hay conexión.
    no_allow = {k: v for k, v in env.items() if k != "GIT_ALLOW_PROTOCOL"}
    done = _git_en(no_allow, "-c", f"core.sshCommand={shutil.which('git')}", "ls-remote", "ssh://git@127.0.0.1/x.git")
    assert done.returncode != 0
    assert evals.NO_SSH in done.stderr, done.stderr


def test_el_entorno_aisla_los_datos_y_antepone_el_bin_del_interprete(tmp_path: Path) -> None:
    """F7R1-29: el `exo` que corre el agente es el del intérprete de la suite."""
    base = {"PATH": os.pathsep.join(["/somewhere/else", "/usr/bin"]), "EXO_DATA_DIR": "/real"}
    env = evals.runner_env(tmp_path / "data", base)
    assert env["EXO_DATA_DIR"] == str(tmp_path / "data")
    assert env["EXO_MEMORY_DB"] == str(tmp_path / "data" / "memory.db")
    first, *rest = env["PATH"].split(os.pathsep)
    assert first == str(Path(sys.executable).parent)
    assert rest == ["/somewhere/else", "/usr/bin"]
    assert base["EXO_DATA_DIR"] == "/real"  # no toca el original


@pytest.mark.skipif(os.name != "nt", reason="en Windows las variables no distinguen mayúsculas")
def test_el_entorno_respeta_la_clave_path_de_windows(tmp_path: Path) -> None:
    env = evals.runner_env(tmp_path, {"Path": "C:\\tools"})
    assert [k for k in env if k.upper() == "PATH"] == ["Path"]
    assert env["Path"].endswith(os.pathsep + "C:\\tools")


def test_problems_exige_el_pack_de_la_skill() -> None:
    """F7R2-28: sin el pack de la skill, `exo init` no la instala y el caso no mide nada."""
    case = {"id": "trigger", "expect": "trigger", "prompt": "validate this payload with a schema"}
    data = {
        "skill": "zod",
        "fixture": "empty",
        "packs": ["core", "sdd"],
        "cases": [
            case,
            {**case, "id": "no-trigger", "expect": "no-trigger", "packs": ["core"]},
            {
                **case,
                "id": "output",
                "checks": {"answer_contains": ["zod"]},
                "review": "The schema is right.",
            },
        ],
    }
    found = evals.problems(data, "zod", {"zod": "frontend"}, {"core", "sdd", "frontend"})
    assert found == [
        "packs must include 'frontend', the pack of zod",
        "no-trigger: packs must include 'frontend', the pack of zod",
    ], found
    data["packs"] = ["core", "sdd", "frontend"]
    data["cases"][1]["packs"] = ["frontend", "ghost"]
    found = evals.problems(data, "zod", {"zod": "frontend"}, {"core", "sdd", "frontend"})
    assert found == ["no-trigger: unknown pack 'ghost'"], found


def test_problems_valida_los_chequeos_nuevos() -> None:
    base = {"id": "output", "expect": "trigger", "prompt": "validate this payload with a schema"}
    for checks, fragment in (
        ({"file_contains": {"src/*.ts": ["z\\.object("]}}, "bad regex"),
        ({"file_contains": {"src/*.ts": []}}, "file_contains"),
        ({"file_contains": ["src/*.ts"]}, "file_contains"),
        ({"files_unchanged": "pom.xml"}, "files_unchanged"),
        ({"files_unchanged": ["pom.xml"]}, "checks needs"),  # solo negativo: no mide nada
        ({"answer_contains": "zod"}, "answer_contains"),
    ):
        found = evals._case_problems({**base, "checks": checks, "review": "x"}, "zod", set(), None)
        assert any(fragment in p for p in found), (checks, found)
    ok = {"file_contains": {"src/*.ts": [r"z\.object\("]}, "files_unchanged": ["package.json"]}
    assert evals._case_problems({**base, "checks": ok, "review": "x"}, "zod", set(), None) == []


def test_problems_rechaza_lo_que_no_mide_nada() -> None:
    data = {
        "skill": "zod",
        "fixture": "nope",
        "packs": ["core", "ghost"],
        "cases": [
            {"id": "trigger", "expect": "trigger", "prompt": "use zod to validate this input"},
            {"id": "no-trigger", "expect": "trigger", "prompt": "short"},
            {"id": "output", "expect": "trigger", "prompt": "validate this payload at the edge"},
        ],
    }
    found = evals.problems(data, "zod", {"zod": "frontend"}, {"core"})
    joined = " | ".join(found)
    for fragment in (
        "fixture",
        "ghost",
        "must include 'frontend'",
        "names the skill",
        "no-trigger: expect",
        "sentence",
        "checks needs",
        "review",
    ):
        assert fragment in joined, (fragment, found)
