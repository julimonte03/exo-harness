# Threat model del motor `exo`

- **Criterio:** 8 de la v1.0 (`docs/plan/fases/F8-endurecimiento-y-distribucion.md`).
- **Código modelado:** la rama `feat/F8-v1`, primero en `93fe606` y actualizado en `d94f6c0`, con las mitigaciones que el dueño eligió para la v1.0. Versión `0.2.0` (`src/exo/_meta.py:16`).
- **Citas:** cada `path:line` se verificó contra `d94f6c0`. Las filas TM-3, TM-6 y TM-8, y las propuestas M-14 a M-16, son de los instaladores, con trabajo en curso: se actualizan aparte y sus citas siguen siendo las de `93fe606`. Una fila que dice "hasta `93fe606`" describe un riesgo que ya se mitigó, y nombra el commit que lo mitigó.
- **Método:** STRIDE con la escala de la skill `threat-modeling` (`content/packs/security/skills/threat-modeling/references/stride.md`). Las categorías OWASP salen de `content/packs/core/shared/owasp-2025.md`, siempre con año y CWE.
- **Quién acepta el riesgo residual:** el dueño del motor, en el rol `tech_lead` de este repo. Un residual Medio o más alto sin ADR que lo acepte queda **pendiente** de su aceptación o de la mitigación propuesta.

## Cómo se lee

- **P × I:** probabilidad e impacto **sin** la mitigación; el riesgo sale de la matriz de `stride.md`.
- **Residual:** la misma matriz con la mitigación puesta. Una mitigación baja la probabilidad; solo un cambio de diseño baja el impacto. Un impacto Alto o Crítico baja a Bajo solo si un test fija la mitigación; sin test queda en Medio como mínimo.
- **Impacto Crítico** es ejecutar código como la persona en su máquina o en la CI, o exponer una credencial: es tomar el sistema (`stride.md`, Impact).
- Los IDs son `TM-n`. Las mitigaciones propuestas son `M-n` y están al final, ordenadas por riesgo.

## Alcance

**Entra:** el motor y todo lo que lo rodea hasta que llega a una máquina o a un proyecto:
1. los instaladores remotos y su remoto simulado de los tests;
2. el release y la CI del motor;
3. los git hooks y el gobierno que corre en las máquinas del equipo y en la CI de cada proyecto;
4. el servidor MCP y el CLI como interfaz del agente (ADR-0005);
5. la memoria por usuario y sus proveedores de embeddings;
6. la ingeniería inversa;
7. las skills, los subagentes y los contratos de los packs;
8. `exo update` y `exo sync`;
9. las personas;
10. el runner de evals;
11. las variables de entorno `EXO_*`.

**Queda afuera:**
- los agentes (Claude Code, Copilot y los demás), sus sandboxes y sus sistemas de permisos, salvo cómo el motor los configura;
- la infraestructura de GitHub, PyPI y Hugging Face;
- el código propio de cada proyecto y la calidad del contenido de las skills, salvo como canal de instrucciones para el agente.

## Activos

| Activo | Nivel | Por qué importa |
|---|---|---|
| A1. Las máquinas del equipo: ejecutar código como la persona | Crítico | Todo lo demás de la persona cuelga de ahí: claves SSH, tokens, sesiones |
| A2. Credenciales: tokens del host del repo, `GITHUB_TOKEN` y OIDC de la CI, la API key de embeddings | Crítico | Con ellas se publica, se comenta en PRs o se lee código privado |
| A3. Integridad de lo que se distribuye: el script del instalador, el wheel, el sdist, el release de GitHub y PyPI | Crítico | Un artefacto alterado llega a cada máquina que instala |
| A4. Los archivos del proyecto: los del humano y los que genera el motor | Interno o Restringido | El motor escribe en repos ajenos |
| A5. La memoria por usuario (`memory.db`) y sus exports | Restringido | Junta observaciones de todos los proyectos de la persona y, por el riesgo aceptado de ADR-0009, puede tener secretos |
| A6. Los controles de gobierno: hooks, `exo check`, gates, `waivers.json`, `governance.*` | Integridad | Son lo que frena un secreto o un cambio sin aprobar |
| A7. Las instrucciones que lee el agente: `AGENTS.md`, skills, subagentes, contratos, overlays, memoria, `.claude/settings.json` | Integridad | Cambiarlas cambia lo que hace el agente en la máquina de cada persona |
| A8. La disponibilidad del flujo: subagentes, la CI, el servidor MCP | Disponibilidad | Sin ellos el ciclo SDD degrada |
| A9. Los datos de usuario fuera del repo: `persona.json`, `uninstall-backups/`, modelos | Interno | Viven fuera del control de versiones |

## Puntos de entrada

| Punto de entrada | Quién lo alcanza |
|---|---|
| `curl … \| sh` e `irm … \| iex` sobre los scripts de `main` | Cualquiera que instala; los cambia quien escribe en `main` |
| `EXO_REF`, `EXO_REPO_URL` y las demás `EXO_*` | Quien controla el entorno de la persona |
| Tags `v*`, `workflow_dispatch` y PRs del repo del motor | Quien tiene escritura; los PRs, cualquiera |
| Archivos versionados del proyecto: `.exo/`, hooks, skills instaladas, `AGENTS.md`, `.claude/settings.json` | Cualquiera que abre un PR o empuja una rama |
| Comandos `exo …` que corre el agente | El agente, influido por todo lo que lee |
| Tools del servidor MCP por stdio | El agente que lo lanzó |
| Código del proyecto analizado en la ingeniería inversa | Quien escribió ese código |
| Respuestas del proveedor de embeddings y de Hugging Face | Esos servicios |
| `evals.json` y fixtures del runner de evals | Quien escribe en este repo |

## Fronteras de confianza

- **Internet → máquina:** el instalador, `exo mem model pull`, los embeddings remotos.
- **Repo y CI del motor → artefactos publicados:** lo que se construye es lo que se instala.
- **Contenido versionado del proyecto → procesos locales:** lo escribe cualquiera con un PR y lo ejecutan git (hooks), el motor (config) y el agente (instrucciones).
- **Agente → motor:** el agente es un llamador a medias confiable: puede seguir instrucciones escondidas en lo que lee.
- **Motor → disco fuera del proyecto:** la carpeta de datos de usuario, y cualquier ruta a la que apunte un link.
- **Código analizado → modelo:** leer una línea la manda al proveedor del modelo.
- **Rama de un PR → CI del proyecto:** la CI corre con la config de la rama y con los tokens del pipeline.

## Diagrama de flujo de datos

```mermaid
flowchart LR
  dev([Persona del equipo])
  agent([Agente de IA])
  attacker([Autor de un PR o de código analizado])
  subgraph internet [Internet]
    gh[(GitHub: main, tags, releases)]
    pypi[(PyPI)]
    hf[(Hugging Face)]
    emb[(Embeddings remotos)]
  end
  subgraph enginecicd [CI del motor]
    release[release.yml: build, SHA256SUMS, release, PyPI]
  end
  subgraph machine [Máquina de la persona]
    installer[install.sh / install.ps1]
    exo[CLI exo y servidor MCP]
    hooks[git hooks: .exo/githooks]
    memdb[(memory.db: Restringido)]
    data[(Datos de usuario: persona, backups, modelos)]
  end
  subgraph project [Repo del proyecto]
    repo[(.exo/, skills, AGENTS.md, .claude/settings.json)]
    code[(Código analizado)]
  end
  subgraph projectci [CI del proyecto]
    check[exo check y exo gate publish]
  end
  release -- "wheel, sdist, SHA256SUMS (OIDC, GITHUB_TOKEN)" --> gh
  release -- "wheel, sdist" --> pypi
  dev -- "curl | sh, irm | iex" --> installer
  gh -- "script de main, tag, wheel, SHA256SUMS (https)" --> installer
  installer -- "instala" --> exo
  attacker -- "PR: config, hooks, skills, código" --> repo
  repo -- "instrucciones" --> agent
  code -- "líneas leídas" --> agent
  agent -- "comandos exo y tools MCP" --> exo
  exo -- "escrituras atómicas, snapshots" --> repo
  repo -- "core.hooksPath" --> hooks
  hooks -- "exo hook" --> exo
  exo -- "observaciones" --> memdb
  memdb -- "exo mem context" --> agent
  exo -- "texto de memorias (--allow-remote)" --> emb
  hf -- "modelos (mem model pull)" --> data
  repo -- "config y gates de la rama" --> check
```

## Amenazas por superficie

### 1. Instaladores remotos

`install.sh`, `install.ps1`, `uninstall.*` y `tests/_remote.py`.

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-1 | Tampering → Elevation of privilege | A1, A3 | El comando documentado baja el script de la rama `main` (`install.sh:5`, `install.ps1:30`), no de un tag. Quien empuja a `main` (o roba la cuenta del dueño) cambia el script, y cada `curl … \| sh` siguiente corre su código, aunque después instale un release. | Baja × Crítico = Alto | TLS de raw.githubusercontent.com (`curl -fsSL`); todo corre desde `main "$@"` en la última línea, así un corte no ejecuta medio script (`install.sh:247-249`, `install.sh:351`); por pipe, PowerShell corre dentro de un bloque y no cambia la sesión (`install.ps1:48-53`); los encabezados muestran cómo bajarlo y leerlo antes (`install.sh:7-11`, `install.ps1:24-27`). Nada fija el contenido del script. | **Alto**, pendiente: M-4 |
| TM-2 | Tampering | A1 | Alguien que controla el entorno pone `EXO_REPO_URL` o `EXO_REF` para instalar desde un espejo propio o un ref con caracteres que cambian la URL o el requisito de pip. | Baja × Bajo = Bajo | Solo `https://`, `file:///` y http a `127.0.0.1`/`localhost`; sin `@`, `?` ni `#` (`install.sh:96-110`, `install.ps1:147-158`); refs sin `..`, sin `-` inicial y con caracteres acotados (`install.sh:112-119`, `install.ps1:160-167`); tests `tests/test_installers.py:357`, `:367`, `:452`, `:462`. La excepción de `file://` y loopback no sale de la máquina y sirve para los tests y un espejo local. El impacto es Bajo porque quien controla el entorno ya corre código como la persona (ADR-0006, `docs/adr/0006-agentes-y-deteccion.md:44`). | Bajo |
| TM-3 | Tampering | A1, A3 | Una redirección de la descarga baja a `http://` y alguien en la red cambia el wheel **y** su `SHA256SUMS`. | Baja × Crítico = Alto | Desde `67d4b8a`, ninguna descarga sigue un salto a otro protocolo. Con curl, `--proto` y `--proto-redir` con el protocolo de `EXO_REPO_URL` (`install.sh:127-129`). Con `https` y sin curl no se baja nada: wget sigue redirecciones a cualquier protocolo, así que `fetch` pide curl (`install.sh:130-132`) y wget queda para http a loopback; `redirect_of` con wget no sigue el salto (`--max-redirect=0`, `install.sh:143`). En PowerShell, `Save-Url` sigue las redirecciones a mano y rechaza la que cambia de protocolo antes de pedirla, en cada salto y no solo en la URI final (`install.ps1:168-200`, `:194-196`). El remoto simulado responde `302` de `http://127.0.0.1` a `https://` en un puerto que rechaza conexiones (`tests/_remote.py:96-99`, `:214-217`); tests `tests/test_installers.py:399` (curl), `:435` (sin curl no se usa wget), `:552` (PowerShell). Hoy GitHub redirige solo a https (supuesto S-4). Sin uv y sin curl no se puede instalar un release desde https (M-6 descartada). | Bajo |
| TM-4 | Tampering, Spoofing | A3 | `SHA256SUMS` sale del mismo release que el wheel: quien puede editar el release (la cuenta del dueño, el `GITHUB_TOKEN` con `contents: write` o una action comprometida en ese job) cambia los dos juntos. El checksum prueba integridad, no autenticidad. | Baja × Crítico = Alto | El checksum frena una descarga cortada o un asset cambiado solo (`install.sh:169-189`, `install.ps1:216-247`); exige exactamente un wheel con nombre acotado (`install.sh:172-179`, `install.ps1:224-229`); test `tests/test_installers.py:346`, `:431`. No hay firma ni atestación del build. | **Alto**, pendiente: M-4 |
| TM-5 | Tampering | A3 | El camino con uv (y sin uv, una rama o un commit) instala con git sobre https en el ref (`install.sh:213-220`, `install.ps1:275-287`), sin checksum. Un tag se puede mover con un force-push, y el mismo ref pasa a apuntar a otro código. | Baja × Crítico = Alto | TLS y la identidad de GitHub; `uv tool install` sin `--force` no pisa otro `exo` (`install.sh:290-291`, `install.ps1:292-293`). Nada impide mover un tag (supuesto S-2). | **Alto**, pendiente: M-4 |
| TM-6 | Tampering | A3 | Hasta `c46eac6`, sin uv, si bajar `SHA256SUMS` fallaba por cualquier razón (red, una redirección rechazada, un release sin el archivo), el instalador pasaba en silencio a git sobre el mismo ref, sin checksum: un *fail open*. | Media × Bajo = Bajo | Desde `0c60bc5`, un ref con forma de release (`v` y un dígito, como los tags de `release.yml`) se detiene si su `SHA256SUMS` no baja, con un mensaje accionable y la causa de la descarga (`install.sh:213-226`, `install.ps1:243-250`); test con un tag de git cuyo release no trae `SHA256SUMS` (`tests/_remote.py:194-196`): `tests/test_installers.py:384`, `:535`. Una rama o un commit siguen yendo por git, sin checksum, porque no tienen release; ese camino es https al mismo origen. | Bajo |
| TM-7 | Spoofing | A1 | Hay otra herramienta que se llama `exo` (ADR-0001) y el instalador la pisa, o la persona corre la otra creyendo que es el motor. | Media × Medio = Medio | El link de `~/.local/bin/exo` se pisa solo si apunta al venv del motor (`install.sh:297-304`); uv sin `--force` no reemplaza una herramienta ajena (`install.sh:290-291`); el paquete se llama `exo-harness` (`pyproject.toml:9`). | Bajo |
| TM-8 | Tampering | A9 | Hasta `c46eac6`, `uninstall.ps1` pasaba `$Venv`, armado con `EXO_DATA_DIR`, a `Test-Path` y `Remove-Item` sin `-LiteralPath`: con `[`, `]` o `*` en la ruta, PowerShell la leía como comodín, y con `datos[1]` borraba `datos1\venv` y dejaba el propio; `install.ps1` no encontraba el `exo.exe` recién instalado. | Baja × Medio = Bajo | Desde `b24d6de`, `-LiteralPath` en `uninstall.ps1:90-94` y en `install.ps1:337`; el resto ya lo usaba, y `Join-Path` y `New-Item -Path` no expanden comodines en 5.1 (probado con `datos[1]`). Tests con `datos[1]` y una `datos1\venv` al lado: `tests/test_installers.py:580` (desinstalar) y `:594` (instalar por pipe y desinstalar). `uninstall.sh` borra solo `$DATA_DIR/venv` y el link si apunta ahí (`uninstall.sh:51-60`). | Bajo |
| TM-9 | Information disclosure | A4 | Mientras corren los tests de instaladores, el remoto simulado sirve por http una foto del árbol que incluye los archivos sin trackear que git no ignora (`tests/_remote.py:120-134`): otro usuario de la máquina puede leerlos en esa ventana. | Baja × Medio = Bajo | Escucha solo en `127.0.0.1`, en un puerto libre, mientras dura el bloque (`tests/_remote.py:185-199`); git aislado de la config del dev (`tests/_remote.py:101-113`). | Bajo |

### 2. Release y CI del motor

`.github/workflows/release.yml` y `.github/workflows/ci.yml`.

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-10 | Tampering → Elevation of privilege | A2, A3 | Una action de terceros se compromete y se mueve su tag (o su rama, como la `release/v1` de PyPI en `93fe606`): corre en el job con `contents: write` o con `id-token: write` y publica un release o un paquete alterado. | Baja × Crítico = Alto | Desde `b368bc8`, todas las actions van fijadas por SHA con su versión en un comentario (`release.yml:42`, `:44`, `:80`, `:86`, `:102`, `:104`, `:109`, `:147`, `:152`, `:166`, `:171`; `ci.yml:28`, `:30`), y Dependabot propone cada versión nueva como PR (`.github/dependabot.yml:5-12`); test `tests/test_workflows.py:75` y `:92`. Mínimo privilegio: `contents: read` por defecto (`release.yml:33-34`, `ci.yml:10-11`); escritura solo en el job del release (`release.yml:98-99`); OIDC solo en los jobs de PyPI (`release.yml:144-145`, `:163-164`); el environment `pypi` con aprobación del dueño (`release.yml:12-15`, supuesto S-3). Queda que una versión comprometida entre por un PR de Dependabot aprobado sin revisar. | Bajo |
| TM-11 | Tampering | A3 | El build instala `build` y `twine` sin versión (`release.yml:61`) y el backend `hatchling>=1.27` (`pyproject.toml:1-4`) desde PyPI, sin hashes: una versión comprometida de cualquiera de los dos mete código en el wheel que después se firma con el checksum. En la CI, `pip install -e ".[dev]"` (`ci.yml:40`, `pyproject.toml:45`) tiene el mismo problema con menos impacto (token de solo lectura). | Baja × Crítico = Alto | El wheel se instala en un venv limpio y corre `exo --version` y `exo validate` (`release.yml:67-72`), que detecta un paquete roto, no uno alterado. | **Alto**, pendiente: M-5 |
| TM-12 | Elevation of privilege | A3 | Quien tiene escritura empuja un tag `v*` y sale un release de GitHub sin aprobación: el environment con revisores protege solo el job de PyPI (`release.yml:92-99` frente a `:135-145`). Sin uv, `install.sh` instala el último release de GitHub. | Baja × Crítico = Alto | El tag tiene que coincidir con `_meta.VERSION` (`release.yml:48-57`); `gh release create --verify-tag` (`release.yml:128-133`). Hoy solo el dueño escribe (supuesto S-1). | **Alto**, pendiente: M-4 |
| TM-13 | Tampering | A2 | Inyección de comandos en un `run:` a través del nombre del tag o de otra expresión `${{ }}`. | Baja × Crítico = Alto | Las expresiones entran por `env:` y no dentro del script (`release.yml:50-54`, `release.yml:115-118`); desde `b368bc8`, un test falla si un `run:` de cualquier workflow contiene `${{` (`tests/test_workflows.py:60`). | Bajo |
| TM-14 | Elevation of privilege | A2 | Un PR desde un fork corre código en la CI. | Media × Bajo = Bajo | `pull_request`, no `pull_request_target` (`ci.yml:4-8`; test `tests/test_workflows.py:67`), con `contents: read` (`ci.yml:10-11`) y sin secretos; el release no reutiliza artefactos de la CI: `download-artifact` baja solo los de su corrida (`release.yml:104-112`). | Bajo |
| TM-15 | Tampering | A3 | `workflow_dispatch` publica en TestPyPI el build de cualquier rama, con el environment `testpypi` sin reglas (`release.yml:15`, `release.yml:154-177`). | Baja × Bajo = Bajo | Solo quien tiene escritura lanza el workflow; TestPyPI no es lo que se instala; sin tokens guardados (ADR-0017, `docs/adr/0017-repo-publico-ci-y-distribucion.md:41`). | Bajo |

### 3. Git hooks y gobierno en las máquinas y en la CI del proyecto

`src/exo/governance/`, `core.hooksPath` y `exo gate publish`.

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-16 | Elevation of privilege | A1 | `core.hooksPath` apunta a `.exo/githooks/`, una carpeta **versionada** (`src/exo/governance/githooks.py:34`, `:114-119`, `:160`; `src/exo/adapters/generic.py:81-84`). Git no corre hooks versionados justamente por esto: un PR, o una rama de un compañero, cambia `.exo/githooks/pre-commit`, y quien hace checkout de esa rama y commitea ejecuta ese código. | Baja × Crítico = Alto | Los hooks están en el lock: `exo doctor` avisa un cambio a mano (`src/exo/doctor.py:162-168`) y `exo sync` informa el conflicto (`src/exo/installer/engine.py:360-369`) o reescribe el hook si el PR también tocó el lock (`engine.py:370-375`); `exo codeowners` le da al `tech_lead` `.exo/` y, desde `378d004`, también `.husky/`, `.pre-commit-config.yaml` y `.gitattributes` (`src/exo/commands/governance.py:60-69`, `:82-91`; test `tests/test_p0.py:64`), así que un hook alterado no llega a `main` sin su revisión si el host la exige (supuesto S-5). Nada de eso actúa antes del checkout de una rama que todavía no se revisó, y `exo check` no compara los hooks con los del motor (`src/exo/sdd/check.py:408-462`). | **Alto**, pendiente: el resto de M-3 |
| TM-17 | Repudiation, Tampering | A6 | Alguien saltea los hooks con `--no-verify`, o no tiene `exo` en el PATH y el hook sale con 0 (`githooks.py:57-61`). | Alta × Medio = Alto | **Riesgo aceptado** por el dueño en ADR-0014: los hooks son ayuda temprana y la CI es el gate (`docs/adr/0014-enforcement-agnostico.md:28-29`). `exo check --base` repite el escaneo en la CI (`content/packs/core/shared/ci-and-review.md:9-24`) y falla cerrado si git falla (`src/exo/sdd/check.py:387-390`; `src/exo/governance/hookrun.py:164-172`, `:303-309`). | Bajo, si la protección de rama exige la CI (supuesto S-5) |
| TM-18 | Tampering | A1 | `EXO_HOOK_CMD` reemplaza el ejecutable que corre el hook, sin comillas (`githooks.py:36`, `:54-56`). | Baja × Bajo = Bajo | La define quien controla el entorno de la persona, que ya corre código como ella (ADR-0006, `docs/adr/0006-agentes-y-deteccion.md:44`). | Bajo |
| TM-19 | Tampering | A6 | `exo check` lee la config y los waivers de la **rama del PR** (`src/exo/sdd/check.py:417`; `hookrun.py:132-137`): un PR vacía `governance.gates` de su tier, saca detectores de `data_protection.pii` o suma un waiver con un `approved_by` que escribe él mismo, y su propio gate pasa. | Media × Alto = Alto | Un secreto nunca tiene waiver (`src/exo/core/waivers.py:88-91`); el motor no verifica roles y la aprobación efectiva es CODEOWNERS más la protección de rama (`ci-and-review.md:160-168`), con `.exo/` para el `tech_lead` (`src/exo/commands/governance.py:82-91`). Depende de que el proyecto lo configure. | **Medio**, pendiente: M-2 |
| TM-20 | Elevation of privilege | A2 | `exo gate publish` corre `review.publish_command` de la config de la rama con `shell=True` (`src/exo/governance/gates.py:111`, `:121-135`). En una CI que publica con un token de escritura sobre PRs de forks o con `pull_request_target`, el autor del PR elige el comando y se lleva el token. | Media × Crítico = Crítico | Por defecto es `null` y solo imprime (`src/exo/core/config.py:93`; `gates.py:112-113`). Desde `c46eac6`, el comando corre solo si esta máquina lo aprobó por su SHA256 (`gates.py:114-118`; `src/exo/governance/approvals.py:58-73`; test `tests/test_gates_publish.py:177`): eso cubre a quien publica desde su máquina una rama ajena, porque ve el comando y lo aprueba. En la CI no ayuda: la carpeta de datos es nueva en cada corrida y el pipeline aprueba con `--approve-command` (`src/exo/commands/gate.py:34-38`) lo que traiga la rama. Ahí la protección sigue siendo el contrato: aprobar solo en un pipeline confiable y nunca publicar con token de escritura en PRs de forks o en `pull_request_target` (`ci-and-review.md:97-98`). | **Alto**, pendiente: M-2 |

### 4. El servidor MCP y el CLI como interfaz del agente

`src/exo/mcp/`, `src/exo/tools/` y el permiso que el adaptador de Claude Code le da al agente.

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-21 | Elevation of privilege | A1, A2 | Hasta `93fe606`, el adaptador agregaba `Bash(exo:*)` y `PowerShell(exo:*)` a `permissions.allow`, y el agente corría **cualquier** subcomando sin preguntar. Un agente con prompt injection (código revisado, un ticket, una página) corría `exo init --yes --publish-command "<cmd>"`, que reescribe la config sin preguntar (`src/exo/commands/project.py:67-71`, `:276`, `:327-346`, `:604-607`; `src/exo/installer/project.py:136-138`, `:162-163`), y después `exo gate publish`, que ejecuta `<cmd>` en un shell (`gates.py:133-135`). Era ejecución arbitraria sin ningún pedido de permiso. Con el mismo permiso podía habilitar embeddings remotos (`exo mem reindex --allow-remote`), borrar memoria o desinstalar con `--force`. | Media × Crítico = Crítico | Desde `02472cb`, el permiso cubre solo los subcomandos que las skills corren solas (`src/exo/adapters/claude_code.py:37-60`, `:63-67`, `:78-82`). `init`, `sync`, `update`, `uninstall`, `restore`, `gate`, `mem reindex`, `mem delete`, `mem export`, `mem import` y `mem projects` quedan afuera y los aprueba la persona (test `tests/test_adapters.py:109`), y `exo sync` reemplaza el permiso viejo en los proyectos instalados (test `tests/test_adapters.py:126`). Desde `c46eac6`, además, `exo gate publish` no corre un comando que esta máquina no aprobó: con TTY lo muestra y pregunta, y sin TTY se niega (`src/exo/governance/gates.py:114-118`; `src/exo/commands/gate.py:63-70`; test `tests/test_gates_publish.py:177`). Claude Code aplica las reglas recién con el workspace confiable (`claude_code.py:5-10`), y Copilot no recibe la regla (ADR-0005), así que pregunta. Queda un camino social: la persona aprueba en el agente un `exo gate publish --approve-command` cuyo pedido de permiso no muestra el comando. | Bajo; el camino social, en la propuesta de M-1 |
| TM-22 | Tampering, Information disclosure | A4 | Un agente pasa a una tool un `cwd` o un `target` fuera del proyecto, nombres con `..` o argumentos de más, para leer o comparar otra carpeta. | Media × Alto = Alto | Validación S2 compartida por el CLI y el MCP (ADR-0005, `docs/adr/0005-cli-primero-mcp-opcional.md:17-18`): `cwd` resuelto dentro de la raíz (`src/exo/tools/validation.py:43-56`), nombres de skill y de change acotados (`validation.py:24-40`), argumentos desconocidos rechazados (`validation.py:66-69`; `src/exo/tools/base.py:40-48`), `target` con `resolve_within` (`src/exo/tools/registry.py:98-102`); tests `tests/test_tools.py:43`, `:59`, `:64`, y la regresión de `exo p0` (`src/exo/governance/p0.py:82-112`). El MCP está apagado por defecto (`config.py:95`; `claude_code.py:87-90`). | Bajo |
| TM-23 | Information disclosure | A5 | `mem_get` y `mem_delete` aceptan cualquier ID, de cualquier proyecto (`src/exo/tools/memory.py:154-155`, `:163-167`; `src/exo/memory/store.py:508-522`), y `all_projects` abre la búsqueda a todos (`tools/memory.py:37`, `:85-86`). Un agente con prompt injection en el proyecto A lee observaciones del proyecto B (otro cliente) y las deja en un commit, un PR o una página. | Media × Medio = Medio | Las búsquedas y listas van al proyecto detectado salvo que se pida lo contrario (`tools/memory.py:85-86`). La memoria es por usuario y sin auth por decisión (ADR-0009, `docs/adr/0009-memoria-por-usuario.md:26-29`), pero esa decisión no trata la lectura cruzada por un agente. | **Medio**, pendiente: M-8 |
| TM-24 | Tampering | A5 | Las tools que escriben (`mem_delete`, `mem_projects_merge`, `mem_projects_consolidate`: `tools/memory.py:305-311`, `:358-378`) borran o mezclan sin confirmación y sin vuelta atrás (`store.py:508-513`). | Baja × Medio = Bajo | `consolidate` tiene `dry_run`; los IDs se validan (`tools/memory.py:42-51`). | Bajo |
| TM-25 | Denial of service, Tampering | A8 | Una librería nativa escribe en el descriptor 1 durante una tool y rompe el protocolo, o una línea gigante sin fin agota la memoria del servidor. | Baja × Bajo = Bajo | stdout de Python redirigido a stderr durante cada tool (`src/exo/mcp/server.py:72-75`); salida en ASCII, siempre JSON válido (`server.py:113-116`); una tool o un mensaje que falla no tiran el servidor (`server.py:79-81`, `:119-129`; test `tests/test_mcp.py:152`). `contextlib.redirect_stdout` no cubre el descriptor 1 de una librería en C, y `for raw in stdin` no limita el largo de la línea (`server.py:142`). El cliente es local. | Bajo (M-18) |

### 5. La memoria

Una base SQLite por usuario, sin guard, con export sin redactar y con proveedores de embeddings.

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-26 | Information disclosure | A2, A5 | Un agente guarda un token en una observación y la persona después la comparte con `exo mem export`, que sale sin redactar (`src/exo/memory/exchange.py:34-59`). | Baja × Crítico = Alto | **Riesgo aceptado** por el dueño en ADR-0009 (`docs/adr/0009-memoria-por-usuario.md:30-32`, `:62`) y D-24 (`docs/plan/04-DECISIONES.md:159`). Pauta para el agente en las reglas (`content/rules/AGENTS.base.md:10`, `:51`); la ayuda del comando dice "unredacted" (`src/exo/commands/memory.py:510`). | Alto, **aceptado** (ADR-0009) |
| TM-27 | Information disclosure | A5, A9 | Hasta `93fe606`, en Linux la carpeta de datos se creaba con el `umask` y los archivos nuevos quedaban en `0644` (`src/exo/core/fsutil.py:24`): en una máquina compartida, otro usuario leía `memory.db`, `persona.json`, los `uninstall-backups/` con el contenido de `.exo/` de cada proyecto y lo que escribía `exo mem export --output`. | Baja × Alto = Medio | Desde `2634c05`, en POSIX: `paths.private_dir` crea en `0700` las carpetas que faltan, sin tocar las que ya existen (`src/exo/paths.py:18-45`); la base y sus `-wal` y `-shm` quedan en `0600`, también una base vieja al abrirla (`src/exo/memory/db.py:70-94`); `persona.json`, `approved-commands.json`, los backups de desinstalación y `exo mem export --output` se escriben en `0600` (`src/exo/persona.py:71-72`; `src/exo/governance/approvals.py:72-73`; `src/exo/installer/project.py:316-317`; `src/exo/commands/memory.py:177`); `exo doctor` avisa si otros leen la carpeta de datos (`src/exo/doctor.py:364-380`). Tests `tests/test_private_data.py:45`, `:59`, `:68`, `:85`, `:93`. Desde `9b9a35d`, `install.sh` crea la carpeta de datos y las que le falten en `0700`, sin tocar una que ya existe, antes del venv y del PATH (`install.sh:254-259`, `:328`, `:346`); test `tests/test_installers.py:325`. En Windows `%LOCALAPPDATA%` es por usuario y en macOS `~/Library` es `0700` (supuesto S-10). | Bajo |
| TM-28 | Information disclosure | A5 | Las memorias de **todos** los proyectos salen a un servicio remoto de embeddings. | Baja × Alto = Medio | Un proveedor remoto exige `--allow-remote` (`src/exo/memory/embeddings/__init__.py:109-115`); el permiso vive en la `meta` de la base, no en el repo (`src/exo/memory/index.py:45-56`; `store.py:211-218`; ADR-0009, `:63`), así que un PR no lo prende, y `exo doctor` avisa que la sección `memory` del proyecto no tiene efecto (`src/exo/doctor.py:342-348`); Ollama fuera de loopback también lo exige y el local va sin proxies (`src/exo/memory/embeddings/http.py:35-37`, `:106-115`); tests `tests/test_memory_semantic.py:208`, `tests/test_memory_providers.py:79`. El riesgo lo acepta la persona que pasa `--allow-remote` (invariante 11, `AGENTS.md:25`); desde `02472cb`, `exo mem reindex` queda fuera del permiso del agente (TM-21). | Bajo |
| TM-29 | Information disclosure | A2 | Hasta `93fe606`, la API key del proveedor `openai-compatible` viajaba a otro destino: `urllib` sigue las redirecciones y **reenvía `Authorization`** al nuevo origen (verificado el 2026-11-24 con Python 3.14: un `302` a otro puerto recibió `Bearer …`), y `EXO_EMBEDDINGS_URL` aceptaba `http://` sin chequeo. | Baja × Alto = Medio | Desde `28ae30e`, los dos openers usan `_NoRedirect`: un 3xx es un error que dice adónde redirigía, y ni la clave ni el texto van a otra dirección (`src/exo/memory/embeddings/http.py:26-38`, `:55-65`); `EXO_EMBEDDINGS_URL` tiene que ser `https://`, salvo http a esta máquina (`http.py:133-139`). Tests `tests/test_memory_providers.py:127` y `:146`. La clave sale de una variable de entorno, nunca de la base (`http.py:1-6`, `:141-144`). | Bajo |
| TM-30 | Tampering | A7 | Envenenamiento de la memoria: un agente con prompt injection guarda una "convención" con instrucciones, y `exo mem context` se la inyecta en las sesiones siguientes (`content/rules/AGENTS.base.md:48`); si es `personal`, en todos los proyectos (`store.py:5`). | Media × Medio = Medio | Tipos y `topic_key` validados (`src/exo/memory/model.py:21-22`); nada marca la memoria como dato ni dice de qué sesión o agente vino. | **Medio**, pendiente: M-8 |
| TM-31 | Tampering, Denial of service | A5 | Un export armado o entradas enormes rompen la base o la llenan. | Baja × Medio = Bajo | `import` valida todo antes de escribir, en una transacción, y no pisa lo local más nuevo (`exchange.py:5-7`, `:76-119`); límites de contenido, título y resultados (`model.py:16-19`; `store.py:56`, `:63`; `tools/memory.py:241-242`). | Bajo |
| TM-32 | Tampering | A1, A5 | `exo mem model pull` baja de Hugging Face sin fijar revisión ni hash (`src/exo/memory/embeddings/static.py:58-71`; `src/exo/memory/embeddings/onnx.py:61-69`): un repo comprometido entrega otro modelo. | Baja × Medio = Bajo | Solo con el comando explícito (ADR-0009, `:38`); al usarlo, solo archivos locales (`onnx.py:36-39`); `static` baja solo `json`, `safetensors`, `txt` y `model`, sin pickles (`static.py:66-70`). | Bajo (M-19) |

### 6. La ingeniería inversa

Invariante 10 (`AGENTS.md:24`): solo lectura sobre el código del proyecto analizado.

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-33 | Tampering | A4 | El agente que extrae una unidad modifica el código analizado, por error o por una instrucción escondida. | Media × Alto = Alto | El motor escribe solo bajo `.exo/discovery/`, con `join_within` (`src/exo/discovery/store.py:46-55`); los subagentes `re-extractor` y `re-auditor` tienen solo `Read, Grep, Glob` (`content/packs/discovery/agents/re-extractor.md:4`, `content/packs/discovery/agents/re-auditor.md:4`; ADR-0015, `docs/adr/0015-ingenieria-inversa.md:109`); `exo discover status` lista los cambios fuera de las rutas permitidas (`src/exo/discovery/pipeline.py:54-63`, `:83-126`; ADR-0015, `:14`). Es detección, no prevención: inline (un agente sin subagentes) el agente tiene todas sus tools, y un cambio ya commiteado no aparece en `git status`. | **Medio**, pendiente: M-11 |
| TM-34 | Elevation of privilege | A1, A7 | Prompt injection desde el código: un comentario dirigido a la IA le pide al extractor correr un comando o cambiar lo que reporta. | Media × Alto = Alto | El motor marca esas líneas como `suspicious_lines` (`src/exo/discovery/units.py:110-124`, con `src/exo/validate.py:327-339`); la skill dice que son datos para reportar, nunca órdenes (`content/packs/discovery/skills/re-extract/SKILL.md:39`, `:45`); en modo subagente no hay shell (`re-extractor.md:4`). La detección es heurística. | **Medio**, pendiente: M-11 |
| TM-35 | Information disclosure | A2 | El extractor lee un secreto del código y lo manda al modelo, o lo copia al documento de la unidad. | Alta × Alto = Crítico | Los archivos de credenciales quedan como `sensitive` y no se leen (`src/exo/discovery/files.py:492-497`); `secret_lines` le dice a la skill que lea alrededor (`units.py:118-120`; `re-extract/SKILL.md:44`); `exo discover done` corre el escáner y un Crítico no tiene waiver (ADR-0015, `:69`). **Riesgo aceptado** en ADR-0015: leer esas líneas igual las manda al modelo. | Medio, **aceptado** (ADR-0015) |
| TM-36 | Denial of service, Elevation of privilege | A4, A8 | Un repo con archivos enormes o con links hace que el análisis lea fuera del proyecto o no termine. | Media × Medio = Medio | Nunca sigue symlinks ni junctions (`files.py:3-5`, `:383`, `:407`); salta lo que pasa de 1 MB (`files.py:41`, `:500-506`); timeout de `git log` (`src/exo/discovery/git_metrics.py:28`). | Bajo |
| TM-37 | Elevation of privilege | A1 | Correr git en un proyecto que llegó como archivo con su `.git/` (no como clon) ejecuta lo que diga su `.git/config` (por ejemplo `core.fsmonitor`) en `git status` o `git log` (`pipeline.py:94-101`; `git_metrics.py:63-80`). | Baja × Bajo = Bajo | Los diffs van sin diff externo ni textconv (`src/exo/governance/git.py:22-31`); `safe.directory` de git cubre las carpetas de otro dueño. El impacto incremental es Bajo: la persona corre git ahí de todos modos (supuesto S-9). | Bajo |

### 7. Las skills, los subagentes y los contratos de los packs

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-38 | Tampering, Elevation of privilege | A7 | Una skill de terceros, o contenido propio con `EXO_CONTENT_ROOT` (`src/exo/content.py:29-35`), trae instrucciones escondidas: pisar las reglas, bajar y ejecutar, mandar datos afuera o caracteres invisibles. | Baja × Alto = Medio | `exo validate` advierte en `SKILL.md`, `references/`, scripts y subagentes (`validate.py:448-472`, `:554-557`, `:668`), y corre en la CI y en el release (`ci.yml:48-49`; `release.yml:72`); skills copiadas byte a byte, sin plantillas, así ningún valor de la config entra en una skill (invariante 7, `AGENTS.md:21`; `src/exo/installer/bundle.py:60-61`; `src/exo/adapters/base.py:66-71`); regla de no copiar skills de terceros sin licencia (`AGENTS.md:58`). Huecos: son advertencias; no cubren los contratos compartidos, los overlays ni las reglas base (`validate.py:561-576`, `:709-717`); y `exo sync` no valida el contenido de `EXO_CONTENT_ROOT`. | **Medio**, pendiente: M-12 |
| TM-39 | Tampering → Elevation of privilege | A1, A7 | Un PR edita lo que el motor instaló y leen los agentes de todo el equipo: una skill en `.claude/skills/`, el bloque de `AGENTS.md` o `.claude/settings.json`, donde un `Bash(*)` en `permissions.allow` le da al agente de cada compañero un shell sin preguntas. | Baja × Crítico = Alto | El lock detecta el cambio (`doctor.py:162-168`) y `exo sync` no lo pisa sin `--force` (`engine.py:360-369`). Desde `378d004`, `exo codeowners` le da al `tech_lead`, además de las specs y `.exo/`, `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.agents/`, `.mcp.json`, `.husky/`, `.pre-commit-config.yaml` y `.gitattributes` (`src/exo/commands/governance.py:60-69`, `:82-91`; test `tests/test_p0.py:64`; `content/packs/core/shared/ci-and-review.md:164`). Es efectivo solo si el proyecto agrega esas líneas y el host exige la revisión de code owners (supuesto S-5); en Azure DevOps, la política del contrato sigue filtrando solo `/specs/*` y `/.exo/*` (`ci-and-review.md:167`). `exo check` todavía no compara lo instalado con el contenido del motor. | **Medio**, pendiente: el resto de M-3 |
| TM-40 | Denial of service (degradación) | A8 | En GitHub Copilot CLI 1.0.114 sobre Windows, un custom agent que declara `tools: … Bash` no tiene shell, aunque la documentación de GitHub dice que `Bash` es alias de `execute`; con `PowerShell` en la lista, sí. Hasta `93fe606`, `sdd-implementer` y `sdd-verifier` declaraban solo `Bash`: apply y verify corrían inline, sin contexto fresco, o un verificador sin shell revisaba sin correr los tests. Lo verificó el coordinador de F8 el 2026-11-24 con dos agentes de prueba. | Alta × Medio = Alto | Desde `59294c9`, los dos declaran también `PowerShell` (`content/packs/sdd/agents/sdd-implementer.md:4`, `content/packs/sdd/agents/sdd-verifier.md:4`), y `exo validate` da error si un subagente lista `Bash` sin `PowerShell` (`src/exo/validate.py:680`, `:687-707`; test `tests/test_validate.py:164`). La CI del proyecto sigue corriendo sus tests y `exo check`. Depende de una versión de Copilot CLI: otra puede cambiar el comportamiento (supuesto S-13). | Bajo |

### 8. `exo update` y `exo sync`

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-41 | Tampering | A4 | Una actualización pisa lo que editó el humano, borra skills que el equipo usa (huérfanas) o lleva un proyecto hacia atrás con un motor viejo. | Media × Alto = Alto | Con conflictos no se escribe nada sin `--force` (`engine.py:360-369`, `:473-474`) y `--force` nunca pisa un archivo del humano (`engine.py:66-70`, `:357-358`); las huérfanas se conservan sin `--prune` (`engine.py:63-65`, `:384-395`) y un renombre conocido se muestra como tal (`src/exo/installer/renames.py:18-21`); `exo update` es vista previa por defecto (`src/exo/installer/update.py:72-79`) y no baja un lock más nuevo sin `--force` (`update.py:66-71`; `src/exo/core/lock.py:16-19`); una config que no se puede usar aborta (`installer/project.py:74-84`); tests en `tests/test_engine.py` y `tests/test_update.py`. | Bajo |
| TM-42 | Elevation of privilege | A1, A4 | Un repo trae un symlink o una junction en una ruta gestionada (por ejemplo `.claude/skills` hacia `~/.ssh` o hacia el `~/.bashrc`) para que `exo sync` escriba o borre fuera del proyecto. | Media × Crítico = Crítico | `join_within` rechaza cualquier componente que sea link (`fsutil.py:218-238`) y `safe_relpath` rechaza absolutas, unidades y `..` (`fsutil.py:175-192`); las rutas del lock se resuelven dentro del proyecto (`lock.py:279-287`); una ruta insegura es conflicto que `--force` no resuelve (`engine.py:325-334`); tests `tests/test_engine.py:265`, `:457`. Queda una carrera: la caché de links supone que el motor es el único que escribe durante la corrida (`fsutil.py:195-215`). | Bajo |
| TM-43 | Tampering, Information disclosure | A4, A9 | Un snapshot armado en `.exo/backups/` (ignorado por git, `generic.py:47-53`) hace que `exo restore` borre o escriba fuera de sus raíces; o un backup de desinstalación deja copia del proyecto fuera del repo. | Baja × Medio = Bajo | El restore valida todo antes de tocar nada: solo archivos regulares, rutas seguras y dentro de las raíces (`src/exo/core/snapshots.py:158-197`, `:323-335`), y antes toma un snapshot del estado actual (`snapshots.py:336`); tests `tests/test_snapshots.py:286`, `:297`. `exo uninstall` no borra la carpeta del motor si es un link (`installer/project.py:331-332`). Los permisos del backup, en TM-27. | Bajo |

### 9. Personas

`persona.json` en la carpeta de datos del usuario (ADR-0018).

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-44 | Elevation of privilege | A6 | Un overlay (por ejemplo `tech-lead`) hace que el agente apruebe un gate escalado o relaje un tier. | Media × Medio = Medio | **Riesgo aceptado** y acotado por el dueño en ADR-0018: un overlay nunca relaja una regla, un gate, un tier ni una aprobación (`docs/adr/0018-overlays-de-persona.md:3`, `:27-30`), y la regla base lo repite (`content/rules/AGENTS.base.md:11`); test `tests/test_persona.py:144`. La aprobación efectiva es del host, no del agente (`ci-and-review.md:160-168`). | Bajo |
| TM-45 | Tampering | A9 | Un proceso local cambia `persona.json` para que el agente lea otro archivo. | Baja × Bajo = Bajo | El rol sale de una lista cerrada y un archivo dañado es un error (`src/exo/persona.py:59-61`, `:67-68`); la ruta del overlay se arma con el rol, sin entrada libre (`persona.py:32-34`); vive fuera del repo (ADR-0018, `:34`) y ninguna variable de entorno decide (ADR-0018, `:37`). | Bajo |
| TM-46 | Tampering | A7 | Un PR edita `.exo/shared/personas/<rol>.md` para meter instrucciones que el agente sigue "por encima de las reglas". | Baja × Medio = Bajo | Es un contrato instalado: está en el lock (`generic.py:58-61`) y `.exo/` es del `tech_lead` por CODEOWNERS (`commands/governance.py:82-91`). `exo validate` no le pasa el chequeo de instrucciones (TM-38). | Bajo (M-12) |

### 10. El runner de evals

`tests/_skill_evals.py` y `tests/test_skill_evals.py`, con agentes reales.

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-47 | Elevation of privilege | A1 | El agente de un eval corre con tools permitidas sin preguntar, entre ellas `Bash(git:*)`, `Bash(exo:*)`, `Edit` y `Write` (`tests/test_skill_evals.py:45-49`): un fixture o un pedido con instrucciones lo lleva a `git config --global`, a un `git push` o a `exo gate publish --approve-command` con un comando (TM-21). | Baja × Medio = Bajo | Desde `d94f6c0`, `GIT_CONFIG_GLOBAL` apunta a un archivo de la carpeta temporal y sin config del sistema (`tests/_skill_evals.py:343-350`; test `tests/test_skill_evals_schema.py:207`), y `git push` queda denegado (`_skill_evals.py:329-331`); en Copilot, el runner de escenarios también lo deniega (`tests/_agents.py:39-41`). Los fixtures y los `evals.json` son sintéticos y viven en este repo (`AGENTS.md`, sección Tests); el proyecto es una copia temporal; las rutas de `setup` no salen del proyecto (`_skill_evals.py:178-203`); `agent_e2e` queda fuera de la suite y de la CI (`pyproject.toml:72-79`). Los dos runners siguen permitiendo `exo:*` entero (`test_skill_evals.py:45-49`; `_agents.py:39`), con las aprobaciones en la carpeta temporal y fixtures sin `publish_command`. | Bajo |
| TM-48 | Information disclosure, Tampering | A5, A7 | La corrida toma la config de usuario del agente (skills, hooks, MCP, `CLAUDE.md`) o la memoria real de la persona, y el resultado no mide lo que dice, o el eval escribe en esa memoria. | Media × Medio = Medio | `--setting-sources project,local --strict-mcp-config` (`_skill_evals.py:72-74`, `:316-334`); `EXO_DATA_DIR` y `EXO_MEMORY_DB` en la carpeta temporal (`_skill_evals.py:337-342`); el workspace no es confiable y el `permissions.allow` del proyecto no cuenta (`test_skill_evals.py:13-17`). En Copilot, un `COPILOT_HOME` propio por corrida (`tests/_agents.py:124-134`). | Bajo |
| TM-49 | Denial of service | A8 | Una corrida se cuelga o consume turnos y costo sin límite. | Baja × Bajo = Bajo | 40 turnos y 1800 s por defecto (`test_skill_evals.py:50-51`); solo a mano (`pyproject.toml:72-79`). | Bajo |

### 11. Variables de entorno

| ID | STRIDE | Activo | Escenario | P × I | Mitigación existente o riesgo aceptado | Residual |
|---|---|---|---|---|---|---|
| TM-50 | Tampering | A1, A5 | Las variables `EXO_*` cambian dónde vive la memoria (`EXO_DATA_DIR`, `EXO_MEMORY_DB`: `paths.py:57-59`, `:74-76`), qué contenido se instala (`EXO_CONTENT_ROOT`: `content.py:29-35`), qué corre el hook (`EXO_HOOK_CMD`: `githooks.py:36`), adónde van los embeddings remotos y con qué clave (`EXO_EMBEDDINGS_URL`, `EXO_EMBEDDINGS_API_KEY`: `http.py:21-22`), y de dónde instala el instalador (`EXO_REPO_URL`, `EXO_REF`, `EXO_INSTALL_*`: `install.sh:48-55`, `install.ps1:56-65`). Una herramienta del proyecto que carga variables (un `.env`, un devcontainer) podría fijarlas. | Baja × Bajo = Bajo | Ninguna decide un control de seguridad (ADR-0006, `:44`; ADR-0018, `:37`): un proveedor remoto igual exige `--allow-remote` guardado en la base (`embeddings/__init__.py:109-115`); las URLs y los refs del instalador igual se validan (TM-2); la detección de agentes por variables no habilita nada (`src/exo/adapters/detect.py:100-106`). Quien fija el entorno de la persona ya corre código como ella (supuesto S-6). | Bajo |

## Casos de abuso

- Como colaborador con escritura en el repo del motor, o con la cuenta del dueño, cambio `install.sh` en `main` para que cada `curl … | sh` corra mi código (TM-1), o empujo un tag y edito el release con un wheel y un `SHA256SUMS` míos (TM-4, TM-5, TM-12).
- Como mantenedor de una action de terceros, muevo su tag para correr en el job del release con `contents: write` o con el OIDC de PyPI (TM-10), o publico una versión de `build` o de `hatchling` que altera el wheel (TM-11).
- Como autor de un PR en un proyecto, cambio `.exo/githooks/pre-commit` y espero que alguien haga checkout de mi rama y commitee (TM-16), o vacío los gates de mi tier y me agrego un waiver (TM-19).
- Como autor de un PR de un fork, pongo un `review.publish_command` que manda el token del pipeline a mi servidor, si la CI publica gates con escritura (TM-20).
- Como autor de un comentario en el código, de un ticket o de una página que lee el agente, le pido que corra `exo init --yes --publish-command …` y `exo gate publish`, que en `93fe606` no pedían permiso y ahora sí (TM-21), o que lea la memoria de otro proyecto con `mem_get` (TM-23), o que guarde una "convención" que lo siga guiando en otras sesiones (TM-30).
- Como autor de un PR, agrego `Bash(*)` a `.claude/settings.json` o reescribo una skill instalada para el agente de todo el equipo (TM-39).
- Como autor de código que alguien adopta con la ingeniería inversa, escribo un comentario dirigido a la IA para que modifique el código o mienta en el reporte (TM-33, TM-34).
- Como servicio de embeddings, o como alguien que controla su redirección, recibo la API key de la persona en otro origen (TM-29).
- Como otro usuario de una máquina Linux compartida, leo `memory.db` y los backups de desinstalación (TM-27).
- Como autor de un repo con links, apunto `.claude/skills` fuera del proyecto para que `exo sync` escriba ahí (TM-42).

## Resumen por residual

En el formato del gate `threat_model` de la skill: la severidad es el residual, y la regla es la categoría STRIDE con su categoría OWASP Top 10:2025 y su CWE (`owasp-2025.md`). No queda ningún residual Crítico: TM-21 bajó a Bajo con M-1.

| Severidad | File:line | Hallazgo | Rule/OWASP |
|---|---|---|---|
| High | install.sh:5 | TM-1: el script por pipe sale de `main`, sin nada que fije su contenido | Tampering, A08:2025 Software or Data Integrity Failures, CWE-494 |
| High | install.sh:169 | TM-4: `SHA256SUMS` del mismo release: integridad sin autenticidad | Spoofing, A08:2025 Software or Data Integrity Failures, CWE-345 |
| High | install.sh:220 | TM-5: uv y git sobre un tag que se puede mover, sin checksum | Tampering, A08:2025 Software or Data Integrity Failures, CWE-494 |
| High | .github/workflows/release.yml:61 | TM-11: `build`, `twine` y `hatchling` sin versión fija ni hashes | Tampering, A03:2025 Software Supply Chain Failures, CWE-1357 |
| High | .github/workflows/release.yml:92 | TM-12: un tag `v*` crea el release de GitHub sin aprobación | Elevation of privilege, A01:2025 Broken Access Control, CWE-862 |
| High | src/exo/governance/githooks.py:34 | TM-16: `core.hooksPath` apunta a hooks versionados que cambia un PR; CODEOWNERS cubre lo que llega a `main`, no el checkout de una rama sin revisar | Elevation of privilege, A08:2025 Software or Data Integrity Failures, CWE-829 |
| High | src/exo/governance/gates.py:133 | TM-20: en la CI, `publish_command` de la rama del PR corre en un shell si el pipeline lo aprueba | Elevation of privilege, A05:2025 Injection, CWE-78 |
| High | src/exo/memory/exchange.py:34 | TM-26: secretos en la memoria y export sin redactar (aceptado, ADR-0009) | Information disclosure, A06:2025 Insecure Design, CWE-256 |
| Medium | src/exo/sdd/check.py:417 | TM-19: la rama del PR decide la config de su propio gate | Tampering, A01:2025 Broken Access Control, CWE-863 |
| Medium | src/exo/tools/memory.py:154 | TM-23: `mem_get` y `mem_delete` cruzan proyectos | Information disclosure, A01:2025 Broken Access Control, CWE-639 |
| Medium | content/rules/AGENTS.base.md:48 | TM-30: la memoria entra al contexto como instrucción, sin procedencia | Tampering, A05:2025 Injection, CWE-1427 (closest: CWE-94) |
| Medium | src/exo/discovery/pipeline.py:83 | TM-33: el solo lectura se detecta, no se impide | Tampering, A06:2025 Insecure Design, CWE-269 |
| Medium | src/exo/discovery/units.py:121 | TM-34: prompt injection desde el código analizado | Elevation of privilege, A05:2025 Injection, CWE-1427 (closest: CWE-94) |
| Medium | src/exo/discovery/files.py:492 | TM-35: un secreto leído llega al modelo (aceptado, ADR-0015) | Information disclosure, A01:2025 Broken Access Control, CWE-200 |
| Medium | src/exo/validate.py:561 | TM-38: el chequeo de instrucciones no cubre contratos, overlays ni reglas | Tampering, A08:2025 Software or Data Integrity Failures, CWE-829 |
| Medium | src/exo/commands/governance.py:60 | TM-39: CODEOWNERS ya cubre skills, `AGENTS.md` y `.claude/`, pero depende del host y `exo check` no compara lo instalado | Elevation of privilege, A01:2025 Broken Access Control, CWE-862 |
| Low | install.sh:99 | TM-2: `EXO_REPO_URL` y `EXO_REF` validados | Tampering, A08:2025 Software or Data Integrity Failures, CWE-829 |
| Low | install.sh:129 | TM-3: ninguna descarga sigue un salto a otro protocolo, con test; con https, sin curl no se baja | Tampering, A04:2025 Cryptographic Failures, CWE-319 |
| Low | install.sh:222 | TM-6: un release sin SHA256SUMS se detiene; una rama o un commit van por git | Tampering, A10:2025 Mishandling of Exceptional Conditions, CWE-636 |
| Low | install.sh:297 | TM-7: no pisa otro `exo` | Spoofing, A03:2025 Software Supply Chain Failures, CWE-1357 |
| Low | uninstall.ps1:91 | TM-8: la carpeta de datos con -LiteralPath, con test | Tampering, A05:2025 Injection, CWE-20 |
| Low | tests/_remote.py:120 | TM-9: el remoto simulado sirve lo sin trackear en loopback | Information disclosure, A01:2025 Broken Access Control, CWE-200 |
| Low | .github/workflows/release.yml:152 | TM-10: actions fijadas por SHA, con Dependabot y test | Tampering, A03:2025 Software Supply Chain Failures, CWE-1357 |
| Low | .github/workflows/release.yml:50 | TM-13: expresiones por `env:`, con test | Tampering, A05:2025 Injection, CWE-78 |
| Low | .github/workflows/ci.yml:4 | TM-14: PRs de forks con token de solo lectura | Elevation of privilege, A06:2025 Insecure Design, CWE-269 |
| Low | .github/workflows/release.yml:154 | TM-15: TestPyPI sin reglas | Tampering, A01:2025 Broken Access Control, CWE-862 |
| Low | src/exo/governance/githooks.py:57 | TM-17: `--no-verify` y hooks sin `exo` (aceptado, ADR-0014) | Repudiation, A06:2025 Insecure Design, CWE-602 |
| Low | src/exo/governance/githooks.py:54 | TM-18: `EXO_HOOK_CMD` | Tampering, A08:2025 Software or Data Integrity Failures, CWE-829 |
| Low | src/exo/adapters/claude_code.py:63 | TM-21: el permiso del agente cubre solo los subcomandos de las skills, y `gate publish` corre solo comandos aprobados | Elevation of privilege, A06:2025 Insecure Design, CWE-269 |
| Low | src/exo/tools/validation.py:43 | TM-22: validación S2 de las tools | Tampering, A01:2025 Broken Access Control, CWE-22 |
| Low | src/exo/tools/memory.py:305 | TM-24: tools que borran o mezclan memoria | Tampering, A01:2025 Broken Access Control, CWE-862 |
| Low | src/exo/mcp/server.py:142 | TM-25: stdout del protocolo y líneas sin límite | Denial of service, A06:2025 Insecure Design, CWE-770 |
| Low | src/exo/paths.py:23 | TM-27: datos de usuario en 0700 y 0600 en POSIX, con aviso de `exo doctor` | Information disclosure, A01:2025 Broken Access Control, CWE-922 |
| Low | src/exo/memory/embeddings/__init__.py:109 | TM-28: embeddings remotos solo con `--allow-remote` en la base | Information disclosure, A01:2025 Broken Access Control, CWE-200 |
| Low | src/exo/memory/embeddings/http.py:26 | TM-29: sin redirecciones y con https obligatorio para la API key | Information disclosure, A01:2025 Broken Access Control, CWE-200 |
| Low | src/exo/memory/exchange.py:106 | TM-31: import validado y límites de entrada | Tampering, A05:2025 Injection, CWE-20 |
| Low | src/exo/memory/embeddings/static.py:66 | TM-32: modelos sin revisión fija | Tampering, A08:2025 Software or Data Integrity Failures, CWE-494 |
| Low | src/exo/discovery/files.py:407 | TM-36: sin links y con límite de tamaño | Elevation of privilege, A01:2025 Broken Access Control, CWE-59 |
| Low | src/exo/discovery/pipeline.py:94 | TM-37: git en una carpeta que no es un clon | Elevation of privilege, A08:2025 Software or Data Integrity Failures, CWE-829 |
| Low | content/packs/sdd/agents/sdd-verifier.md:4 | TM-40: los subagentes con shell declaran `PowerShell`, y `exo validate` lo exige | Denial of service, A10:2025 Mishandling of Exceptional Conditions, CWE-755 |
| Low | src/exo/installer/engine.py:360 | TM-41: conflictos, huérfanas y versión del lock | Tampering, A02:2025 Security Misconfiguration, CWE-1188 |
| Low | src/exo/core/fsutil.py:218 | TM-42: rutas por links | Elevation of privilege, A01:2025 Broken Access Control, CWE-59 |
| Low | src/exo/core/snapshots.py:323 | TM-43: restore y backups | Tampering, A01:2025 Broken Access Control, CWE-22 |
| Low | content/rules/AGENTS.base.md:11 | TM-44: un overlay nunca relaja (aceptado, ADR-0018) | Elevation of privilege, A06:2025 Insecure Design, CWE-602 |
| Low | src/exo/persona.py:59 | TM-45: rol de lista cerrada | Tampering, A05:2025 Injection, CWE-20 |
| Low | src/exo/adapters/generic.py:58 | TM-46: overlays versionados en `.exo/` | Tampering, A08:2025 Software or Data Integrity Failures, CWE-829 |
| Low | tests/test_skill_evals.py:45 | TM-47: tools permitidas en los evals, con la config global de git aislada y sin `git push` | Elevation of privilege, A06:2025 Insecure Design, CWE-269 |
| Low | tests/_skill_evals.py:74 | TM-48: aislamiento de la config del agente y de la memoria | Information disclosure, A01:2025 Broken Access Control, CWE-200 |
| Low | tests/test_skill_evals.py:50 | TM-49: turnos y timeout de los evals | Denial of service, A06:2025 Insecure Design, CWE-770 |
| Low | src/exo/paths.py:57 | TM-50: variables `EXO_*` | Tampering, A05:2025 Injection, CWE-20 |

## Mitigaciones propuestas

Ordenadas por el residual que bajaban en `93fe606`. Cada una dice si está **hecha** (con su commit) o sigue **propuesta**.

### Crítico

**M-1. El agente no ejecuta comandos configurados sin una persona (TM-21, TM-20).** **Hecha** en lo principal:

1. **Hecha (`02472cb`):** el permiso del adaptador de Claude Code cubre solo `AGENT_COMMANDS`, los subcomandos que las skills corren solas (`src/exo/adapters/claude_code.py:37-60`, `:63-67`). Lo que cambia la instalación, borra, reindexa o exporta memoria, o ejecuta un comando configurado queda afuera, y un test lo fija (`tests/test_adapters.py:109`). `exo sync` reemplaza `Bash(exo:*)` en los proyectos instalados (`tests/test_adapters.py:126`).
2. **Hecha (`c46eac6`):** `exo gate publish` corre solo un comando aprobado en esa máquina. El SHA256 del texto exacto va a `approved-commands.json`, en la carpeta de datos (`src/exo/governance/approvals.py:58-73`); con TTY muestra el comando y pregunta, sin TTY se niega, y `--approve-command` lo aprueba (`src/exo/commands/gate.py:34-38`, `:63-70`; `src/exo/governance/gates.py:114-118`). El contrato explica que en la CI el flag va solo en un pipeline confiable (`content/packs/core/shared/ci-and-review.md:97`).
3. **Propuesta:** que `exo init` y `exo sync` avisen cuando cambia `review.publish_command`.
4. **Hecha (`0c23b79`):** `--approve-command` recibe el texto exacto del comando (`exo gate publish --approve-command '<comando>'`) y aprueba solo si coincide con `review.publish_command`; si no, no aprueba ni corre nada (`src/exo/commands/gate.py`, `_publish`). El pedido de permiso del agente muestra lo que se aprueba, y en la CI el pipeline escribe el comando que acepta: una rama que cambia `publish_command` no coincide (`content/packs/core/shared/ci-and-review.md`, sección D). Esto baja también TM-20 cuando el pipeline sigue el contrato.

### Alto

**M-2. La config de seguridad sale de la rama base (TM-19, TM-20).** **Propuesta**; es lo que falta para TM-20 en la CI.
- `exo check --base <ref>` compara con la base `governance.gates`, `governance.protected_branches`, `governance.githooks`, `data_protection.pii`, `review.publish_command` y `waivers.json`. Si el PR los debilita, da un hallazgo que pide al `tech_lead`, como un gate escalado.
- `exo gate publish --base <ref>` usa el `publish_command` de la base, nunca el de la rama.

**M-3. Lo instalado no cambia sin revisión (TM-16, TM-39).** **Hecha en parte:**
- **Hecha (`378d004`):** `exo codeowners` suma lo que leen los agentes y lo que ejecuta git: `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.agents/`, `.mcp.json`, `.husky/`, `.pre-commit-config.yaml` y `.gitattributes` (`src/exo/commands/governance.py:60-69`, `:82-91`; test `tests/test_p0.py:64`; `content/packs/core/shared/ci-and-review.md:164`).
- **Propuesta:** la política de Azure DevOps del contrato filtra solo `/specs/*` y `/.exo/*` (`ci-and-review.md:167`); tiene que nombrar las mismas rutas.
- **Propuesta:** `exo check --base` falla si un archivo gestionado del lock difiere de lo que esta versión del motor generaría: hooks, skills, subagentes, contratos y los ítems de `permissions.allow`. Así el hook o la skill alterados no llegan a `main`, aunque el host no exija code owners.
- **Propuesta, con un ADR** (cambia ADR-0014): los scripts de los hooks se escriben en una carpeta no versionada del clon (por ejemplo `.git/exo-hooks/`, que `exo sync` regenera) y `core.hooksPath` apunta ahí. Es lo único que cubre el checkout de una rama sin revisar.

**M-4. Distribución con autenticidad (TM-1, TM-4, TM-5, TM-12).** **Propuesta.** Fijar el motor a un tag en los ejemplos de CI del contrato ya está hecho (`content/packs/core/shared/ci-and-review.md:20`, `:26`).
- **Rulesets en GitHub:** `main` con PR obligatorio, sin force-push y sin borrado; los tags `v*` los crea solo el dueño, sin moverlos ni borrarlos.
- **Releases inmutables** de GitHub, para que un asset publicado no se pueda reemplazar.
- **Atestaciones del build:** `actions/attest-build-provenance` en `release.yml` sobre `dist/*`, y en el README `gh attestation verify <wheel> --repo <repo>`. PyPI ya recibe atestaciones con trusted publishing y la action de pypa.
- **Instalación fijada:** el README documenta la URL del instalador por tag (`…/<tag>/install.sh`), que no cambia cuando cambia `main`.
- **El job `github-release`** usa un environment con revisores, como el de PyPI.

**M-5. Cadena de build fijada (TM-10, TM-11).** **Hecha en parte:**
- **Hecha (`b368bc8`):** actions por SHA, con la versión en un comentario, incluida `pypa/gh-action-pypi-publish` (`.github/workflows/release.yml:152`), y Dependabot para `github-actions` (`.github/dependabot.yml:5-12`); test `tests/test_workflows.py:75`, `:92`.
- **Propuesta:** `build`, `twine` y `hatchling` desde un archivo de requisitos con `--require-hashes` (TM-11, residual Alto).
- **Propuesta:** para la CI, lo mismo con los extras de desarrollo, aunque el impacto es menor.

**M-6. wget no sigue redirecciones a otro protocolo (TM-3).** **Descartada (`67d4b8a`):** con https se exige curl; seguir los saltos a mano con wget depende de la salida de `wget -S`, que cambia entre GNU wget, wget2 y busybox, y baja el último salto dos veces. La propuesta original era: En `install.sh`, seguir las redirecciones a mano y verificar cada salto. `redirect_of` ya existe; el costo es bajar el último salto dos veces:

```sh
fetch() {
    if command -v curl >/dev/null 2>&1; then
        curl --proto "=$SCHEME" --proto-redir "=$SCHEME" -fsSL -o "$2" "$1"
        return
    fi
    # wget sigue redirecciones a cualquier protocolo: se siguen a mano, de a una.
    url=$1
    hops=0
    while next=$(redirect_of "$url") && [ -n "$next" ]; do
        case "$next" in
            "$SCHEME"://*) url=$next ;;
            *) die "$url redirected to $next, which is not $SCHEME; refusing it." ;;
        esac
        hops=$((hops + 1))
        [ "$hops" -le 10 ] || die "Too many redirects from $1."
    done
    wget -q --max-redirect=0 -O "$2" "$url"
}
```

Si no, exigir curl cuando `SCHEME` es `https`.

### Medio

**M-7. Aviso al exportar memoria con secretos (TM-26).** **Propuesta.** Es opcional y decide el dueño, porque ADR-0009 descartó el guard: `exo mem export` corre `core/secrets.py` sobre lo que exporta y **avisa** por stderr qué observaciones parecen tener un secreto, sin redactar ni frenar. Si se adopta, va como `D-xx` con opciones.

**M-8. La memoria del agente, acotada y marcada como dato (TM-23, TM-30).** **Propuesta.**
- `mem_get` y `mem_delete` devuelven `NotFound` para una observación de otro proyecto que no sea `personal`, salvo `all_projects`.
- El servidor MCP solo acepta `all_projects` si se lanzó con `exo mcp --all-projects`, que decide la persona en la config del agente.
- `exo mem context` y `mem_get` marcan el contenido como notas, no instrucciones, y dicen de qué proyecto, sesión y agente vino.

**M-9. Permisos privados en POSIX (TM-27).** **Hecha (`2634c05`):**
- `paths.private_dir` crea en `0700` las carpetas que faltan, sin tocar las que ya existen (`src/exo/paths.py:18-45`).
- La base y sus `-wal` y `-shm` quedan en `0600` (`src/exo/memory/db.py:70-94`).
- `persona.json`, `approved-commands.json`, los backups de desinstalación y `exo mem export --output` se escriben en `0600` (`src/exo/persona.py:71-72`; `src/exo/governance/approvals.py:72-73`; `src/exo/installer/project.py:316-317`; `src/exo/commands/memory.py:177`).
- `exo doctor` suma el chequeo `data-dir` (`src/exo/doctor.py:364-380`).
- Tests en `tests/test_private_data.py`.

La carpeta que crea `install.sh` sin uv queda con el `umask` (`install.sh:307`, `:324`); `exo doctor` lo avisa.

**M-10. La API key no sigue redirecciones ni viaja en claro (TM-29).** **Hecha (`28ae30e`):**
- `_NoRedirect` en los dos openers, con un error que dice adónde redirigía (`src/exo/memory/embeddings/http.py:26-38`, `:55-65`).
- `https://` obligatorio fuera de esta máquina (`http.py:133-139`).
- Tests `tests/test_memory_providers.py:127`, `:146`.

**M-11. Solo lectura verificable en la ingeniería inversa (TM-33, TM-34).** **Propuesta.**
- `exo discover status` compara también los commits desde el inicio de la adopción, no solo `git status`: el plan guarda el commit base fuera de los JSON deterministas.
- La extracción inline (sin subagentes) se informa como degradación en el reporte de cobertura.

**M-12. El chequeo de instrucciones cubre todo lo que lee el agente (TM-38, TM-46).** **Propuesta.**
- `check_shared` y `check_rules` de `src/exo/validate.py` llaman a `check_instructions`, como `check_skill`.
- Hoy eso daría una advertencia legítima en `content/packs/discovery/shared/discovery-contract.md:34`, que describe el ataque; hace falta decidir si se acepta como advertencia o si se suma una marca de excepción por línea.
- `exo sync` corre `exo validate` sobre `EXO_CONTENT_ROOT` y no instala con errores.

**M-13. Workflows sin inyección, con test (TM-13).** **Hecha (`b368bc8`):** los tests fallan si un `run:` contiene `${{` (`tests/test_workflows.py:60`), si un workflow usa `pull_request_target` (`tests/test_workflows.py:67`), si un `uses:` no va por SHA con su versión (`tests/test_workflows.py:75`) o si falta Dependabot (`tests/test_workflows.py:92`).

**M-14. Test de redirección en los instaladores (TM-3).** **Hecha (`67d4b8a`).** En PowerShell, además, cada salto se verifica antes de pedirlo. El remoto simulado responde `302` desde `http://127.0.0.1` hacia un destino `https://`: con `--proto-redir =http` y con el chequeo de PowerShell la descarga tiene que fallar.

### Bajo

**M-15. `-LiteralPath` en `uninstall.ps1` (TM-8).** **Hecha (`b24d6de`),** también en `install.ps1:337`:

```powershell
    $Venv = Join-Path $DataDir 'venv'
    if (Test-Path -LiteralPath $Venv) {
        Remove-Item -LiteralPath $Venv -Recurse -Force
        $removed = $true
    }
```

**M-16. Sin fallback silencioso (TM-6).** **Hecha (`0c60bc5`),** con `v` y un dígito en lugar de `v*`. Si el ref tiene forma de release (`v*`) y bajar `SHA256SUMS` falla, el instalador se detiene con un mensaje accionable en vez de pasar a git; una rama o un commit siguen yendo por git.

**M-17. Evals sin tocar la config global (TM-47).** **Hecha (`d94f6c0`):**
- `runner_env` fija `GIT_CONFIG_GLOBAL` a un archivo de la carpeta temporal y apaga la config del sistema (`tests/_skill_evals.py:343-350`; test `tests/test_skill_evals_schema.py:207`).
- `git push` queda denegado (`tests/_skill_evals.py:329-331`), como en el runner de escenarios (`tests/_agents.py:41`).
- **Propuesta:** acotar el `exo:*` de los dos runners (`tests/test_skill_evals.py:45-49`, `tests/_agents.py:39`) a `AGENT_COMMANDS`, para que los evals midan lo mismo que ve el agente en un proyecto.

**M-18. Protocolo MCP blindado (TM-25).** **Propuesta.**
- Durante cada tool, el descriptor 1 apunta a stderr a nivel del sistema (`os.dup2`), no solo `sys.stdout`.
- `serve` corta una línea de más de 10 MB con un `PARSE_ERROR`.

**M-19. Modelos con revisión fija (TM-32).** **Propuesta.** `snapshot_download(..., revision=<sha>)` con la revisión registrada por modelo por defecto, y el hash de los archivos bajados en `meta`.

## Supuestos

- **S-1.** La cuenta de GitHub del dueño usa segundo factor, y hoy es la única con escritura en el repo del motor.
- **S-2.** No hay rulesets que protejan `main` ni los tags `v*` en el repo del motor; no se ve desde el código. Si existen, TM-1, TM-5 y TM-12 bajan de probabilidad, no de impacto.
- **S-3.** El dueño configuró el environment `pypi` con revisores y el patrón de tags `v*`, como indica `release.yml:12-15`; no se ve desde el repo.
- **S-4.** GitHub (raw, releases y el almacenamiento de assets) responde solo por https y redirige solo a https.
- **S-5.** Cada proyecto corre `exo check --base` como check obligatorio de la protección de rama (`ci-and-review.md:160-168`). No corre `exo gate publish` con un token de escritura en PRs de forks ni en `pull_request_target` (`ci-and-review.md:98`).
- **S-6.** La máquina y la cuenta de la persona no están comprometidas: quien controla su entorno o sus archivos ya corre código como ella. Es la base de TM-2, TM-18, TM-45 y TM-50.
- **S-7.** El agente es un llamador a medias confiable: puede seguir instrucciones escondidas en lo que lee. Su sistema de permisos funciona como lo documenta su fabricante: en Claude Code, las reglas del proyecto valen solo con el workspace confiable; Copilot pide confirmación sin regla.
- **S-8.** El proveedor del modelo procesa el código leído bajo el acuerdo de la organización que adopta el motor. Es lo que hace aceptable el residual de TM-35.
- **S-9.** Los proyectos analizados son clones: su `.git/config` es local y lo controla la persona.
- **S-10.** En Windows, `%LOCALAPPDATA%` tiene permisos por usuario; en macOS, `~/Library` es `0700`.
- **S-11.** Los fixtures y los `evals.json` son sintéticos y pasan por revisión, como el resto del repo.
- **S-12.** Las dependencias opcionales (`sqlite-vec`, `fastembed`, `model2vec`, `huggingface_hub`) son tan confiables como PyPI y se instalan solo con los extras.
- **S-13.** El comportamiento de Copilot CLI 1.0.114 en Windows (TM-40) es el que verificó el coordinador de F8 el 2026-11-24; la documentación de GitHub dice otra cosa y puede cambiar con la versión.
