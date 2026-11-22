"""Las anotaciones de GitHub Actions que `conftest.py` escribe por cada test que falla (D-45)."""

from __future__ import annotations

from types import SimpleNamespace

from conftest import ANNOTATION_LINES, annotation


def test_anotacion_de_un_test_que_falla() -> None:
    report = SimpleNamespace(
        location=("tests\\test_x.py", 41, "test_y"),
        nodeid="tests/test_x.py::test_y[a,b]",
        longreprtext="def test_y():\n>   assert 1 == 2\nE   assert 1 == 2: 100%\n",
    )
    assert annotation(report) == (
        "::error file=tests/test_x.py,line=42,title=tests/test_x.py%3A%3Atest_y[a%2Cb]"
        "::def test_y():%0A>   assert 1 == 2%0AE   assert 1 == 2: 100%25"
    )


def test_anotacion_de_un_error_de_coleccion_y_solo_el_final() -> None:
    lines = [f"línea {n}" for n in range(40)]
    report = SimpleNamespace(nodeid="tests/test_roto.py", longreprtext="\n".join(lines))
    text = annotation(report)
    assert text.startswith("::error file=tests/test_roto.py,line=1,title=tests/test_roto.py::")
    assert text.split("::", 2)[2] == "%0A".join(lines[-ANNOTATION_LINES:])
