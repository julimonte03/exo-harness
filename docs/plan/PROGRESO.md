# Progreso de construcción

**Fase activa:** F0

Una fase está **terminada** cuando: todos sus criterios de aceptación pasaron con el comando exacto, la CI está verde en los tres sistemas operativos y el PR de la fase está mergeado.

## Estado por fase

| Fase | Estado | Rama / PR | Inicio | Cierre | Notas |
|---|---|---|---|---|---|
| F0 Fundaciones | En curso | `feat/F0-fundaciones` (sin remoto ni PR) | 2026-10-29 | | Criterios 1, 2, 4–7 OK. Falta el 3 (CI en GitHub): requiere crear el repo remoto (D-16, D-22) |
| F1 Núcleo | Pendiente | | | | |
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

Entorno: Windows 11, venv `.venv` con Python 3.14.5. La suite también se corrió con Python 3.10.20 (venv con `uv`).

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | El paquete se instala y responde | `pip install -e ".[dev]"`; `exo --version`; `python -m exo --version` | OK: los dos imprimen `exo 0.0.1` |
| 2 | Tests y lint verdes | `pytest`; `ruff check .` | OK: 8 passed, cobertura 96.55 % (umbral 80 %); ruff "All checks passed!" |
| 3 | CI verde en los 3 SO | Run de GitHub Actions del PR | **Pendiente**: no hay repo remoto. `.github/workflows/ci.yml` está listo (ubuntu/macos/windows × 3.10/3.13) |
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
