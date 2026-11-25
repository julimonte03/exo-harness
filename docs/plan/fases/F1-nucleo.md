# F1 — Núcleo determinista

## Objetivo

Portar a stdlib todo lo determinista del runtime del reporte (capítulos 04, 05 §5.2–5.4 y 10 §10.5), sin adaptadores de agentes ni memoria. Al terminar, el motor ya sabe leer packs y skills, validar contenido, clasificar riesgo, lintear artefactos, hacer snapshots seguros, fusionar bloques en archivos y servir tools por MCP.

## Depende de

F0 cerrada.

## Alcance

Entra: `core/*`, `packs/`, registry, fitness, speclint con plantillas, observabilidad de solo lectura, validador del contenido, doctor base, servidor MCP con los grupos *Skills* y *Observabilidad*, CLI de esos comandos, y contenido mínimo para poder testear.

No entra: adaptadores, instalación en proyectos (F2), memoria (F3), skills reales (F4 en adelante).

## Entregables y contratos

**`core/fsutil.py`.** `write_atomic(path, data: bytes)` con temporal en el mismo directorio + `os.replace`; `sha256_file`, `sha256_bytes`; `safe_relpath(p)` que rechaza `..`, rutas absolutas y letras de unidad (comportamiento de `config.py` del reporte). Escrituras siempre en binario: las skills se copian byte a byte y los archivos del humano conservan sus fines de línea (CRLF incluido).

**`core/frontmatter.py`.** Parser de un subconjunto de YAML suficiente para el estándar Agent Skills: escalares, strings con comillas simples y dobles, listas, un nivel de mapa anidado (`metadata`) y bloques `|` y `>`. Modo estricto para el validador: todo lo que esté fuera del subconjunto es error con número de línea.

**`core/config.py`.** Esquema 1 de `.arnes/config.json` (ver `02-ARQUITECTURA.md` §2.12). Lectura tolerante con defaults silenciosos, escritura atómica, saneo (`prefix` con `^[A-Z][A-Z0-9]*$`, `specs_dir` relativo y seguro) y función de migración por número de esquema.

**`core/filemerge.py`.** `inject`, `replace`, `remove`, `list_blocks` para bloques `<!-- BEGIN:arnes:<id> -->` … `<!-- END:arnes:<id> -->` y la variante con `#` para TOML/YAML. Idempotente: si el resultado es igual al contenido actual, no escribe. Backup opt-in.

**`core/structmerge.py`.** `merge_json_key(path, dotted_key, value)` que solo toca esa clave y devuelve error tipado si el archivo no es JSON válido (por ejemplo JSONC con comentarios), sin modificarlo.

**`core/lock.py`.** Lectura y escritura de `.arnes/lock.json`, entradas `{path, kind, owner, sha256, block_id?, key?}`, y `drift(project)` que devuelve archivos modificados a mano.

**`core/snapshots.py`.** Port del comportamiento del reporte: tar.gz determinista (entradas ordenadas, uid/gid/mtime normalizados, gzip con `mtime=0`), deduplicación por hash, `prune(keep=5)` respetando `pins.json`, `pin`/`unpin`, `restore` que snapshotea el estado actual antes de restaurar, y extracción segura que rechaza path traversal, links y devices.

**`packs/`.** Carga de `pack.json`, validación, resolución de `requires` en orden topológico con detección de ciclos, descubrimiento de skills (carpetas con `SKILL.md`) y de subagentes.

**`registry.py`.** Render de `.arnes/skill-registry.md` a partir del frontmatter (nombre, descripción, pack, ruta).

**`sdd/fitness.py`.** (Desde D-52, ADR-0019, son tres tiers: lo que acá da Tier 4 pasa a dar Tier 3, y las ceremonias son `minimal`, `light` y `full`. Lo cambia F9.) Port exacto del motor del §4.8: siete dimensiones (`blast_radius`, `component_criticality`, `security_data_sensitivity`, `reversibility`, `files_modules_footprint`, `test_maturity_gap`, `regulatory_compliance_impact`) con valores 0–3; reglas FM-01, FM-02, FM-03 (Tier 4), FM-10, FM-11, FM-12, FM-13 (Tier 3), FM-20 (Tier 2), FM-30 (Tier 1); evidencia faltante o ilegible da Tier 4; `compare_tiers(actual, propuesto)` devuelve upgrade, downgrade o igual; mapeo tier → ceremonia (`minimal`, `light`, `full`, `full`) según §6.3. Crear también `content/packs/sdd/skills/risk-tiering/references/classification-rules.md` con la tabla de reglas, y un **test de paridad** que compare el código con ese Markdown (como `RULE_TIERS` en el reporte).

**`sdd/speclint.py` + `sdd/templates/`.** Cinco tipos: `functional` (proposal/spec), `technical` (design), `test-spec`, `verify-record`, `pr`. Las plantillas se escriben ahora a partir de lo que el reporte sí detalla: secciones de `design.md` (§6.7: Architecture Overview, Modules / Files, Data Shapes, Sequence Of Operations, Error Handling, Test Plan, Migration / Backwards Compatibility, Risks & Mitigations), salida de `sdd-verify` (§6.7: Verdict, Spec Coverage, Scenario Coverage, Issues Found, Tests, Out-of-Scope Drift, Judgment Day Handoff, Gate summary) y cuerpo del PR (§7.2: Summary, Ticket, Changes, Test Plan, Checklist). El lint verifica encabezados obligatorios, formato de IDs (`FR-n`, `NFR-n`, `S-n`) y referencias cruzadas (cada `S-n` del spec aparece en el Test Plan del diseño). Salida humana y `--json`.

**`sdd/observability.py`.** Port de solo lectura del §5.4: recorre `<specs_dir>`, detecta épicas, changes y `archive/`, deriva la fase por los artefactos presentes, lee `ai-usage-record.json` y `followups.json`, aplica los descartes y proyecta `jira_key` (renombrado `ticket_key`) y `attribution_schema_version` aunque sean null.

**`validate.py` (`arnes validate`).** Reglas del §10.5 adaptadas: manifiestos de pack (nombre kebab-case igual a la carpeta, semver, descripción); frontmatter de cada skill según el estándar (nombre igual a la carpeta, hasta 64 caracteres, descripción de hasta 1024, nombres únicos en toda la colección, sin escapes `\uXXXX` literales); referencias `skill:<nombre>` resolubles y declaradas en `requires`/`optional` del pack; archivos de `references/` citados existen; `content/rules/AGENTS.base.md` de hasta 60 líneas; patrones de secretos fuera de bloques de código; aviso si un `SKILL.md` supera 500 líneas.

**`doctor.py`.** Chequeos base: versión de Python, plataforma, encoding de stdio, versión del motor, ejecutable en el `PATH`, contenido embebido presente, espacio en disco, auto-test de filemerge y de determinismo de snapshots. F2 y F3 agregan sus chequeos.

**`mcp/server.py` + `mcp/tools/`.** JSON-RPC 2.0 por stdio, un mensaje por línea, `initialize` → `tools/list` → `tools/call`, logs a stderr, errores de dominio con `isError: true`. Validadores S2: `validate_cwd` (`resolve()` + `is_relative_to`), `validate_skill_name`, `validate_change_name`. Tools de esta fase: `skills_list`, `skill_info`, `skills_diff`, `list_changes`, `get_change_state`, `get_followups` (`status`: `open`/`dismissed`/`all`), `get_ai_usage_record`.

> **Implementado según ADR-0005 (D-23):** las tools se definen una sola vez en `src/exo/tools/registry.py`, cada una con su subcomando del CLI (`exo skills …`, `exo change …`). Los validadores S2 están en `src/exo/tools/validation.py`, y `src/exo/mcp/server.py` es un adaptador opcional sobre ese registro.

**`cli.py`.** Subcomandos: `version`, `validate`, `registry`, `fitness classify --evidence-json`, `speclint <ruta> [--type] [--json]`, `doctor`, `mcp`, `backups {list,pin,unpin}`, `restore`, `inject`.

**Contenido mínimo.** `content/packs/core/pack.json`, `content/packs/sdd/pack.json`, una skill de prueba `hello-arnes`, `content/rules/AGENTS.base.md` provisorio y la referencia de fitness.

## Tareas (en orden)

1. `fsutil` + tests (incluye Windows: separadores, CRLF, rutas largas).
2. `frontmatter` + tests con casos válidos e inválidos.
3. `config` + migraciones + tests.
4. `filemerge` y `structmerge` + tests de idempotencia y de archivos inválidos.
5. `lock` + tests de drift.
6. `snapshots` + tests de determinismo y de extracción maliciosa (fixtures con traversal, symlink y device).
7. `packs` + `registry` + tests de ciclos y nombres duplicados.
8. `fitness` + test por cada regla FM, límites y paridad con el Markdown.
9. Plantillas + `speclint` + tests por tipo.
10. `observability` + tests sobre un árbol `specs/` de fixture.
11. `validate` + un fixture por cada violación.
12. `mcp` + tests por subprocess (protocolo real) y validadores S2 parametrizados.
13. `doctor` + `cli` + test que verifica que `src/arnes` no importa nada fuera de stdlib (análisis con `ast`, con excepción declarada para `memory/backends` y `memory/embeddings`).

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Suite verde con cobertura ≥ 85 % de `src/arnes` | `pytest --cov=src/arnes --cov-fail-under=85` |
| 2 | Fitness reproduce todas las reglas | `arnes fitness classify --evidence-json '{"security_data_sensitivity":3,...}'` devuelve Tier 4 con regla FM-01, y el test tabular cubre FM-01…FM-30 y el caso de evidencia ilegible |
| 3 | Snapshots deterministas | Dos snapshots del mismo árbol tienen el mismo SHA256 |
| 4 | Extracción segura | Los fixtures maliciosos se rechazan |
| 5 | MCP funcional | Test por subprocess: `initialize` y `tools/list` devuelven 7 tools con `inputSchema`; un `change_name` con `../` devuelve `isError: true` |
| 6 | Validador estricto | `arnes validate` pasa sobre `content/` y falla con mensaje específico en cada fixture de violación |
| 7 | Núcleo sin dependencias | El test de imports pasa |
| 8 | Idempotencia de filemerge | Inyectar dos veces el mismo bloque deja el archivo byte a byte igual y no lo reescribe |

## Referencias al reporte

§4.1 (módulos), §4.5 (flujo de sync), §4.6 (invariantes), §4.7 (config), §4.8 (fitness), §5.2–5.4 (MCP y observabilidad), §6.3 (ceremonias), §6.7 (salidas de design y verify), §7.2 (cuerpo del PR), §10.5 (validador).
