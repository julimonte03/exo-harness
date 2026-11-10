# Progreso de construcción

**Fase activa:** F3 (pendiente: aprobar su plan; D-07 y D-08 los decide el experimento de la fase y D-12 sigue abierta).

Una fase está **terminada** cuando: todos sus criterios de aceptación pasaron con el comando exacto, la CI está verde en los tres sistemas operativos y el PR de la fase está mergeado.

**Mientras no haya repo remoto** (decisión del dueño, 2026-10-30): la fase se cierra en local. La suite y el lint se corren en Windows y en Linux (Ubuntu en WSL, sobre un clon limpio), y la rama se mergea a `main` con `git merge --no-ff`, sin push. La CI (Azure Pipelines, `azure-pipelines.yml`, incluido macOS) y el PR quedan diferidos (ADR-0008). Cuando exista el remoto, se suben `main` y las ramas, y se verifica la CI de cada fase cerrada así.

## Estado por fase

| Fase | Estado | Rama / PR | Inicio | Cierre | Notas |
|---|---|---|---|---|---|
| F0 Fundaciones | Terminada (local; CI diferida) | `feat/F0-fundaciones`, mergeada a `main` en local, sin PR | 2026-10-29 | 2026-10-30 | Criterios 1, 2, 4–7 OK. Criterio 3: Windows y Linux en local OK; macOS y Azure Pipelines diferidos hasta tener remoto (ADR-0008) |
| F1 Núcleo | Terminada (local; CI diferida) | `feat/F1-nucleo`, mergeada a `main` en local, sin PR | 2026-10-30 | 2026-10-30 | Criterios 1–8 OK en Windows (3.14 y 3.10) y Linux (WSL). D-23 → ADR-0005 |
| F2 Adaptadores + instalador | Terminada (local; CI diferida) | `feat/F2-adaptadores`, mergeada a `main` en local, sin PR | 2026-10-30 | 2026-11-07 | Criterios 1–7 OK en Windows (3.14 y 3.10) y Linux (WSL). Criterio 1 sin macOS ni Azure. Criterio 8: Claude Code OK, Copilot pendiente (checklist manual). D-04 → ADR-0006, D-05/D-06 → ADR-0007, D-16 → ADR-0008 |
| F3 Memoria v2 | Pendiente | | | | |
| F4 Ciclo SDD | Pendiente | | | | |
| F5 Gobierno y gates | Pendiente | | | | |
| F6 Ingeniería inversa | Pendiente | | | | |
| F7 Packs | Pendiente | | | | |
| F8 Endurecimiento + v1.0 | Pendiente | | | | |

Estados: `Pendiente` · `En curso` · `Bloqueada (D-xx)` · `Terminada`.

## Registro de criterios de aceptación

Copiar este bloque por cada fase al cerrarla.

```markdown
### F<n> — <nombre> — <fecha>

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | ... | `...` | OK / NOK + detalle |

Checklist manual (si aplica): docs/checklists/F<n>-*.md — resultado y observaciones.
Decisiones tomadas durante la fase: D-xx → ADR-xxxx.
Desvíos respecto del plan y por qué:
```

### F0 — Fundaciones — 2026-10-29

Entorno: Windows 11, venv `.venv` con Python 3.14.5. La suite también se corrió con Python 3.10.20 (venv con `uv`) y en Linux: Ubuntu 24.04 en WSL2, Python 3.12.3, clon limpio en `/tmp`, el 2026-10-30.

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | El paquete se instala y responde | `pip install -e ".[dev]"`; `exo --version`; `python -m exo --version` | OK: los dos imprimen `exo 0.0.1` |
| 2 | Tests y lint verdes | `pytest`; `ruff check .` | OK: 8 passed, cobertura 96.55 % (umbral 80 %); ruff "All checks passed!" |
| 3 | CI verde en los 3 SO | Sin remoto: `pip install -e ".[dev]"`, `exo --version`, `python -m exo --version`, `pytest`, `ruff check .` en Windows y en Ubuntu (WSL) | **Parcial**: Windows OK (3.14.5 y 3.10.20) y Linux OK (3.12.3; 8 passed, 96.55 %, versión `exo 0.0.1` por las dos vías). macOS y el run de GitHub Actions (`.github/workflows/ci.yml`) quedan diferidos hasta tener remoto |
| 4 | Nombre centralizado | `pytest --no-cov tests/test_meta.py` | OK: 3 passed. Prueba a mano: un módulo temporal con `".exo/config.json"` hace fallar el test con `_tmp_probe.py:1`, y se revirtió |
| 5 | Matriz de agentes completa | Revisión de `docs/agent-matrix.md` (script que cuenta las filas 1–8 por tabla) | OK: 8 tablas (Claude Code, Copilot CLI, VS Code, cloud agent, Cursor, Codex, Gemini, Devin), cada una con las filas 1–8, URL o `[No verificado]` |
| 6 | Decisiones registradas | `ls docs/adr`; `grep "Decidida" docs/plan/04-DECISIONES.md` | OK: ADR-0001 a 0004; D-01, D-02, D-03 y D-15 decididas |
| 7 | Diferencias con el plan anotadas | `git diff --stat main -- docs/plan/03-MATRIZ-AGENTES.md` | OK: 03 actualizado (86+/43−) con las contradicciones encontradas |

Checklist manual: no aplica en F0. Verificación de reglas: una sesión nueva de Claude Code (`claude -p`) carga `CLAUDE.md` y `AGENTS.md` vía `@AGENTS.md`.

Decisiones tomadas durante la fase:
- D-01 → ADR-0001 (`exo`, con mitigaciones por la colisión con exo-explore/exo).
- D-02 y D-15 → ADR-0002.
- Principio 1 → ADR-0003.
- D-03 → ADR-0004 (gentle-ai y Engram son MIT; sus nombres son marcas ™).
- Nueva **D-23** (abierta): MCP bloqueado por política de la organización.
- Hallazgos de producto anotados en D-04: Windsurf → Devin, Gemini → Antigravity, dos harness en VS Code.

Desvíos respecto del plan y por qué:
- Distribución `exo-harness` (no `exo`): el nombre `exo` está tomado en PyPI.
- La carpeta de datos de usuario es `exo-harness` y no `~/.exo`, porque exo-explore/exo la usa y la borra al desinstalarse (ADR-0001). Afecta a F3.
- `_meta.py` suma `DIST_NAME` y `USER_DIR_NAME` a los campos pedidos.
- La prueba empírica cubrió solo Claude Code, el único agente instalado. Copilot no tiene licencia confirmada en esta máquina.
- `.gitattributes` fuerza LF en todo el repo y deja la transcripción de referencia byte a byte.
- `AGENTS.md` de la raíz difiere de su plantilla `docs/plan/repo-raiz/AGENTS.md`: además del nombre `exo`, agrega la nota de APIs 3.11+, cobertura de 80 % en F0 y `pytest --no-cov`. La plantilla queda como en el plan original.
- Revisión final con contexto fresco (subagente). Se corrigieron: la contradicción del ADR-0003 con la matriz, el test de nombres que podía pasar sin revisar nada, fuentes faltantes, la salvedad de Claude Code ≥ 2.1.281 y la numeración de invariantes. También se agregó un test de metadata de la distribución y se ajustó el CI (cancelación solo en PR, timeout, cache de pip).
- **Cierre sin remoto** (decisión del dueño, 2026-10-30): F0 se mergea a `main` en local con `--no-ff`, sin PR, y el criterio 3 queda parcial (ver la nota al principio de este archivo).

### F1 — Núcleo determinista — 2026-10-30

Entorno: Windows 11 con Python 3.14.5 (venv `.venv`) y 3.10.20 (venv con `uv`); Linux Ubuntu 24.04 en WSL2 con Python 3.12.3 (clon limpio). Resultados: Windows 513 passed y 5 skipped (POSIX-only); Python 3.10, 513 passed; Linux, 518 passed. Cobertura 95,7 %.

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Suite verde con cobertura ≥ 85 % | `pytest --cov=src/exo --cov-fail-under=85` | OK: 513 passed, cobertura 95,78 % |
| 2 | Fitness reproduce todas las reglas | `exo fitness classify --evidence-json '{"security_data_sensitivity":3, …}'` + `pytest tests/test_fitness.py` | OK: `Tier 4 (FM-01)`; el test tabular cubre FM-00 a FM-30 y la evidencia ilegible; la paridad con `classification-rules.md` compara regla, condición y tier (49 passed) |
| 3 | Snapshots deterministas | `pytest -k criterio_3` | OK: el mismo árbol en dos carpetas, con mtimes distintos, da el mismo SHA256 |
| 4 | Extracción segura | `pytest -k criterio_4` | OK: se rechazan traversal, ruta absoluta, unidad, `..\`, symlink, hardlink, device, bloque, FIFO y directorio |
| 5 | MCP funcional | `pytest -k criterio_5` (subprocess) | OK: `initialize`, `tools/list` con 7 tools con `inputSchema`; `change_name` con `../` da `isError: true` con el rechazo de S2 |
| 6 | Validador estricto | `exo validate` + `pytest tests/test_validate.py` | OK: «todo válido» sobre `content/` (con aviso esperado: `risk-tiering` todavía sin `SKILL.md`, llega en F4); un error específico por cada fixture de violación (34 passed) |
| 7 | Núcleo sin dependencias | `pytest tests/test_imports.py` | OK: solo stdlib (`tomllib` cuenta como ausente porque no existe en 3.10) |
| 8 | Idempotencia de filemerge | `pytest -k criterio_8` | OK: dos inyecciones dejan el archivo byte a byte igual y sin reescribir |

Extras:
- `ruff check .` limpio.
- `exo doctor` sin errores; en Windows avisa que la consola es cp1252.
- `pip wheel . --no-deps` incluye `exo/_content` (5 archivos) y las 6 plantillas; instalada en un venv aparte, resuelve su contenido.

Revisión final con contexto fresco (subagente). Encontró 8 problemas para corregir antes de cerrar y todos quedaron resueltos, con test:
- `restore` borraba a través de symlinks y junctions.
- `restore` podaba el snapshot que restauraba y no validaba antes de mutar.
- `filemerge` alteraba finales de línea mixtos, `\f`, NEL y U+2028.
- `filemerge` aceptaba contenido con marcadores.
- El servidor MCP se caía con ciertos mensajes.
- `structmerge` perdía claves duplicadas, precisión numérica y el BOM.
- El frontmatter estricto aceptaba YAML inválido.
- `write_atomic` reemplazaba symlinks.

También se aplicaron casi todas las mejoras menores (lock, observabilidad, CLI, validate, config) y se corrigieron 4 tests que no probaban lo que decían. Además, el autotest del doctor encontró un bug de rutas 8.3 de Windows en snapshots, que quedó corregido con su test.

Decisiones tomadas durante la fase: D-23 → ADR-0005 (CLI primero, MCP opcional y apagado por defecto).

Desvíos respecto del plan y por qué:
- Las tools viven en `src/exo/tools/registry.py` (con su subcomando de CLI) en lugar de `mcp/tools/<grupo>.py`, por ADR-0005; nota en `02-ARQUITECTURA.md` §2.10.
- `packs` es un módulo (`src/exo/packs.py`) y no un paquete, porque es chico.
- Subcomandos agregados por ADR-0005: `exo skills {list,info,diff}`, `exo change {list,status,followups,ai-usage}`, `exo version` y `exo validate --root`.
- Definiciones propias donde la referencia no tenía detalle (apéndices no fotografiados): regla FM-00, regex S2, marcadores `#`, formato de snapshot y manifiesto, fases por artefacto, esquema de `followups.json`, plantillas y versiones de MCP. Están en el plan aprobado y en el docstring de cada módulo.
- Los tests quedan exentos de E501 (tablas de casos); el código del paquete sigue con 100 columnas.
- Cierre local sin remoto, según la regla del principio de este archivo.

### F2 — Adaptadores, detección e instalador — 2026-11-07

Entorno: Windows 11 con Python 3.14.5 (venv `.venv`) y 3.10.20 (venv con `uv`); Linux Ubuntu 24.04 en WSL2 (clon limpio), con Python 3.12 administrado por `uv`, porque el Python del sistema no trae `ensurepip` y el modo venv de `install.sh` lo necesita. Resultados: Windows, 707 passed y 5 skipped (POSIX-only); Python 3.10, 707 passed; Linux, 711 passed. Cobertura 96,38 %.

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Instalación de un comando | `pytest -m installer --no-cov` | OK en Windows y Linux, modos venv y uv. Instalan, corren `exo doctor` sin errores, adoptan un proyecto con `-Init`/`--init` y desinstalan. El PATH se prueba sin tocar el real: en Windows, en una clave temporal de HKCU con `REG_EXPAND_SZ` (el tipo y `%USERPROFILE%` se conservan y la desinstalación deja el valor idéntico); en Linux, en un HOME temporal (`.profile`, `.bash_profile`, `.bashrc`). Además, ninguno de los dos modos pisa un `exo` ajeno. **Parcial:** macOS y el job `installers` de Azure Pipelines quedan diferidos hasta tener remoto |
| 2 | Adopción reproducible | `pytest -k "criterio_2 or golden"` | OK: `exo init --agents claude-code,copilot --yes` sobre el fixture vacío es igual a `tests/golden/claude-copilot__vacio.json`; además 6 golden tests (genérico, `AGENTS.md` del humano, `CLAUDE.md` existente, CRLF, `.mcp.json` JSONC con MCP) |
| 3 | Idempotencia | `pytest -k criterio_3` | OK (9 passed): un segundo `sync` o `init` en los 8 fixtures informa «sin cambios», no crea snapshot y no reescribe la config del humano |
| 4 | Archivos del humano | `pytest -k criterio_4` | OK: fuera de los bloques, `AGENTS.md`, `CLAUDE.md` y `.gitignore` quedan byte a byte iguales, con CRLF |
| 5 | Conflictos | `pytest -k criterio_5` | OK: un archivo generado y editado a mano hace que `exo sync` lo informe, salga con 1 y no escriba nada; con `--force` lo pisa con snapshot |
| 6 | Reversible | `pytest -k criterio_6` | OK (8 passed): `init` + `uninstall` deja idénticos los 8 fixtures, incluidos archivos sin salto de línea final y un `.claude/settings.json` del humano (indentado con `"allow": []`, y compacto con su propio permiso) |
| 7 | Multi-agente incremental | `pytest -k criterio_7` | OK: `exo add-agent cursor` solo agrega `.agents/skills/` (más config y lock); `remove-agent cursor` deja el árbol como estaba |
| 8 | Agentes reales | `docs/checklists/F2-agentes.md` | **Parcial.** Claude Code 2.1.312 (Windows): ve las 3 skills y los 4 subagentes, carga `AGENTS.md` sin `CLAUDE.md` y ejecuta `exo` sin pedir permiso una vez que el workspace es confiable. Copilot: checklist manual pendiente (licencia sin confirmar). MCP: no aplica (ADR-0005, D-23) |

Extras:
- `ruff check .` limpio.
- `exo validate`: «todo válido» (sigue el aviso esperado de `risk-tiering`, que llega en F4).

Checklist manual: `docs/checklists/F2-agentes.md`. Claude Code verificado el 2026-11-02; Copilot queda para el dueño.

Revisiones con contexto fresco (subagentes):
- **Primera revisión: 7 problemas para corregir antes de cerrar**, todos resueltos y con test:
  - Una config rota, inválida o de un esquema más nuevo hacía que `sync` borrara lo de los agentes.
  - La config se validaba después de escribir.
  - Una falla a mitad de camino dejaba archivos huérfanos. Ahora se restaura el snapshot.
  - `--force` perdía entradas del lock.
  - `uninstall` no era exacto con archivos sin salto final ni con un `"allow": []` del humano. Ahora el lock registra por archivo lo que creó el motor.
  - Los instaladores se cortaban en PowerShell 5.1 y aplanaban el PATH de usuario.
  - `install.sh` pisaba otro `exo`.
- **Segunda revisión, sobre esas correcciones: 3 problemas más**, también resueltos y con test:
  - Si faltaba la config con el motor instalado, se borraban los agentes. Ahora se toman del lock.
  - El modo uv pisaba otro `exo`.
  - `uninstall` listaba archivos del motor como si fueran del humano.
- También se aplicaron casi todas las mejoras menores:
  - Las bajas que pasan por un link y un directorio donde va un archivo quedan «sin resolver».
  - Lo creado por el motor se deshace aunque el humano lo haya vaciado.
  - `write_atomic` ya no deja temporales con un destino de solo lectura.
  - La salida de `init`, `uninstall` y `--force --dry-run` es más precisa.

Decisiones tomadas durante la fase:
- D-04 → ADR-0006: base agnóstica con detección; adaptadores solo para Claude Code y Copilot.
- D-05 y D-06 → ADR-0007: skills por proyecto, con las copias que hagan falta gestionadas por el lock.
- D-16 → ADR-0008: Azure DevOps y `azure-pipelines.yml`.

Desvíos respecto del plan y por qué:
- **Commits:** los adaptadores genérico, claude-code y copilot fueron en un solo commit (eran los commits 4 y 5 del plan), porque comparten los golden tests.
- **Permisos de Claude Code:** también agrega `PowerShell(exo:*)`, porque en Windows el agente usa esa herramienta. Las reglas de permiso del proyecto aplican recién cuando el workspace es confiable; `exo doctor` lo avisa (`claude-trust`).
- **Permiso de Copilot para ejecutar `exo`:** diferido. No se verificó una regla de proyecto que Copilot lea (ADR-0005).
- **`created` en el lock:** pasa a ser una lista por archivo (archivo y contenedores JSON creados), no una marca por entrada como decía el plan. Por entrada fallaba entre actualizaciones.
- **La config:** solo se escribe cuando el comando pide cambiar agentes, packs, MCP o tracker, y va en la misma transacción que el resto.
- **`--force`:** pisa lo generado por el motor y editado a mano, pero no un archivo del humano que no está en el lock, ni marcadores rotos o rutas con links. Esos quedan «sin resolver» y el comando sale con 1.
- **Los tests de instaladores:** usan `EXO_INSTALL_ENV_SUBKEY` (Windows) y un HOME temporal (Linux) para ejercitar el PATH sin tocar el de la máquina.
- **Limitaciones conocidas:**
  - `structmerge` reescribe el JSON entero. Un JSON del humano con formato mixto (listas en una línea dentro de un archivo indentado, escapes `\uXXXX`, `{ }`) se normaliza en la primera edición; el contenido no cambia y el original queda en el snapshot. El indentado de Claude Code y el JSON de una línea se conservan.
  - `uninstall` y la vuelta atrás borran directorios vacíos que ya existían antes (git no los versiona).
  - Una primera instalación fallida deja sus snapshots en `.exo/backups/`.
- **Cierre local sin remoto**, según la regla del principio de este archivo.
