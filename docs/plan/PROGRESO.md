# Progreso de construcción

**Fase activa:** F2 (pendiente: decidir D-04, D-05, D-06 y D-16 y aprobar su plan).

Una fase está **terminada** cuando: todos sus criterios de aceptación pasaron con el comando exacto, la CI está verde en los tres sistemas operativos y el PR de la fase está mergeado.

**Mientras no haya repo remoto** (decisión del dueño, 2026-10-30): la fase se cierra en local. La suite y el lint se corren en Windows y en Linux (Ubuntu en WSL, sobre un clon limpio), y la rama se mergea a `main` con `git merge --no-ff`, sin push. La CI de GitHub Actions (incluido macOS) y el PR quedan diferidos. Cuando exista el remoto, se suben `main` y las ramas, y se verifica la CI de cada fase cerrada así.

## Estado por fase

| Fase | Estado | Rama / PR | Inicio | Cierre | Notas |
|---|---|---|---|---|---|
| F0 Fundaciones | Terminada (local; CI diferida) | `feat/F0-fundaciones`, mergeada a `main` en local, sin PR | 2026-10-29 | 2026-10-30 | Criterios 1, 2, 4–7 OK. Criterio 3: Windows y Linux en local OK; macOS y GitHub Actions diferidos hasta tener remoto |
| F1 Núcleo | Terminada (local; CI diferida) | `feat/F1-nucleo`, mergeada a `main` en local, sin PR | 2026-10-30 | 2026-10-30 | Criterios 1–8 OK en Windows (3.14 y 3.10) y Linux (WSL). D-23 → ADR-0005 |
| F2 Adaptadores + instalador | Pendiente | | | | |
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
