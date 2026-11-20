# ADR-0017 — Repo público en GitHub, CI con GitHub Actions y distribución de la v1.0

- **Estado:** Aceptada
- **Fecha:** 2026-11-19
- **Decisiones:** D-22, D-45, D-46 y D-48 (`docs/plan/04-DECISIONES.md`)
- **Reemplaza en parte:** ADR-0008. Sale la CI del motor en Azure Pipelines; lo demás de ADR-0008 ya lo había generalizado ADR-0014 (D-30).

## Contexto

F8 lleva el motor a la v1.0, que tiene que poder instalarse con un comando y estar probada en Windows, macOS y Linux. Hasta F7 el repo vivía solo en local, sin remoto, sin tags y sin CI que corriera. ADR-0008 apuntaba a Azure DevOps privado. Un repo privado no sirve para `curl … | sh` ni para `uvx --from git+…` sin un token.

## Decisión

### Repo

- **Público, en GitHub:** `https://github.com/julimonte03/exo-harness` (D-22).
- **Primer push:** `main` y las ramas de fase se subieron al empezar F8; los tags y los releases salen al cierre.
- **Limpieza previa (D-46):** antes del primer push se reescribió toda la historia con `git filter-repo`:
  - el autor pasó al noreply de GitHub del dueño;
  - `docs/referencia/` salió de la historia (queda en local, ignorada por git);
  - toda mención de la organización de origen o de sus herramientas pasó a un término genérico.

  Los hashes anteriores a la reescritura no existen en el remoto. El respaldo previo quedó fuera del repo, en la máquina del dueño.

### CI (D-45)

- **GitHub Actions:** `.github/workflows/ci.yml` con Windows, macOS y Linux y Python 3.10, 3.11, 3.12 y 3.13. Corre ruff, pytest con cobertura ≥ 85 %, `exo validate` y `--version` por las dos vías.
- **Jobs aparte:**
  - los extras de memoria;
  - los instaladores (`-m installer`);
  - el build (wheel y sdist, instalados en un venv limpio).
- **Corre sobre** `main`, las ramas `feat/**` y los PR.
- **`azure-pipelines.yml`** queda como ejemplo, sin mantenerse en paridad.

### Releases y distribución

- **Release:** un tag `vX.Y.Z` dispara `.github/workflows/release.yml`, que:
  - arma el wheel y el sdist;
  - escribe `SHA256SUMS`;
  - crea el release de GitHub con los artefactos;
  - publica en PyPI por *trusted publishing*, sin tokens guardados en el repo. Antes de la primera publicación hay un ensayo en TestPyPI.
- **Versión:** semver. La versión sale de `_meta.VERSION`, y el tag tiene que coincidir con ella (el workflow lo verifica). `CHANGELOG.md` registra cada versión.
- **Instaladores remotos:**
  - `install.sh` e `install.ps1` funcionan desde un clon (como hasta ahora) o por pipe (`curl -fsSL …/install.sh | sh`, `irm …/install.ps1 | iex`);
  - por pipe, instalan con `uv tool install` desde el repo en el ref de `EXO_REF` (por defecto, el último release), o con pip en un venv si no hay uv;
  - solo usan `https`;
  - cuando bajan un artefacto del release, verifican su `SHA256SUMS`.
- **Sin instalar:** `uvx --from git+https://github.com/julimonte03/exo-harness exo init`.
- **Marketplaces de agentes:** quedan fuera de la v1.0.

### Documentación (D-48)

- **En inglés** lo que lee quien usa el motor, como lo instalado (ADR-0011): `README.md`, `QUICK-START.md`, `docs/guides/`, `CONTRIBUTING.md` y `CHANGELOG.md`.
- **En español** el plan, los ADRs y los docstrings.

## Consecuencias

- **macOS** entra a la CI por primera vez: lo que falle ahí se arregla en F8.
- **La historia es otra:** un clon anterior a la reescritura no comparte commits con el remoto. No hay clones así, porque el repo era solo local.
- **PyPI** necesita que el dueño cree el proyecto y configure el *trusted publisher* en pypi.org. Sin eso, el release igual sale en GitHub.
- **Lo que baja `curl … | sh` es código que se ejecuta:** el threat model del motor (F8) lo cubre, y el README muestra cómo revisarlo antes de correrlo.
