# 99 — Trazabilidad reporte → plan

Este archivo muestra que cada pieza del reporte transcripto tiene un destino: una fase del plan o un descarte con motivo.

## Piezas del reporte

| Reporte | Pieza | Destino |
|---|---|---|
| §1.2, §2.1 | 12 plugins por stack/disciplina + meta-plugin | Packs del instalador (`02-ARQUITECTURA.md` §2.5); el meta-plugin pasa a ser la opción "todos los packs" del wizard (F2) |
| §2.3 | Manifiestos `.devin-plugin/plugin.json`, `git-subdir`, `ref`/`sha` | `pack.json` (F1); el pinning pasa a la versión del motor en el lock (F2) |
| §2.5 | Referencias cross-plugin y degradación | `skill:<nombre>` + `skill-resolver.md` (F1 validador, F4 contrato) |
| §2.6 | AGENTS.md, MCP y runtime solo en core | Se conserva: reglas en `content/rules/`, un único servidor MCP (F1) |
| §3 | Anatomía de skill y campos de frontmatter | Formato canónico del estándar + `metadata` (`02-ARQUITECTURA.md` §2.6) |
| §3 | Contratos `_shared/` | `content/shared/` → `.arnes/shared/` (F4, F5) |
| §4.1 | Módulos del runtime | Ver tabla `02-ARQUITECTURA.md` §2.4 (F1, F2, F3) |
| §4.2 | 18 subcomandos del CLI | F1 (núcleo), F2 (instalación), F3 (`mem`), F4 (`change`, `specs`, `check`), F5 (`gate`, `p0`), F6 (`discover`), F8 (`update`) |
| §4.3 | Scopes `project`, `windsurf`, `global`, `windsurf-global` | Reemplazados por adaptadores + scope `project`/`user` (F2) |
| §4.4 | Resolución de fuentes de skills | Contenido embebido en el paquete + `ARNES_CONTENT_ROOT` para desarrollo (F1) |
| §4.5 | Flujo de sync con SHA256 y snapshots | Motor de operaciones (F2) sobre `snapshots.py` (F1) |
| §4.6 | 11 invariantes | Se conservan y se suman 6 (`02-ARQUITECTURA.md` §2.13) |
| §4.7 | `.devin/config.json` | `.arnes/config.json` esquema 1 (F1) |
| §4.8 | Motor de fitness y reglas FM | Port exacto + test de paridad (F1) |
| §4.9 | `setup.py`, wrappers | `pyproject.toml` + `install.sh`/`install.ps1` (F0, F2) |
| §5.1 | `.mcp.json` con bootstrap autolocalizante | Configs MCP generadas por adaptador con `arnes mcp` + doctor (F2) |
| §5.2 | Protocolo JSON-RPC stdio y validación S2 | F1 |
| §5.3 | 22 tools | Skills y observabilidad (F1), memoria (F3), discovery (F6) |
| §5.4 | Observabilidad read-only | F1 |
| §5.5 | engram + guard S1 | F3 |
| §5.6 | Convención de memoria para SDD | `memory-convention.md` (F4) |
| §6.1–6.7 | Roles, fases, tiers, mapa fase → skills, contrato común, delegación, contratos de salida | F4 |
| §6.8 | SPDD (REASONS Canvas) | F7 prioridad 1 |
| §6.9 | Ejemplo `specs/ONBRDN-11044-…` | Se reemplaza por los fixtures del motor y por el dogfooding desde F4 |
| §7.1 | Reglas always-on | `AGENTS.base.md` (F5) |
| §7.2 | `branch-pr` y comentarios únicos por gate | `branch-pr` (F4) + gates como artefacto y `arnes gate publish` (F5) |
| §7.3 | RACI y roles | `governance.roles` + CODEOWNERS (F5) |
| §7.4 | Controles P0 | S1 (F3), S2 (F1), resto (F5); `arnes p0` (F5) |
| §7.5 | Matriz DPA | Datos en `content/shared/dpa-matrix.md`, perfil `legacy-profile` (F5) |
| §7.6 | Threat model lite | Actualizado con las superficies nuevas (F8) |
| §7.7 | AI Usage Record | Esquema (F4), verificación en `arnes check` (F4, F5) |
| §7.8 | Jueces advisory | Código y seguridad (F5), resto (F7) |
| §8.1 | Playbooks y knowledge notes | **Descartado** por decisión del dueño; los gates ya tenían skill equivalente |
| §8.2 | `tools/devin_sync.py` | **Descartado** (propio de Devin) |
| §8.3 | 3 Automations | **Descartado**; el escaneo semanal de dependencias puede volver como job de CI en F7 si se necesita |
| §8.4 | CI de GitHub inexistente | Corregido: CI real del motor (F0) y plantillas para proyectos (F5) |
| §9.1 | Canal Devin por `git-subdir` | Reemplazado por adaptador `windsurf-devin` (F2) |
| §9.2–9.3 | Canales CLI local y Desktop | Instaladores de un comando + adaptadores (F2) |
| §9.4 | Canal Cloud | Cubierto por la versión de los archivos en el repo: los agentes en la nube leen lo mismo que los locales (verificar por agente en F0) |
| §10.1 | 4 redes de validación | `arnes validate`, smoke, `arnes p0`, pytest (F1, F5) |
| §10.5 | Reglas del validador | F1 |
| §11 | Guía de replicación | Este plan |
| §12.1 | Deuda documental | Prevención: `arnes validate` chequea conteos citados en docs (F8) |
| §12.2 | Controles advisory | Parcialmente enforced con git hooks y CI (F5) |
| — | `src/index.py` (fastapi) | **Descartado**: sin propósito documentado |
| — | `_covharness.py` | **Descartado**: pytest y pytest-cov como dependencias de desarrollo |
| — | Overlays de persona (`persona.py`) | Opcional, F8 (D-17) |
| — | Carpeta y workflows de la plataforma interna de CI | **Descartado** |

## Las 100 skills del reporte

Destinos: F3, F4, F5, F6, F7 o "CLI" (reemplazada por un comando del runtime). Las skills renombradas indican su nombre nuevo.

| Pack original | Skill | Destino |
|---|---|---|
| agentic | `agentic-reliability-review` | F7 |
| agentic | `context-engineering-review` | F7 |
| core | `ai-usage-record` | F4 |
| core | `branch-pr` | F4 |
| core | `chained-pr` | F7 |
| core | `code-generation` | F4 |
| core | `cognitive-doc-design` | F7 |
| core | `comment-writer` | F7 |
| core | `context-config-audit` | F6 |
| core | `data-classification` | F5 (pack `security`) |
| core | `engram-protocol` → `memory-protocol` | F3 |
| core | `issue-creation` | F7 |
| core | `knowledge-retrieval` → `context-retrieval` | F4 |
| core | `parallel-dispatch` | F7 |
| core | `prompt-hygiene` | F5 (pack `security`) |
| core | `review` | F5 (pack `quality`) |
| core | `skill-creator` | F7 |
| core | `skill-improver` | F7 |
| core | `skill-registry` | CLI (`arnes registry`, F1) |
| core | `skill-reviewer` | F5 |
| core | `software-solution` | F7 (partida en varias skills o references) |
| core | `test-strategy` | F4 |
| core | `work-unit-commits` | F4 |
| design | `architecture-decision-record` | F6 |
| design | `architecture-diagram-designer` | F7 |
| design | `diagram-design` | F7 |
| design | `executive-visual-quality-gate` | F7 |
| design | `uml-visual-designer` | F7 |
| frontend | `accessibility-audit` | F7 (prioridad 1) |
| frontend | `frontend-design` | F7 |
| frontend | `frontend-engineering` | F7 |
| frontend | `frontend-patterns` | F7 |
| frontend | `playwright` | F7 |
| frontend | `react-patterns` | F7 |
| frontend | `react-testing` | F7 |
| frontend | `security-scan-node` | F7 |
| frontend | `tailwind-4` | F7 |
| frontend | `typescript-reviewer` | F7 |
| frontend | `typescript` | F7 |
| frontend | `zod` | F7 |
| java | `backend-and-api` | F7 |
| java | `backend-engineering` | F7 |
| java | `java-build-resolver` | F7 |
| java | `java-coding-standards` | F7 |
| java | `java-reviewer` | F7 |
| java | `jpa-patterns` | F7 |
| java | `security-scan-jkp` | F7 |
| java | `springboot-patterns` | F7 |
| java | `springboot-security` | F7 |
| java | `springboot-verification` | F7 |
| ops | `capacity-planning` | F7 |
| ops | `chaos-engineering` | F7 |
| ops | `debug-systematically` | F7 |
| ops | `incident-response` | F7 |
| ops | `kibana-logs` | F7 |
| ops | `log-analysis` | F7 |
| ops | `on-call-handoff` | F7 |
| ops | `root-cause-5whys` | F7 |
| ops | `runbook-writer` | F7 |
| ops | `slo-design` | F7 |
| product | `functional-flow-designer` | F7 |
| product | `jira-card-creator` | F7 |
| product | `jira-refinement-assistant` | F7 |
| product | `product-discovery` | F7 (prioridad 1) |
| product | `roadmap-generator` | F7 |
| python | `python-patterns` | F7 |
| python | `python-reviewer` | F7 |
| quality | `comite-excelencia` | F7 |
| quality | `harness-review` | F5 |
| quality | `judge-business` | F7 |
| quality | `judge-code-reviewer` | F5 |
| quality | `judge-frontend` | F7 |
| quality | `judge-product` | F7 |
| quality | `judge-security` | F5 |
| quality | `judge-team` | F7 |
| quality | `judgment-day` | F5 |
| quality | `review-4r` | F7 |
| sdd | `context-anchoring` | F7 |
| sdd | `project-onboarding` | F4 |
| sdd | `prompt-code-sync` | F7 |
| sdd | `prompt-spec-review` | F7 |
| sdd | `reasons-canvas-author` | F7 |
| sdd | `sdd-apply` | F4 |
| sdd | `sdd-archive` | F4 |
| sdd | `sdd-design` | F4 |
| sdd | `sdd-explore` | F4 |
| sdd | `sdd-init` | F4 |
| sdd | `sdd-new` | F4 |
| sdd | `sdd-onboard` | F7 |
| sdd | `sdd-orchestrator` | F4 |
| sdd | `sdd-propose` | F4 |
| sdd | `sdd-spec` | F4 |
| sdd | `sdd-status` | F4 |
| sdd | `sdd-tasks` | F4 |
| sdd | `sdd-verify` | F4 |
| sdd | `spdd-fitness-matrix` → `risk-tiering` | F4 |
| security | `secure-coding-baseline` | F5 |
| security | `secure-diagram-sanitizer` | F7 |
| security | `security-code-review` | F5 |
| security | `threat-modeling` | F5 |

**Totales:** F3 = 1, F4 = 20, F5 = 11, F6 = 2, CLI = 1, F7 = 65 → 100. Más 5 skills nuevas de ingeniería inversa en F6 (`arnes-adopt`, `re-extract`, `re-synthesize`, `re-audit`, `re-adoption-plan`).

## Inconsistencias del reporte y cómo se resuelven

Corresponden a la sección 4 de `99-notas-de-transcripcion.md` y al capítulo 12 del reporte.

| Inconsistencia | Resolución en el plan |
|---|---|
| core con 20 o 21 skills | Irrelevante: el catálogo se reconstruye con conteo verificado por `arnes validate` |
| `quality` menciona "selección de la regresión afectada" sin skill que la haga | No se promete en la descripción del pack; candidata a skill nueva post-v1 |
| `threat-model-lite` nombrado como skill | Es un documento; la skill es `threat-modeling` |
| `sdd-init` y `sdd-archive` con `subagent: true` pero listadas como inline | Se definen como inline (`arnes-execution: inline`) |
| LOC del runtime 8 305 vs ≈ 9 100 | Irrelevante para la reconstrucción |
| 17 vs 16 archivos de test | Irrelevante; la suite nueva se mide en CI |
| 24 knowledge notes no listadas | Knowledge descartado; los temas útiles (guardrails, patrones por stack) se absorben en skills de F7 |
| Campo `agent` sin explicación | No se reproduce; los subagentes se modelan con `arnes-subagent` |
| `ense\u00f1as` literal | El validador rechaza escapes Unicode literales |
| `index.py` no documentado | Descartado |
| Conteos viejos en docs (§12.1 #1, #2) | `arnes validate` verifica conteos citados (F8) |
| Doc de Cloud desactualizada (§12.1 #6, #7) | Sin canal Cloud separado: los agentes en la nube leen los archivos del repo |
| "CI verde" sin CI (§12.1 #11) | CI real (F0, F5) |
