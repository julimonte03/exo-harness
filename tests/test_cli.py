"""`exo --version` y `python -m exo --version` responden con la misma versión (F0, criterio 1)."""

from __future__ import annotations

import argparse
import os
import runpy
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

from exo import _meta

EXPECTED = f"{_meta.NAME} {_meta.VERSION}"


def test_version_en_proceso(capsys: pytest.CaptureFixture[str]) -> None:
    from exo.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == EXPECTED


def test_sin_argumentos_muestra_ayuda(capsys: pytest.CaptureFixture[str]) -> None:
    from exo.cli import main

    assert main([]) == 0
    assert f"usage: {_meta.NAME}" in capsys.readouterr().out


def test_modulo_main_en_proceso(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["exo", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("exo", run_name="__main__", alter_sys=True)
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == EXPECTED


def test_python_m_exo_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "exo", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == EXPECTED


def _console_script() -> Path | None:
    scripts = Path(sysconfig.get_path("scripts"))
    for name in (_meta.NAME, f"{_meta.NAME}.exe"):
        candidate = scripts / name
        if candidate.is_file():
            return candidate
    return None


def test_console_script_coincide_con_python_m() -> None:
    script = _console_script()
    if script is None:
        pytest.skip("el paquete no está instalado con `pip install -e .`")
    result = subprocess.run([str(script), "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == EXPECTED


# -- importación diferida de los subcomandos (F8) ------------------------------------------


def _choices(parser: argparse.ArgumentParser) -> list[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return list(action.choices)
    return []


def test_la_tabla_de_comandos_coincide_con_lo_que_registra_cada_modulo() -> None:
    """Un subcomando nuevo va en `commands.MODULES`: si no, el CLI lo encuentra igual (carga
    todos los módulos), pero arranca más lento."""
    import importlib

    from exo import commands

    for module, names in commands.MODULES.items():
        parser = argparse.ArgumentParser()
        importlib.import_module(f"exo.commands.{module}").register(parser.add_subparsers())
        assert tuple(_choices(parser)) == names, f"actualizá commands.MODULES[{module!r}]"
    every = [name for names in commands.MODULES.values() for name in names]
    assert len(every) == len(set(every))


def test_la_ayuda_general_tiene_todos_los_comandos_en_orden() -> None:
    from exo import commands
    from exo.cli import build_parser

    every = [name for names in commands.MODULES.values() for name in names]
    assert _choices(build_parser()) == every
    assert _choices(build_parser(["project"])) == list(commands.MODULES["project"])


def test_que_modulos_necesita_cada_llamada() -> None:
    from exo import commands

    every = list(commands.MODULES)
    assert commands.needed(["sync", "--project", "x"]) == ["project"]
    assert commands.needed(["mem", "search", "pagos"]) == ["memory"]
    assert commands.needed(["discover", "inventory"]) == ["tools"]
    assert commands.needed(["--version"]) == []
    for argv in ([], ["--help"], ["-h", "sync"], ["no-existe"]):  # la ayuda o el error
        assert commands.needed(argv) == every, argv


def test_un_comando_desconocido_sigue_dando_el_error_de_argparse(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from exo.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["no-existe"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice: 'no-existe'" in err and "'sync'" in err


_LOADED = (
    "import sys\n"
    "from exo.cli import main\n"
    "try:\n"
    "    main(sys.argv[1:])\n"
    "except SystemExit:\n"
    "    pass\n"
    "print(' '.join(sorted(m for m in sys.modules if m.startswith('exo.'))))\n"
)


@pytest.mark.parametrize(
    ("argv", "module", "absent"),
    [
        (["--version"], None, ("exo.memory", "exo.discovery", "exo.installer", "exo.sdd")),
        (["version"], "version", ("exo.memory", "exo.discovery", "exo.validate", "exo.sdd")),
        (["sync", "--help"], "project", ("exo.memory.store", "exo.validate", "exo.sdd.check")),
        (["mem", "--help"], "memory", ("exo.installer", "exo.discovery", "exo.adapters")),
    ],
)
def test_un_subcomando_importa_solo_su_modulo(
    argv: list[str], module: str | None, absent: tuple[str, ...]
) -> None:
    """F8: `exo sync` no carga la memoria ni el validador; `exo mem`, nada del instalador;
    `exo --version`, ningún subcomando."""
    from exo import commands

    src = str(Path(_meta.__file__).resolve().parents[1])
    done = subprocess.run(
        [sys.executable, "-c", _LOADED, *argv],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": src},
    )
    loaded = set(done.stdout.strip().splitlines()[-1].split())
    others = {f"exo.commands.{m}" for m in commands.MODULES if m != module}
    assert module is None or f"exo.commands.{module}" in loaded
    assert not loaded & others
    assert not {m for m in loaded if m.startswith(absent)}
