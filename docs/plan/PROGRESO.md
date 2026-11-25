# Progreso de construcción

**Fase activa:** ninguna. F8 cierra con el merge de su PR a `main`: v1.0.0, hito M4. Repo público en `https://github.com/julimonte03/exo-harness` (D-22, ADR-0017).

**Paquete de capacidades y tiers (F9 a F13)**, registrado el 2026-11-25 en el paso 0 (rama `feat/paquete-registro`):
- **Fuente:** `docs/plan/paquete-capacidades.md`.
- **Decisiones:** D-52 a D-55, con ADR-0019 y ADR-0020.
- **Versión:** `git tag --list "v1*"` devolvió `v1.0.0` el 2026-11-25, así que el paquete termina en **2.0.0** (sección 0 del paquete, punto 2).
- **Próxima fase:** F9, que arranca cuando se mergee el PR del paso 0.

Una fase está **terminada** cuando: todos sus criterios de aceptación pasaron con el comando exacto, la CI está verde en los tres sistemas operativos y el PR de la fase está mergeado; desde F8, el dueño lo abre y lo mergea en GitHub (D-51).

**Hasta F7, sin repo remoto** (decisión del dueño, 2026-10-30): las fases se cerraron en local. La suite y el lint se corrieron en Windows y en Linux (Ubuntu en WSL, sobre un clon limpio), y la rama se mergeó a `main` con `git merge --no-ff`, sin push. La CI y el PR quedaron diferidos (ADR-0008).

**Desde F8** (D-22, D-45): el repo es público en GitHub y la CI corre en GitHub Actions, con Windows, macOS y Linux y Python 3.10 a 3.13 (`.github/workflows/ci.yml`). `main` y las ramas de F0 a F7 se subieron el 2026-11-19. `azure-pipelines.yml` queda como ejemplo, sin paridad. Cada fase cierra con un PR de su rama a `main`, que el dueño abre y mergea en GitHub con la CI en verde; nunca hay push directo a `main` (D-51).

## Estado por fase

| Fase | Estado | Rama / PR | Inicio | Cierre | Notas |
|---|---|---|---|---|---|
| F0 Fundaciones | Terminada (local; CI diferida) | `feat/F0-fundaciones`, mergeada a `main` en local, sin PR | 2026-10-29 | 2026-10-30 | Criterios 1, 2, 4–7 OK. Criterio 3: Windows y Linux en local OK; macOS y Azure Pipelines diferidos hasta tener remoto (ADR-0008) |
| F1 Núcleo | Terminada (local; CI diferida) | `feat/F1-nucleo`, mergeada a `main` en local, sin PR | 2026-10-30 | 2026-10-30 | Criterios 1–8 OK en Windows (3.14 y 3.10) y Linux (WSL). D-23 → ADR-0005 |
| F2 Adaptadores + instalador | Terminada (local; CI diferida) | `feat/F2-adaptadores`, mergeada a `main` en local, sin PR | 2026-10-30 | 2026-11-07 | Criterios 1–7 OK en Windows (3.14 y 3.10) y Linux (WSL). Criterio 1 sin macOS ni Azure. Criterio 8: Claude Code OK, Copilot pendiente (checklist manual). D-04 → ADR-0006, D-05/D-06 → ADR-0007, D-16 → ADR-0008 |
| F3 Memoria v2 | Terminada (local; CI diferida) | `feat/F3-memoria`, mergeada a `main` en local, sin PR | 2026-11-13 | 2026-11-13 | Criterios 2–8 OK en Windows (3.14 y 3.10 sin extras) y Linux (WSL, con y sin extras). Criterio 1 fuera de alcance (ADR-0009). D-07/D-08 → ADR-0010; D-20, D-24 y D-25 → ADR-0009; D-12 parcial |
| F4 Ciclo SDD | Terminada (local; CI diferida) | `feat/F4-ciclo-sdd`, mergeada a `main` en local, sin PR | 2026-11-14 | 2026-11-14 | Criterios 1–7 OK en Windows (3.14 y 3.10) y Linux (WSL); 4 a 7 con Claude Code real. Criterio 6 sin Copilot (opcional). D-26, D-27 y D-28; D-11 → ADR-0013 |
| F5 Gobierno y gates | Terminada (local; CI diferida) | `feat/F5-gobierno`, mergeada a `main` en local, sin PR | 2026-11-15 | 2026-11-16 | Criterios 1–7 OK en Windows (3.14 y 3.10) y Linux (WSL); 7 con Claude Code real (Tier 1 y Tier 2), Copilot opcional. Hito M2 (v0.1.0). D-12, D-21 y D-29 a D-32 → ADR-0014 |
| F6 Ingeniería inversa | Terminada (local; CI diferida) | `feat/F6-ingenieria-inversa`, mergeada a `main` en local, sin PR | 2026-11-16 | 2026-11-17 | Criterios 1–7 OK en Windows (3.14 y 3.10) y Linux (WSL); 3 a 5 con Claude Code real (dos corridas sobre `py-invoices`), Copilot opcional. Criterio 8 diferido a F8 (D-35). Hito M3 (v0.2.0). D-14, D-19 y D-33 a D-37 → ADR-0015 |
| F7 Packs | Terminada (local; CI diferida) | `feat/F7-packs`, mergeada a `main` en local, sin PR | 2026-11-17 | 2026-11-17 | Criterios 1–4 OK en Windows (3.14 y 3.10) y Linux (WSL); 3 con Claude Code real (117 de 117 evals). 65 skills nuevas, 6 packs nuevos. D-12 (resto), D-18 y D-38 a D-44 → ADR-0016 |
| F8 Endurecimiento + v1.0 | Terminada | `feat/F8-v1`, PR a `main` (D-51) | 2026-11-19 | 2026-11-25 | Criterios 1, 2 y 4–8 OK; 3 con 5 de 6 escenarios (el Tier 3 de Copilot, parcial: D-50). CI de GitHub Actions en verde en los tres sistemas y Python 3.10 a 3.13. Hito M4 (v1.0.0). D-22, D-35, D-17 y D-45 a D-48 → ADR-0017 y ADR-0018; D-49 (MIT), D-50 y D-51 (cierre por PR). Historia limpia (D-46) |
| F9 Tres tiers | Pendiente | `feat/F9-tres-tiers` | | | Paquete. D-52 → ADR-0019. Versión 2.0.0 (BREAKING) |
| F10 Catálogo de capacidades y perfil | Pendiente | `feat/F10-capacidades` | | | Paquete. D-53 → ADR-0020 |
| F11 Modelo por tier y por rol | Pendiente | `feat/F11-modelos` | | | Paquete. D-54 → ADR-0020 |
| F12 Segunda opinión | Pendiente | `feat/F12-segunda-opinion` | | | Paquete. D-55 → ADR-0020 |
| F13 Medición y ajuste | Pendiente | `feat/F13-medicion` | | | Paquete. ADR que confirma o ajusta los defaults revisables. Hito v2.0.0 |

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
| 3 | CI verde en los 3 SO | Sin remoto: `pip install -e ".[dev]"`, `exo --version`, `python -m exo --version`, `pytest`, `ruff check .` en Windows y en Ubuntu (WSL) | **Parcial**: Windows OK (3.14.5 y 3.10.20) y Linux OK (3.12.3; 8 passed, 96.55 %, versión `exo 0.0.1` por las dos vías). macOS y el run de GitHub Actions (`.github/workflows/ci.yml`) quedan diferidos hasta tener remoto. **F8:** `ci.yml` existe desde F8 y la CI corre los tres sistemas (D-45) |
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

### F3 — Memoria v2 — 2026-11-13

**Entorno:**
- Windows 11, con Python 3.14.5 (venv `.venv`, con los extras `[vector]` y `[static]` y los dos modelos bajados) y Python 3.10.20 (venv con `uv`, **sin extras**).
- Linux Ubuntu 24.04 en WSL2, con Python 3.12 de `uv`, sobre un clon limpio, con y sin extras.

**Resultados:**

| Entorno | Resultado |
|---|---|
| Windows, Python 3.14 | 891 passed, cobertura 94,84 % |
| Windows, Python 3.10 sin extras | 884 passed |
| Linux | 888 passed; con extras, 174 tests de memoria |

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Guard sin fugas | — | **Fuera de alcance** (decisión del dueño, D-24, ADR-0009). La memoria no tiene guard |
| 2 | Funciona sin extras | Suite completa en el venv de Python 3.10 sin `[vector]`, más `exo mem save` y `exo mem search --json` | OK: la suite pasa (los tests de modelos y de sqlite-vec se saltean) y `mode` es `"lexical"` |
| 3 | Índices reconstruibles | `pytest -k criterio_3 tests/test_memory_semantic.py tests/test_memory_providers.py` | OK (2 passed). Se borran los vectores y el índice FTS5 y se reindexa desde SQLite: mismos resultados antes y después, con el proveedor de prueba y con el modelo onnx real (las 50 consultas del dataset) |
| 4 | Concurrencia | `pytest tests/test_memory_concurrency.py` | OK (2 passed). Servidor MCP y CLI en dos procesos, 60 `save` + 60 `search` cada uno, con índice semántico y sin él: sin errores de lock |
| 5 | Experimento cerrado | `exo mem eval --providers static,onnx --output docs/evals/memory-2026-11-13.md` | OK: reporte con la tabla de métricas y ADR-0010. La regla se congeló en `15ac9ba` antes de correr. Gana `hybrid-onnx` (Recall@5 80,0 contra 62,2 de la léxica, exactas sin pérdida) |
| 6 | Rendimiento | La misma corrida | OK: p95 de 67,1 ms con 5 000 memorias en `hybrid-onnx` (85 ms al repetirla en la revisión), con el modelo cargado. Cada llamada del CLI carga el modelo: entre 1,3 y 2,1 s (ver ADR-0010) |
| 7 | Nada sale sin permiso | `pytest -k criterio_7` y `exo mem reindex --provider openai-compatible` | OK: error claro (pide `--allow-remote`) y sale con 1. Además, Ollama local no pasa por el proxy y Ollama en otro host cuenta como remoto |
| 8 | Paridad de API | `pytest -k criterio_8` | OK: las 15 tools con los nombres del §5.3, por CLI (`exo mem …`) y por el servidor MCP |

**Extras:**
- `ruff check .` limpio y `exo validate` «todo válido».
- **Sesión real de Claude Code 2.1.312** (`claude -p` sobre un proyecto adoptado, con una memoria sembrada):
  - Por la regla de `AGENTS.md`, corrió `exo mem context` al empezar, recuperó la decisión y cerró la sesión con `exo mem session summary`.
  - Sin `--allowedTools`, el comando quedó esperando aprobación: el workspace no era confiable, el mismo hallazgo de F2. El agente no inventó la memoria.

**Revisión final con contexto fresco** (subagente):
- Reprodujo los números del experimento y encontró 8 problemas para corregir. Todos quedaron resueltos con su test (`tests/test_memory_regresiones.py`: 29 de 31 fallan con el código anterior):
  - `--content -` corrompía el UTF-8 en Windows.
  - Un remoto de git con acentos rompía la detección del proyecto.
  - Ollama local pasaba por el proxy del sistema.
  - Un `reindex` con otra dimensión desde otro proceso dejaba la búsqueda rota, y `doctor` decía ok.
  - Un modelo roto impedía guardar.
  - El import comparaba fechas como texto.
  - Repos sin remoto con la misma carpeta compartían memoria.
  - La latencia se había medido con el modelo cargado y el CLI lo recarga en cada llamada. Ahora hay un caché en el proceso y la aclaración en ADR-0010.
- También se aplicaron casi todas las menores:
  - la consulta FTS5 la tokeniza FTS5;
  - abrir la base no toma el lock de escritura;
  - la salida a un pipe va en UTF-8;
  - `save` muestra los parecidos;
  - errores claros para ids enormes y sesiones inexistentes;
  - `merge` no duplica contenido idéntico, entre otras.
- **Python 3.10:** antes de la revisión ya había aparecido un bug, que quedó corregido. Con la resolución del reloj de Windows, el import pisaba una versión local con la misma fecha.
- **Un test escribió en la carpeta de datos real del usuario:** un `monkeypatch.undo()` deshizo el aislamiento. Se revisó la base: solo tenía lo que había creado el test, y se borró. `conftest` ahora usa un `MonkeyPatch` propio.

**Decisiones tomadas durante la fase:**
- ADR-0009, decisión del dueño: la memoria es por usuario, sin guard ni perfiles (D-24, D-12 parcial), sin Qdrant (D-20) y sin hooks, solo reglas (D-25). La política de la organización bloquea los hooks de proyecto en Claude Code (`allowManagedHooksOnly`).
- ADR-0010, por el experimento: D-07 → `hybrid-sqlite`; D-08 → `onnx` (FastEmbed, `paraphrase-multilingual-MiniLM-L12-v2`) primero en `local` y `static` (model2vec) como alternativa. El extra `[vector]` pasa a ser sqlite-vec + FastEmbed; model2vec queda en `[static]`.

**Desvíos respecto del plan y por qué:**
- **Fuera de la fase, por ADR-0009:** el guard S1 (tarea 2 y criterio 1), Qdrant (tarea 7) y los hooks de sesión (parte de la tarea 9).
- **Configuración de la memoria:** vive en la `meta` de la base (`exo mem reindex --provider …`), no en `.exo/config.json`. Hay una base por usuario para todos sus proyectos. La sección `memory` de la config del proyecto queda sin efecto y `exo doctor` lo avisa.
- **Sin descargas implícitas:** los modelos se bajan solo con `exo mem model pull`, a una carpeta temporal que se renombra al terminar. Al usarlos se cargan de la carpeta local, sin red.
- **Índice FTS5 sin triggers:** se mantiene desde Python, así un Python sin FTS5 puede escribir igual y el índice se reconstruye al volver a abrir con FTS5. Tiene contenido propio, en lugar de contenido externo.
- **Vectores en una tabla común:** blobs float32 con la función de distancia de sqlite-vec, en lugar de una tabla virtual `vec0`. Así los filtros se aplican antes de rankear con el mismo SQL para sqlite-vec y para el backend de Python.
- **Definiciones propias:** la referencia no las trae. Son los `inputSchema` de las 15 tools, la normalización del remoto, los tipos de observación y el formato de export. Están en los docstrings.
- **Trabajo futuro documentado en ADR-0010:**
  - pesos de RRF para el idioma cruzado (la semántica sola acierta el 80 % y la híbrida, el 40 %);
  - palabras vacías en la léxica;
  - un dataset más grande y escrito por otra persona.
- **Cierre local sin remoto**, según la regla del principio de este archivo. El job de Azure Pipelines con extras queda definido en `azure-pipelines.yml`.

### Refactor al inglés (ADR-0011) — 2026-11-14

No es una fase: es la rama previa a F4 que pide ADR-0011. Rama `refactor/ingles`, mergeada a `main` en local, sin PR. Se hizo en tres ramas en paralelo que se integraron en esta:
- `i18n/a`: el contenido de `content/`, las plantillas SDD y los mensajes de `sdd`.
- `i18n/b`: el núcleo, los instaladores, `doctor` y los comandos.
- `i18n/c`: la memoria, las descripciones de las tools y el servidor MCP.

**Resultados:**

| Entorno | Resultado |
|---|---|
| Windows, Python 3.14 | 890 passed, cobertura 94,78 %, `ruff check .` limpio |
| Windows, Python 3.10 sin extras | 884 passed; `exo validate` «all valid» |
| Windows, tests de instaladores | 2 passed (4 salteados: son de `install.sh`) |
| Linux | 888 passed, más los 4 tests de `install.sh` |

Se regeneraron los goldens de `tests/golden/` (6 archivos) y se revisó el diff.

**Cambios visibles, además de los textos:**
- Claves del JSON del CLI: `agentes` → `agents`, `backup de seguridad` → `safety_backup` y `también se borra…` → `also_removed`, que ahora es una lista.
- Los errores de uso empiezan con `usage error:` y `doctor` marca los avisos con `warning`.
- La marca que el instalador deja en el perfil del shell pasa a ser `# added by <dist>`. Como todavía no hubo releases, no hay instalaciones con la marca vieja.
- `exo validate` nunca verificó que los disparadores fueran bilingües: solo lo decía su mensaje, que ahora pide disparadores en inglés.

**Queda en español a propósito:**
- La documentación del repo, los docstrings y los comentarios (ADR-0011).
- Las confirmaciones aceptan «sí», además de «yes».
- El dataset del experimento de memoria (`tests/memory_eval/`), que es bilingüe porque mide el idioma cruzado.

### F4 — Ciclo SDD con specs vivas — 2026-11-14

**Entorno:**
- Windows 11, con Python 3.14.5 (`.venv`) y Python 3.10.20 (venv con `uv`, sin extras).
- Linux Ubuntu 24.04 en WSL2, con Python 3.12 de `uv`, sobre un clon limpio de la rama.
- Claude Code 2.1.325, con `claude -p` sobre copias de `tests/fixtures/repos/toy-python/`.
- Los datos aislados con `EXO_DATA_DIR` y `EXO_MEMORY_DB`.

**Resultados:**

| Entorno | Resultado |
|---|---|
| Windows, Python 3.14 | 1189 passed, cobertura 94,64 % |
| Windows, Python 3.10 sin extras | 1183 passed |
| Linux | 1187 passed; `ruff check .` limpio y `exo validate` «all valid» |

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Contenido válido | `exo validate` | OK: «2 packs, 23 skills, 4 subagents, 8 shared contracts: all valid». Son 8 skills de core (7 nuevas, más `memory-protocol`) y 15 de sdd (las 13 de la fase, más `sdd-continue` y `sdd-ff`) |
| 2 | Mapa consistente | `pytest tests/test_phase_map_consistency.py` | OK (47 passed). Toda skill del mapa existe o declara su degradación. Las skills de fase corren donde dice la tabla de la sección G y nombran las Required de su fila. Los subagentes tienen las tools de su rol |
| 3 | Deltas deterministas | `pytest -k criterio_3 tests/test_specs.py` | OK (5 passed): resultado esperado byte a byte, idempotencia (sin escritura ni snapshot) y fallo con referencias inexistentes sin escribir nada |
| 4 | Tier 1 con subagentes | Claude Code sobre `toy-python`: `--version` en el CLI | OK. Tier 1 (FM-30). La evidencia del riesgo, en `sdd-explorer`; apply, en `sdd-implementer`; verify, en `sdd-verifier` con contexto fresco. Fase siguiente `risk → new → apply → verify → archive → none`. Delta integrado en `specs/capabilities/cli/`. `exo check --base master` y `speclint`, con 0 errores (`docs/checklists/F4-ciclo.md`) |
| 5 | Tier 3 | Claude Code: tareas en SQLite, con ticket `PROJ-42` | OK. Tier 3 (FM-10). Aparecen exploration, proposal, spec, design, tasks y test-spec. Los jueces corrieron en `sdd-judge` y apply en dos corridas de `sdd-implementer`. Verify, en `sdd-verifier` con contexto fresco: dio `blocked` por el arnés de prueba (un commit de `exo sync` en la rama y un permiso de la prueba) y el ciclo se frenó como manda el contrato. Archive quedó pendiente de esos dos puntos |
| 6 | Sin subagentes | Claude Code con `--disallowedTools "Task Agent"` | OK. Todo inline, con «no isolation» declarado en cada fase. Mismos artefactos y chequeos (Tier 2 por la evidencia). Copilot queda opcional: lo prueba el dueño |
| 7 | Reglas de tier | `pytest -k criterio_7 tests/test_changes.py`, más una conversación | OK. Tests: evidencia faltante da Tier 4, un tier ilegible cuenta como 4 y el downgrade sin `--confirm-downgrade` sale con 1. En la conversación, el orquestador no bajó un Tier 3: la evidencia no lo sostenía, y distinguió el pedido de la confirmación literal |

**Extras:**
- `ruff check .` limpio.
- **Claude Code en `claude -p`:** el workspace no es confiable y `permissions.allow` no aplica (lo mismo de F2). Las corridas pasan las herramientas con `--allowedTools`.
- **La primera sesión de Tier 3 se cortó a los 50 minutos.** La segunda la retomó desde `exo change status` (`next_phase: apply`): el estado sobrevive entre sesiones.

**Tres subagentes escribieron el contenido** (worktrees manuales; el aislamiento automático falla en esta máquina):
- Escribieron las skills de core, las de sdd y los subagentes contra los contratos ya mergeados, y cada uno reportó las lagunas que encontró.
- **Ajustes del runtime:**
  - `exo check` ve los changes archivados que se nombran o que toca el diff.
  - Speclint exige que `test-spec.md` cubra el delta y toma el veredicto de la primera palabra.
  - JSON desde un archivo, para PowerShell 5.1.
- **Ajustes de los contratos:**
  - Pasan a core.
  - Se definen el plan congelado de Tier 1 y 2, quién registra y la propiedad de `spec.md` y `test-spec.md` cuando sube el tier.

**Revisión final con contexto fresco** (subagente, sobre `main...feat/F4-ciclo-sdd`):
- Encontró 9 problemas del runtime y 7 inconsistencias entre contratos y skills. Todo se corrigió con su test (`tests/test_f4_regresiones.py`, 25 tests).
- **Runtime:**
  - la carpeta vacía de una épica archivada aparecía como change y `exo check` fallaba;
  - el JSON en UTF-16 de PowerShell daba un traceback;
  - la evidencia mal formada se registraba como Tier 4, y después había que confirmar un downgrade;
  - la capacidad quedaba sin requisitos tras un REMOVED;
  - había secciones repetidas;
  - la merge reescribía los fines de línea mezclados;
  - speclint y la merge leían distinto un archivo con BOM;
  - `--base` comparaba contra la punta y no contra el merge-base;
  - había escrituras a través de links;
  - los errores de uso salían con 1.
- **Contratos:**
  - un `needs-rework` volvía a verify sin arreglar nada;
  - la marca de «apply terminado» se registraba aunque apply no terminara;
  - nadie escribía `followups.json`;
  - `branch-pr` y `pr.md` estaban desactualizados;
  - `sdd-new` negaba su fila del mapa;
  - los tickets con `#` iban sin comillas.
- **La fase siguiente salió de la prosa al runtime:** `exo change status` calcula `next_phase` con un registro ordenado de fases (`exo change record --phase-done`).
- **El test de consistencia lee la tabla de la sección G** en vez de repetirla.

**Incidente:**
- Un `exo uninstall` manual sobre un proyecto de prueba escribió un backup en la carpeta de datos real del usuario (`uninstall-backups/`). Solo tenía ese proyecto de prueba y se borró enseguida.
- Desde entonces, toda corrida manual o de agente aísla `EXO_DATA_DIR` y `EXO_MEMORY_DB` (anotado en el checklist).

**Decisiones tomadas durante la fase:**
- **D-26** (del dueño): el ticket va normalizado en los nombres de cambio y épica.
- **D-27** (del dueño): artefactos por tier; Tier 1 sin delta si no cambia comportamiento.
- **D-28:** los meta-comandos son skills.
- **ADR-0013:** formato de specs vivas y deltas, integración por ID y lápidas.

**Desvíos respecto del plan y por qué:**
- **Contratos en `content/packs/core/shared/`**, no en `content/shared/`:
  - las skills de core los citan y core se instala siempre;
  - `exo validate` exige que un pack cite solo contratos suyos o de lo que requiere.
  - Las plantillas y el esquema del AI Usage Record se instalan como contratos (`.exo/shared/templates/` y `schemas/`), con una sola fuente en `src/exo/sdd/`.
- **`core/tickets.py`** en lugar de `sdd/tickets.py`: lo usa la config, que es de core.
- **Dónde corre cada fase** (definición propia sobre §6.1, sección G del contrato común):
  - la planificación corre inline porque habla con la persona;
  - explore, verify y los jueces corren en subagentes de solo lectura que devuelven el documento;
  - apply corre en `sdd-implementer`.
- **Comandos que el plan no nombraba:** `exo change record` (§7.7: escritura atómica e idempotente del registro), `--evidence-file`, `@<archivo>` y `--no-tickets` (PowerShell 5.1), y `exo change status` con `next_phase`. `exo change new/record`, `exo specs` y `exo check` no son tools del registro: escriben, y el MCP está bloqueado por la política.
- **Lápidas** (`## Removed Requirements`): un REMOVED repetido no hace nada y los IDs no se reusan.
- **`followups.json`:** en F4 no lo escribe nadie. Los hallazgos de los jueces viven en `verify-record.md` y la persona decide cada uno; F5 agrega el archivo.
- **Goldens con contenido sintético** (`tests/_content.py`): `hello-exo` sale del contenido real, y un smoke instala el contenido real sin golden.
- **`tests/fixtures/repos/toy-python/`** es el único fixture versionado como carpeta, sin archivos de agente; pytest no lo recorre.
- **El verifier corre solo tests, por instrucción:** el `tools` de los subagentes no restringe a qué comandos llega `Bash`.
- **Para F5:**
  - `exo check` v1 no mira el veredicto (da PASS con `blocked`);
  - los gates tienen que hacerlo.
- **Cierre local sin remoto**, según la regla del principio de este archivo.

### F5 — Gobierno, seguridad y gates — 2026-11-16

**Entorno:**
- Windows 11, con Python 3.14.5 (`.venv`) y Python 3.10.20 (venv con `uv`, sin extras).
- Linux Ubuntu 24.04 en WSL2, con Python 3.12 de `uv`, sobre un clon limpio de la rama.
- Claude Code 2.1.325, con `claude -p` sobre copias de `tests/fixtures/repos/toy-python/`, con hooks activos.
- Los datos aislados con `EXO_DATA_DIR` y `EXO_MEMORY_DB`.

**Resultados:**

| Entorno | Resultado |
|---|---|
| Windows, Python 3.14 | 1456 passed, cobertura 94,17 % |
| Windows, Python 3.10 sin extras | 1450 passed |
| Linux | 1454 passed; `ruff check .` limpio y `exo validate` «all valid» |

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Reglas acotadas | `exo validate` | OK: «4 packs, 34 skills, 4 subagents, 11 shared contracts: all valid», sin advertencias. `AGENTS.base.md` tiene 54 líneas (el límite es 60) |
| 2 | Hooks efectivos | `pytest -k criterio_2 tests/test_githooks.py`, más `pytest tests/test_git_diff.py` | OK (3 passed; `test_git_diff.py`, 18 passed). En repos git temporales: mensaje inválido rechazado y válido aceptado, con y sin `Refs:`; secreto y PII sintéticos en el stage rechazados, y aceptados con waiver; push a `main`, force-push y borrado de rama protegida rechazados. `test_git_diff.py` cubre las vías de evasión que encontró la revisión |
| 3 | Check estricto | `pytest -k criterio_3 tests/test_check_f5.py` | OK (6 passed). Un Tier 2 sin `test-spec.md`, sin registro, con veredicto `blocked` o sin su gate falla; completo, pasa |
| 4 | Gates publicables | `pytest -k criterio_4 tests/test_gates_publish.py` | OK (2 passed). `--dry-run` da exactamente un texto por gate, con su marcador; con un `publish_command` de prueba, una llamada por gate. En la corrida de Tier 2, `exo gate publish --dry-run` imprimió `code_review` y `contract_check` |
| 5 | CI de proyecto (agnóstica) | `pytest -k criterio_5 tests/test_check_f5.py` | OK (1 passed). En un repo temporal, `exo check --base main` (el paso de los ejemplos) da 0 con un change Tier 2 completo y 1 sin su gate. Sin remoto no hay CI real: los ejemplos de `ci-and-review.md` quedan `[No verificado]` |
| 6 | P0 | `exo p0` en el proyecto de la corrida real, más `pytest -k criterio_6 tests/test_p0.py` | OK: `=== P0 GATE: PASSED (3/3) ===` (escáner con 26 casos, 8 entradas maliciosas rechazadas, `core.hooksPath = .exo/githooks`) |
| 7 | Proyecto nuevo de punta a punta | Claude Code real (`docs/checklists/F5-proyecto-nuevo.md`) | OK en dos corridas. Tier 1 (`--version`, PROJ-7) y Tier 2 (rechazar títulos vacíos, PROJ-8): `exo init` con los cuatro packs y los hooks activos, commits con `Refs:` por los hooks, gates (`contract_check` y `code_review`, este escrito por `harness-review` en el verifier) y `exo check --base main` en verde. Copilot queda opcional |

**Extras:**
- `ruff check .` limpio.
- **La corrida en Linux encontró un test roto:** la rama POSIX del test del bit de ejecución leía un atributo que no existe. En Windows no corre; el motor estaba bien.
- **Al subir la versión,** el install editable se reinstala (`uv pip install -e .`) para que la metadata diga 0.1.0 y `test_meta` pase.
- **En la corrida de Tier 2,** la respuesta del verifier se cortó por un error de stream y Claude Code lo informó como "interrupted by user". Se retomó con `claude -p --resume` (`docs/checklists/F5-proyecto-nuevo.md`).

**Tres subagentes escribieron los packs** (worktrees manuales, contra los contratos ya mergeados): `security`, `quality`, y `skill-reviewer` con el pre-chequeo de `exo validate`. Lo integré con cherry-pick:
- **El mapa fase → skills** ganó la sección Gates. La tabla de degradaciones pasó a «Inline criteria for skills not installed»: puede tener filas de skills que existen si viven en un pack opcional, para que un proyecto con `sdd` y sin `quality` o `security` siga degradando con criterio.
- **Los gates se conectaron al ciclo:** quién escribe cada uno y en qué fase, y que el orquestador persiste los que devuelve un subagente.
- **Dos huecos del motor que expuso `quality`:** followups arreglados (`--fixed`) y descartes por `id`.

**La preparación de la corrida real encontró un bug:** el `pre-commit` bloqueaba el commit de `exo init` porque un hash de `lock.json` tenía una tira de dígitos que pasaba Luhn. Se corrigió el detector de tarjetas.

**Revisión final con contexto fresco** (dos subagentes: motor y contenido). Todo lo que encontraron se corrigió con su test:
- **Motor (3 High, 4 Medium, 13 Low):**
  - el escaneo del diff se podía esquivar (una línea que empieza con `++ `, `-diff` en `.gitattributes`, nombres que git entrecomilla, `diff.noprefix`) y fallaba abierto si git fallaba;
  - `--base` no escaneaba con persistencia `memory` o `none` ni junto con `--change`;
  - `env-assignment` daba un Crítico con `PYTHONPATH` o `COMPAT_MODE` y no veía `PASSWORD=`;
  - `pre-push` escaneaba el árbol de trabajo en vez de lo empujado y no revisaba ramas nuevas;
  - la activación pisaba un `core.hooksPath` global y apagaba los hooks de `.git/hooks` (git-lfs);
  - el framework pre-commit no traía `pre-push` y su estado daba «ok» sin instalar;
  - menores: `--status fixed`, escrituras parciales de `exo change record`, BOM en `commit-msg`, la redacción de secretos cortos, falsos positivos de tarjetas, waivers, nombres de gate con dígitos, marcadores duplicados en `publish`, `judgment-day` que no contaba la última entrada, scripts de skills sin revisar, ramas protegidas con patrón.
- **Contenido (1 High, 6 Medium, 15 Low):**
  - `sdd-design` no escribía el gate `threat_model`, así que un Tier 3 terminaba con `exo check` en rojo;
  - no había camino para un riesgo que el `tech_lead` acepta;
  - los jueces de design y verify no registraban followups y sus IDs chocaban;
  - un ejemplo enseñaba a comparar contraseñas con tiempo constante (en vez de verificar un hash);
  - nueve pares OWASP ↔ CWE mal mapeados (verificados en cwe.mitre.org), y CWE-613, deprecado en CWE 5.0;
  - el umbral de tech_lead no era uno solo;
  - restos de F4 en el contenido instalado.

**Decisiones tomadas durante la fase:**
- **D-12** (del dueño): protección de datos agnóstica; fuera `legacy-profile`.
- **D-21** (del dueño): git hooks por defecto.
- **D-29** (del dueño): el ticket como footer `Refs:`.
- **D-30** (del dueño): CI y PR agnósticos, con el host detectado y guardado.
- **D-31:** sin hooks de agente.
- **D-32:** `exo p0` redefinido.
- **ADR-0014:** enforcement agnóstico.

**Desvíos respecto del plan y por qué:**
- **`secure_coding_check` corre al final de apply,** no en verify. Es una pasada con ciclo de arreglo propio, y la revisión independiente ya la hace `security_review` en verify. Así verify no carga tres skills de gate.
- **`skill-reviewer` no es un gate de tier:** sus hallazgos van a Issues Found del verify. Un gate opt-in que ninguna fase escribía dejaba `exo check` en rojo.
- **Packs por defecto:** si el contenido no trae alguno (un árbol propio), se saltea; pedidos explícitamente, siguen fallando.
- **Un riesgo aceptado por el `tech_lead`** llega al siguiente verify como dato y no bloquea `ready`; el gate sigue ESCALATED para el PR.
- **Tarea 9 (hooks de agente) fuera de alcance** (D-31): el enforcement real son los git hooks y la CI.
- **Plantillas de CI → ejemplos** en el contrato `ci-and-review.md` (D-30), sin `exo init --ci`.

**Limitaciones conocidas:**
- **Husky:** se soporta husky 9; los scripts nuevos que crea el motor no tienen el preámbulo de husky 8.
- **Framework pre-commit:** el `pre-push` toma la ref de las variables `PRE_COMMIT_*` cuando no llega por stdin [No verificado contra el framework real].
- **Nombre de la skill `review`:** puede chocar con el comando integrado `/review` de Claude Code. Se mantiene porque el plan lo nombra así; a revisar en F7.
- **Ejemplos de CI y de `publish_command`** (`gh`, `az`, `glab`): `[No verificado]`, porque no hay remoto.
- **Cierre local sin remoto**, según la regla del principio de este archivo.

### F6 — Ingeniería inversa y adopción de proyectos existentes — 2026-11-17

**Entorno:**
- Windows 11, con Python 3.14.5 (`.venv`) y Python 3.10.20 (venv con `uv`, sin extras).
- Linux Ubuntu 24.04 en WSL2, con Python 3.12 de `uv`, sobre un clon limpio de la rama.
- Claude Code 2.1.325, con `claude -p` sobre copias de `tests/fixtures/repos/py-invoices/`.
- Los datos aislados con `EXO_DATA_DIR` y `EXO_MEMORY_DB`.

**Resultados:**

| Entorno | Resultado |
|---|---|
| Windows, Python 3.14 | 1577 passed y 6 skipped (POSIX y extras de memoria), cobertura 93,72 % |
| Windows, Python 3.10 sin extras | 1571 passed y 12 skipped (POSIX, symlinks y extras de memoria), cobertura 93,45 % |
| Linux | 1575 passed y 8 skipped (extras de memoria que no están), cobertura 93,48 %; `exo --version` y `python -m exo --version` dan `exo 0.2.0`; `ruff check .` limpio y `exo validate` «6 packs, 41 skills, 6 subagents, 13 shared contracts: all valid» |

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Determinismo | `pytest -k criterio_1 tests/test_discovery_inventory.py tests/test_discovery_ground_truth.py` | OK (4 passed). En los tres fixtures, con historia de tres autores, `exo discover inventory`, `structure` y `plan` en subprocesos con `PYTHONHASHSEED` 1, 4242 y 77 dan los mismos bytes en todo `discovery/`. Commitear los resultados y correrlos otra vez no cambia nada y deja el árbol limpio |
| 2 | Inventario correcto | `pytest -k criterio_2 tests/test_discovery_ground_truth.py` | OK (6 passed). En `py-invoices`, `node-shop` y `java-library`: lenguajes, frameworks, entrypoints, tests, CI, migraciones, contratos de API, infraestructura y archivos sensibles según la verdad conocida; módulos y aristas exactos |
| 3 | Adopción completa | Claude Code real con `/exo-adopt` sobre `py-invoices` (`docs/checklists/F6-adopcion.md`), verificado contra la verdad conocida | OK en dos corridas. En la segunda, con el contenido final: R0 a R6 completos, 9 de 10 unidades cerradas y 1 salteada con su razón, 4 capacidades as-is (51 FR y 2 NFR, todos con evidencia). Las 5 capacidades de la verdad conocida tienen una spec que cita sus archivos clave |
| 4 | Precisión | `exo discover coverage` después de la auditoría, en las mismas corridas | OK. Segunda corrida: muestra de 30 FR, las 4 capacidades al 100 % sin ronda de reapertura. Primera: `quotes` dio 75 %, el agente la reabrió, re-extrajo, re-sintetizó y re-auditó, y terminó al 100 % |
| 5 | Solo lectura | `pytest -k criterio_5 tests/test_discovery_units.py`, más las corridas reales | OK (1 passed). En las dos corridas, `outside_changes: []` y `git status` solo con `.exo/context.md`, `.exo/discovery/`, los ADRs `*-recovered-*` y `specs/capabilities/` |
| 6 | Reanudable | `pytest -k criterio_6 tests/test_discovery_units.py` | OK (1 passed). Cortar a mitad de R3 y seguir no rehace las unidades cerradas, y una unidad cortada a medias se extrae de nuevo |
| 7 | Incremental | `pytest -k criterio_7 tests/test_discovery_units.py` | OK (1 passed). Cambiar un archivo y correr `update` marca stale solo su unidad y la capacidad que lo cita. La capacidad tiene que estar registrada con `exo discover synthesized`; una que nunca se registró aparece en `unrecorded_capabilities` |
| 8 | Escala | — | Diferido a F8 (D-35) |

**Extras:**
- `ruff check .` limpio y `exo validate` sin advertencias.
- **Fixtures con verdad conocida:** `py-invoices` (FastAPI, 1114 líneas), `node-shop` (Express y React con TypeScript, 1306) y `java-library` (Spring, 1256). Su verdad conocida vive afuera, en `tests/fixtures/ground-truth/`, así el agente de la corrida real no lee la respuesta. Los escribieron tres subagentes en paralelo, con la lista obligatoria de casos difíciles.
- **`tests/_git.py`** reemplaza cinco helpers `_git` duplicados y da historias con fechas y autores fijos.
- **`.npmrc` no es un archivo de credenciales:** muchos repos lo versionan solo con la URL del registro, y bloquearlo en el `pre-commit` rompía proyectos legítimos. Un token adentro lo sigue viendo el escáner.
- **Al subir la versión** (0.2.0, hito M3), el install editable se reinstala en los dos venvs (`uv pip install --offline --no-deps -e .`), y los goldens cambian solo en la versión del lock y en el encabezado del registro de skills.
- **Un fallo intermitente en Python 3.10:** `test_check.py::test_base_revisa_el_change_archivado_en_el_diff` (de F4) falló una vez en una suite completa que corría junto con la corrida real. No se reprodujo en otras dos suites completas ni en cuatro corridas sueltas, y no quedó el traceback. La sospecha es el `rename` de una carpeta recién escrita en Windows, pero no está confirmada.

**Corridas reales** (`docs/checklists/F6-adopcion.md`):
- **La primera**, con el contenido de antes de la revisión, cumplió los criterios 3 a 5. También mostró tres huecos del contenido: la re-auditoría parcial, `speclint` sobre la carpeta de capacidades y una unidad bloqueada que dejaba a R4 sin salida.
- **La segunda**, con el contenido final, cumplió los criterios 3 a 5 y usó los comandos nuevos: `skip` para la unidad de auth, `synthesized` para cada capacidad, la muestra entera en una sola auditoría y el commit en una rama de adopción como paso siguiente. Mostró dos cosas más, corregidas con su test o en el contenido:
  - `done` tomaba la puntuación que sigue a un `[Doc] path` como parte de la ruta;
  - una unidad de infraestructura sin capacidad (las migraciones) mandaba la reanudación a R4 sin fin.

**Revisión final con contexto fresco** (dos subagentes: motor y contenido). Todo lo que encontraron se corrigió con su test, salvo L13, que queda como limitación:
- **Motor (4 High, 9 Medium, 13 Low):**
  - commitear los resultados cambiaba el inventario y el churn;
  - un checkout con `core.autocrlf` daba otros hashes y reescribía los archivos;
  - una unidad cuyo conjunto de archivos cambió en un replan seguía cerrada;
  - un archivo de código o una spec que no es UTF-8 rompían el pipeline;
  - la relajación de severidad valía para specs sin `Status:`;
  - imports de varios nombres, `extends` de `tsconfig` y TOML con corchetes adentro de strings;
  - `build`, `coverage` u `out` se excluían también adentro del código (ahora, solo en la raíz o junto a un manifiesto), y el recorrido seguía links;
  - `done` salteaba un párrafo suelto sin evidencia, y aceptaba un `[Doc]` a un archivo de credenciales;
  - el chequeo de rutas permitidas tenía huecos (renombres, un proyecto en una subcarpeta del repo) y tomaba el lock del índice de git (ahora usa `--no-optional-locks`);
  - la cobertura contaba veredictos de una muestra vieja;
  - además, un `TypeError` previo en `graph._join(".", ".")`.
- **Contenido (3 High, 7 Medium, 10 Low):**
  - una unidad que no se podía cerrar trababa el pipeline;
  - el chequeo final usaba `speclint` sobre la carpeta de capacidades;
  - una capacidad stale se perdía al cerrar otra vez sus unidades;
  - la tabla de Resume no salía de `status`, y `reopen --capability` no tenía fallback;
  - la re-auditoría era parcial;
  - R6 rompía el chequeo de solo lectura;
  - el `@archivo` sin comillas en PowerShell;
  - el contenido prometía un escáner de PII que no cubre todo;
  - la regla de memoria siempre activa chocaba con D-37;
  - formatos desalineados con `context-template` y la plantilla de ADR.
- **Lo que el contenido corregido necesitó del motor** (E1 a E5):
  - `exo discover skip <unidad> --reason`;
  - `exo discover synthesized <capacidad>`, con su registro en `discovery/capabilities/` (resuelve L10: la señal stale ya no se pierde);
  - `status` con lo que falta para cerrar la adopción;
  - el fallback de `reopen --capability` a su `Source:`;
  - specs que no son UTF-8 con un aviso en vez de traceback.

**Decisiones tomadas durante la fase:**
- **D-33** (del dueño): el pack `discovery` se ofrece solo si el repo ya tiene código.
- **D-34** (del dueño): `.exo/discovery/` se commitea.
- **D-35** (del dueño): la prueba de escala, a F8.
- **D-14 y D-19,** cerradas con su default: parsers heurísticos con stdlib, y sin build ni tests del proyecto.
- **D-36:** `exo uninstall` conserva `discovery/` y `context.md`.
- **D-37:** las skills de discovery no escriben memoria.
- **ADR-0015:** estado en el repo, evidencia verificable y specs as-is.

**Desvíos respecto del plan y por qué:**
- **Fixtures de 1,1 a 1,3 mil líneas,** en vez de 2 a 3 mil. Alcanzan para los casos difíciles y la suite no se alarga.
- **Sin escritura de memoria** (D-37, F6:33): lo commiteado es la fuente compartida, y la memoria es por usuario (ADR-0009).
- **Pack `design` adelantado desde F7,** con `architecture-decision-record`, para los ADRs recuperados.
- **Comandos que el plan no nombraba:** `next`, `done`, `skip`, `reopen`, `synthesized`, `sample`, `audit` y `coverage`. Salieron del bucle por CLI (ADR-0005), de la revisión y de la corrida real. Solo `status` es tool (`discovery_status`): los demás escriben.
- **Sin `state.json`:** el estado de cada unidad y de cada capacidad se deriva de sus registros, así dos ramas no se pisan.
- **Criterio 7:** una capacidad es stale desde su registro de `synthesized`, no desde el estado de sus unidades. Así la señal dura hasta que se re-sintetiza.

**Limitaciones conocidas:**
- **IDs con colisión de slug (L13):** si aparece `src/user_profile` junto a `src/user-profile`, en un replan la unidad ya cerrada cambia de ID y vuelve a pendiente. Solo pasa con `--replan`.
- **Parsers heurísticos** (D-14): no ven imports dinámicos ni alias que no están en la config.
- **Subagentes de solo lectura:** el texto de cada unidad pasa dos veces por el contexto del orquestador. En los fixtures alcanza; F8 evalúa un extractor que escriba solo su unidad.
- **Permisos del agente:** en las dos corridas, Claude Code no pudo leer `src/invoices/auth/tokens.py`. En la primera pidió un permiso que nadie podía dar; en la segunda lo bloqueó una regla de denegación que no está en el repo ni en la config del usuario. Es una protección del harness, no del motor: el contenido saltea la unidad con su razón y la deja como pregunta abierta.
- **Copilot:** no se corrió (opcional).
- **Cierre local sin remoto**, según la regla del principio de este archivo.

### F7 — Packs de stack y resto del catálogo — 2026-11-17

**Entorno:**
- Windows 11, con Python 3.14.5 (`.venv`) y Python 3.10.20 (venv con `uv`, sin extras).
- Linux Ubuntu 24.04 en WSL2, con Python 3.12 de `uv`, sobre un clon limpio de la rama.
- Claude Code 2.1.325 para los evals, con `claude -p` sobre copias de los fixtures.
- Los datos aislados con `EXO_DATA_DIR` y `EXO_MEMORY_DB`.

**Resultados:**

| Entorno | Resultado |
|---|---|
| Windows, Python 3.14 | 1702 passed y 6 skipped (POSIX y extras de memoria), cobertura 93,76 % |
| Windows, Python 3.10 sin extras | 1696 passed y 12 skipped (POSIX, symlinks y extras de memoria), cobertura 93,49 % |
| Linux | 1699 passed y 9 skipped (extras de memoria que no están), cobertura 93,52 %; `ruff check .` limpio y `exo validate` «12 packs, 106 skills, 6 subagents, 16 shared contracts: all valid» |

**Lo que se escribió:** las 65 skills de F7 (de 41 a 106), en 12 packs. Seis packs son nuevos: `product`, `frontend`, `java`, `python`, `ops` y `agentic`.

| Prioridad | Skills | Packs |
|---|---|---|
| 1 | 15 | `sdd` (overlay SPDD: 5), `quality` (jueces, comité y 4R: 6), `product`, `frontend` y `core` (4) |
| 2 | 23 | `java` (10), `python` (2), `frontend` (11): los stacks del equipo, en el orden de D-38 |
| 3 | 11 | `ops` (10) y `security` (`secure-diagram-sanitizer`) |
| 4 | 16 | `product` (4), `design` (4, con el contrato `executive-style.md`), `agentic` (2) y `core` (6) |

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Contenido válido | `exo validate` | OK: «12 packs, 106 skills, 6 subagents, 16 shared contracts: all valid», sin advertencias |
| 2 | Degradación correcta | `pytest -k criterio_2 tests/test_f7_degradation.py` | OK (9 passed). Para cada pack opcional del ciclo, con el pack instalado cada skill que nombra el mapa está en el bundle y en el registro; sin él, el mapa instalado trae su fila de degradación con la frase exacta. Los packs sin skills en el mapa (`agentic`, `ops`, `python`) están en una lista explícita |
| 3 | Evals | `pytest -m agent_e2e tests/test_skill_evals.py`, con Claude Code real | OK: 117 de 117 casos con el contenido final (las 38 skills de prioridad 1 y 2, más `pre-commit-review`, con `trigger`, `no-trigger` y `output` cada una). Claude Code 2.1.325, con el runner aislado de la config de usuario: ninguna de las 20 skills de usuario de esta máquina quedó visible. 115 pasaron a la primera. Los otros dos pasaron después de su arreglo: el `output` de `prompt-code-sync` encontró un defecto real (después de corregir la lógica de un canvas aprobado, el gate quedaba `APPROVED`; ahora queda pendiente al instante), y el de `chained-pr` tenía un chequeo de texto demasiado literal. Revisé cada resultado: la skill cargada, la respuesta y los archivos escritos |
| 4 | Instalación por stack | `pytest -k criterio_4 tests/test_stack.py` | OK (8 passed). Sobre los cuatro fixtures, con y sin git: `py-invoices` y `toy-python` sugieren `python`, `java-library` sugiere `java` y `node-shop` (monorepo) sugiere `frontend`. `exo init --yes` sobre una copia de `node-shop` instaló `frontend` y `ops` |

**Extras:**
- `ruff check .` limpio. `exo p0` en una copia de `node-shop` con `exo init`: «P0 GATE: PASSED (3/3)».
- **Motor:**
  - canvas SPDD (`canvas.md`, siete secciones, IDs cruzados también sin `spec.md`);
  - gates condicionales (`exo check` revisa todo gate presente, exige `prompt_spec_review` con canvas, y un gate ilegible ya no aborta el chequeo);
  - detección de stack en monorepos (`files.project_names`, sin terceros, muestras, borrados ni links);
  - `exo uninstall` conserva `.exo/brand.json`.
- **`review` pasa a `pre-commit-review`** (D-40). En un proyecto de F5, `exo sync` borra la carpeta vieja (es del lock) e instala la nueva.

**Cómo se escribió:** el motor, los contratos y la integración con el ciclo los escribí yo. Las skills las escribieron subagentes, tres por tanda (P1, P2, y P3 con P4), en worktrees manuales, con un brief común y un anexo por tanda que recogía lo aprendido. Las integré con cherry-pick.

**Evals (D-41):**
- **El runner** (`tests/test_skill_evals.py`, `agent_e2e`, fuera de la suite normal):
  - copia el fixture con historia git y corre `exo init` con los packs del eval;
  - trabaja en una rama `feat/<skill>-eval`;
  - corre `claude -p` con `stream-json`, aislado de la config de usuario (`--setting-sources project,local`, `--strict-mcp-config`);
  - detecta la skill por la tool `Skill` o por la lectura de su `SKILL.md`.
- **Los tres casos por skill:** `trigger`, `no-trigger` y `output`, con chequeos sobre la respuesta y los archivos.
- **Primera pasada** (antes de la revisión final):
  - P1: 45 de 45, después de corregir seis evals mal planteados y un corte por tiempo de `review-4r`. Las seis correcciones fueron:
    - un `no-trigger` cuyo estado hacía aplicar la skill de verdad;
    - chequeos de texto demasiado literales.
  - P2: 67 de 69. Los dos fallos fueron `output` de Java que pedían implementar algo no trivial: el agente abrió un change SDD, como manda el `AGENTS.md` instalado.
- **En las 114 corridas** de la primera pasada no se cargó ninguna skill que no fuera de exo.
- **La corrida final**, con el contenido después de la revisión, está arriba (criterio 3).

**Revisión final con contexto fresco** (tres subagentes: motor, contratos y P1; P1 restante y P2; P3 y P4). Encontraron 1 High, 34 Medium y 73 Low. Cuatro subagentes los arreglaron todos, con test cuando tocaban el motor; ninguno resultó falso positivo.
- **High:** el modo secuencial de `parallel-dispatch` corría apply en la sesión del orquestador. Ahora usa un `sdd-implementer` por unidad.
- **Motor:**
  - la detección de stack fallaba en un proyecto ignorado por un repo padre;
  - un gate en UTF-16 abortaba `exo check`;
  - el canvas sin `spec.md` no cruzaba IDs;
  - el runner no aislaba la config de usuario de Claude Code y no validaba rutas de Windows en `setup`;
  - `test_f7_degradation` pasaba vacío para tres packs.
- **Contratos y ciclo:**
  - el orquestador no conocía el overlay SPDD (canvas en Tier 1 y 2, ediciones del canvas desde apply);
  - un refactor del canvas daba un gap High;
  - qué pasa si un proyecto lista un gate condicional en `governance.gates`;
  - `context-anchor.md` no lo leía ninguna fase;
  - los criterios inline copiados eran los viejos;
  - el comité convocaba jueces sin entrada;
  - las skills de gates condicionales no se cargaban en Tier 1.
- **Packs de stack:**
  - una tabla única CWE → OWASP Top 10:2025 (`.exo/shared/owasp-2025.md`), verificada contra top10.owasp.org;
  - escáneres alineados en severidad y formato;
  - `pip-audit -r` y `npx` que podían instalar paquetes;
  - Spring Boot 4 y Security 7 (con fuentes);
  - un `@ExceptionHandler(Exception.class)` que se tragaba los 4xx;
  - disparadores de los revisores que pisaban a `pre-commit-review` y `sdd-verify`;
  - evals sin `quality` ni `security`.
- **P3 y P4:**
  - `incident-response` permitía leer Secrets de Kubernetes;
  - el sanitizador dejaba datos personales hacia el mismo equipo;
  - `exo change record` desde un subagente;
  - una regla única para documentos del proyecto fuera de la carpeta del change;
  - dos estilos "neutros";
  - el marcador de estilo contaba antes de la aprobación;
  - disparadores que se pisaban (diagramas, logs, skills).

**Decisiones tomadas durante la fase:**
- **D-38** (del dueño): los stacks del equipo son Java, Python y frontend, en ese orden.
- **D-39** (del dueño): las skills de Jira se generalizan como `work-item-creator` y `refinement-assistant`.
- **D-40** (del dueño): `review` pasa a `pre-commit-review`.
- **D-41** (del dueño): todos los evals de prioridad 1 y 2 se corren con Claude Code real.
- **D-18:** se cerró con su default.
- **D-12, resto:** `.exo/brand.json` opcional, y las herramientas corporativas son opcionales.
- **D-42:** nombres en inglés.
- **D-43:** gates condicionales.
- **D-44:** el escaneo de Python va en `security-scan-jkp`.
- **ADR-0016.**
- **De la revisión:**
  - los documentos del proyecto se escriben durante un change con aprobación y listados en el plan (`sdd-phase-common` §C);
  - toda cita de OWASP lleva el año;
  - un gate condicional listado en `governance.gates` se vuelve gate del tier;
  - `context-anchor.md` y `pr-part-<n>.md` son los dos archivos fuera de las fases.

**Desvíos respecto del plan y por qué:**
- **P3 y P4 sin evals:** el plan los pide solo para prioridad 1 y 2.
- **Skills de `ops`, `design`, `agentic` y la mayoría de P4 fuera del mapa de fases,** como en el reporte: se cargan por su `description` o a pedido. Sumarlas competiría con el tope de 5 skills por delegación.
- **`security-scan-jkp` sigue en `java`** (D-44). Un proyecto solo Python escanea con el criterio inline de su fila de degradación.
- **`exo-permissions`:** se unificó con el vocabulario que ya tenía el contenido (`write-code`, `write-specs`, `read-only+tests`…) en lugar de un `read-write` genérico.

**Limitaciones conocidas:**
- **OWASP:** el pack `security` (F5) sigue en el Top 10:2021, verificado entonces contra CWE; los packs de stack usan 2025. Toda cita lleva el año y la tabla compartida da la equivalencia, pero falta migrar `security` a 2025.
- **Los evals miden el modo degradado de las herramientas:** el runner no puede correr `mvn`, `npm`, `pip` ni `pytest`, así que nunca se ve una corrida real del build, de los tests ni de los escáneres.
- **Evals de "no dispara":** dependen de cómo Claude Code elige skills por su `description`. Un cambio de versión del agente puede moverlos.
- **Spring Boot 4:** lo que el subagente no pudo confirmar contra las fuentes quedó marcado `[Not verified]`.
- **Convención nueva a revisar:** la aprobación de primer uso del estilo ejecutivo (memoria más el marcador `exo-style:` en los diagramas). No toca el motor.
- **Copilot:** no se corrió (opcional).
- **Cierre local sin remoto**, según la regla del principio de este archivo.

### F8 — Endurecimiento, evals y distribución (v1.0) — 2026-11-25

**Entorno:**
- Windows 11, con Python 3.14.5 (`.venv`) y Python 3.10.20 (venv con `uv`, sin extras).
- Linux Ubuntu 24.04 en WSL2, con Python 3.12 de `uv`, sobre una copia de la rama en el disco de Linux.
- GitHub Actions (D-45, ADR-0017): Windows, macOS y Linux con Python 3.10 a 3.13, más los jobs de extras de memoria, instaladores y build.
- Claude Code 2.1.325 y GitHub Copilot CLI 1.0.114 para los escenarios, con la config de usuario aislada.
- Los datos aislados con `EXO_DATA_DIR` y `EXO_MEMORY_DB` en toda corrida manual o de agente.

**Resultados:**

| Entorno | Resultado |
|---|---|
| Windows, Python 3.14 | 1984 passed y 15 skipped (POSIX, extras de memoria y un caso de rutas), cobertura 93,79 % |
| Windows, Python 3.10 sin extras | 1978 passed y 21 skipped (además, los extras de memoria que no están), cobertura 93,54 % |
| Linux (WSL) | 1987 passed y 12 skipped (los de Windows y los extras de memoria que no están), cobertura 93,71 %; `ruff check .` limpio, `exo validate` «12 packs, 106 skills, 6 subagents, 20 shared contracts: all valid» y `exo validate --docs . --docs docs/guides` «11 files, 17 count markers, 369 commands: all valid» |
| GitHub Actions | [corrida 45666950140](https://github.com/julimonte03/exo-harness/actions/runs/45666950140): 19 de 19 jobs en verde (tests en Windows, macOS y Linux con Python 3.10 a 3.13, extras de memoria, instaladores y build) |

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | Instalar y adoptar en menos de 2 minutos | El instalador remoto real (`irm …/install.ps1 \| iex`, con `EXO_REF=feat/F8-v1`) y `exo init --agents <agente> --yes`, cronometrados (`docs/checklists/F8-v1.md`) | OK: Claude Code 56,4 s con uv y 67,1 s sin uv (venv y pip desde git); Copilot 27,9 s. `exo doctor` sin errores, y cada agente lista las skills del proyecto |
| 2 | Un segundo agente sin romper el primero | `exo add-agent copilot` sobre el repo de Claude Code, y los goldens `claude-copilot__*` (`tests/test_adapters.py`) | OK: 3,6 s. Cambian solo `.exo/config.json` y `.exo/lock.json`, porque Copilot lee las mismas `.claude/skills/` y `.claude/agents/`. `exo doctor` sin errores |
| 3 | Ciclos Tier 1 y Tier 3 válidos, con Claude Code y con Copilot | `pytest -m agent_e2e tests/test_agent_scenarios.py` | 5 de 6 OK: Tier 1, Tier 3 y adopción `quick` con Claude Code; Tier 1 y adopción `quick` con Copilot. **El Tier 3 de Copilot quedó parcial** (D-50): hizo todas las fases hasta verify, con sus subagentes, pero no archivó. El verify quedó `blocked` por un riesgo que tenía que aceptar el `tech_lead`, Copilot `-p` deniega sin preguntar los comandos compuestos, y la cuenta se quedó sin cuota antes de la última reanudación |
| 4 | Ingeniería inversa con cobertura ≥ 80 % y precisión ≥ 90 % | `/exo-adopt` en `standard` con Claude Code sobre una copia de exo (`git archive` de `bc96270`), y `coverage.md` | OK: 19 de 19 módulos (100 %), 178 de 178 requisitos con evidencia, 100 % de precisión en las 11 capacidades (30 FR del re-auditor). La auditoría independiente (15 FR al azar fuera de la muestra, con contexto fresco) dio 15 de 15 |
| 5 | Memoria con decisión documentada | ADR-0010 vigente, y `pytest --no-cov -m perf tests/test_perf.py` | OK: ADR-0010 sigue vigente (la búsqueda híbrida es el default por un experimento con la regla congelada antes). Los 9 tests de rendimiento pasan: `exo init` < 10 s, `exo sync` sin cambios < 1 s, `exo discover inventory` y `structure` sobre 50 mil líneas < 30 s, y la búsqueda léxica con p95 < 150 ms sobre 5000 memorias. Sobre exo mismo (81 mil líneas), `inventory` tardó 16,3 s en frío y 5,4 s en caliente |
| 6 | CI verde en los tres sistemas y Python 3.10 a 3.13, con cobertura ≥ 85 % | GitHub Actions, `ci.yml` | OK: [corrida 45666950140](https://github.com/julimonte03/exo-harness/actions/runs/45666950140), 19 de 19 jobs en verde. La cobertura de la suite queda en 93,5 % a 93,8 % según el entorno (mínimo 85 %). El PR a `main` vuelve a correrla sobre la historia reescrita |
| 7 | Actualización segura | `pytest --no-cov -k criterio_7 tests/test_update.py` | OK (6 passed): `exo update` de 0.2.0 a 1.0.0 sobre un proyecto instalado conserva lo editado, reporta los conflictos, muestra el renombre de `review` y no borra huérfanas sin `--prune` (sin TTY nunca pregunta ni borra; en una terminal pregunta antes); `--json` da la misma información |
| 8 | Threat model actualizado | `docs/seguridad/threat-model-motor.md` | OK: las 11 superficies del alcance, 52 amenazas con su mitigación o su riesgo aceptado. 593 citas `path:line` y 32 commits verificados contra `f764784`. Ningún residual Crítico: 8 Altos (TM-1, TM-4, TM-5, TM-11 y TM-12, de la cadena de suministro, que bajan con los ajustes de GitHub del checklist; TM-16 y TM-20, pendientes de M-3 y M-2; TM-26, aceptado en ADR-0009), 8 Medios y 36 Bajos |

Checklist manual: `docs/checklists/F8-v1.md`, con los criterios 1 a 4 en detalle y los pasos del release. Los checklists de Copilot pendientes de F2 a F7 no se corrieron porque la cuota de Copilot se terminó con los escenarios: quedan como deuda (D-50).

**Lo que se escribió:**
- **Actualización:** `exo update` (vista previa por defecto, `--apply`, `--prune` y `--force`; una skill que choca queda entera como estaba), migraciones del lock, `exo sync` que ya no borra huérfanas sin `--prune`, y un guard que no lleva un proyecto a una versión anterior del motor.
- **Distribución:**
  - los instaladores remotos (`curl … | sh` e `irm … | iex`) desde GitHub, con `EXO_REF`, el wheel verificado contra `SHA256SUMS` y solo `https`;
  - `release.yml` con tests, build, checksums, el release de GitHub y PyPI por trusted publishing;
  - la licencia MIT (D-49).
- **CI:** GitHub Actions con la matriz de 12 jobs más extras, instaladores y build; las actions fijadas por SHA, Dependabot y anotaciones de los tests que fallan.
- **Rendimiento:** `tests/test_perf.py` (marker `perf`, en la suite normal). Un `sync` sin cambios ya no corre git para los hooks y cachea los links.
- **Seguridad:** el threat model del motor (52 amenazas, STRIDE), y sus mitigaciones:
  - el permiso de Claude Code solo para los subcomandos que las skills corren solas;
  - `exo gate publish` corre solo un comando aprobado en esa máquina, para ese proyecto y con los archivos que corre;
  - los embeddings sin redirects;
  - los datos de usuario privados en POSIX;
  - los runners de evals sin red para git y sin `git push`.
- **Opcionales:** `exo status` enriquecido, las personas (ADR-0018), el pack `security` en OWASP Top 10:2025 y `exo validate --docs`.
- **Documentación de usuario en inglés** (D-48): README, QUICK-START, CONTRIBUTING, CHANGELOG y las guías de `docs/guides/`.
- **Escenarios con agentes reales:** `tests/test_agent_scenarios.py` y `tests/_agents.py`, con Claude Code y Copilot CLI.

**Revisión final con contexto fresco** (tres subagentes: el motor; la distribución, la CI y la seguridad; el contenido y los docs). Encontraron 60 hallazgos: 6 High, 23 Medium y 31 Low. Los 6 High eran 4 problemas distintos. Tres subagentes los arreglaron todos, cada arreglo del motor con su test; ninguno resultó falso positivo.
- **High:**
  - la aprobación de `publish_command` fijaba solo el texto del comando, para cualquier repo: ahora queda atada al proyecto, al texto y al SHA256 de los archivos del proyecto que el comando nombra (en Windows, también los que `cmd` busca por `PATHEXT`);
  - `exo sync`, `init` y los comandos de agentes llevaban un proyecto a una versión anterior del motor sin avisar;
  - en modo automático, un hallazgo Medium o Low no dejaba archivar: ahora se aplaza a un followup, `pr.md` lo lista en "Known followups" y hay a lo sumo dos rondas de retrabajo;
  - el overlay `qa` relajaba una regla (un test que falla bloquea `ready` igual).
- **Medium y Low, entre otros:**
  - el proxy del sistema con `openai-compatible` local;
  - los permisos privados como best-effort en discos FAT;
  - la config que reescribe el motor conserva el estilo de la persona;
  - los colores de `exo status` en Windows;
  - `uninstall.ps1` con la salida redirigida;
  - git sin transporte de red en los runners;
  - el runner de escenarios borra la copia de la cuenta de Copilot y exige que `check` vea el change;
  - un solo formato de cita OWASP;
  - y varias citas viejas del threat model.

**Decisiones tomadas durante la fase:**
- **D-22** (del dueño): repo público en GitHub.
- **D-35** (del dueño): la prueba de escala se hace sobre el propio exo.
- **D-17** (del dueño): overlays de persona → ADR-0018.
- **D-45 a D-48:**
  - D-45: la CI pasa a GitHub Actions (ADR-0017);
  - D-46: la historia se limpia antes del primer push;
  - D-47: Copilot CLI en esta máquina;
  - D-48: la documentación de usuario en inglés.
- **D-49** (del dueño): licencia MIT.
- **D-50** (del dueño): se cierra con el Tier 3 de Copilot parcial y sus checklists como deuda.
- **D-51** (del dueño): cada fase cierra con un PR a `main` que el dueño mergea con la CI en verde.

**Desvíos respecto del plan y por qué:**
- **Copilot:** el Tier 3 quedó parcial y los checklists de F2 a F7 no se corrieron, por la cuota (D-50).
- **El merge a `main`** no es local: lo hace el dueño en GitHub con un PR (D-51).
- **La historia se reescribe una segunda vez** al cierre, para sacar un resto del nombre de una herramienta de origen que quedó después de D-46. Los hashes citados en los docs se remapean en el mismo paso.
- **PyPI:** el workflow está listo, pero publicar depende de que el dueño configure el trusted publisher y el environment `pypi` (checklist de release).

**Limitaciones conocidas:**
- **TM-20 y TM-16 quedan en Alto**, pendientes de M-2 y M-3. En la CI, la aprobación de `publish_command` fija solo el texto, y la protección depende de que el pipeline siga el contrato `ci-and-review`.
- **Copilot CLI 1.0.114 con `-p`** deniega sin preguntar las cadenas con `;`, `git --no-pager`, los rangos `a...b` y los scripts de PowerShell con variables. Las skills se pueden quedar a mitad en corridas desatendidas.
- **Que Claude Code aplica `permissions.allow` recién con el workspace confiable** está verificado en sesión interactiva, no en `-p`.
- **El ajuste de GitHub** (rulesets, environments, la inmutabilidad de los releases) es un checklist para el dueño, no lo hace el motor.
