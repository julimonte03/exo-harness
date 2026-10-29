# F7 — Packs de stack y resto del catálogo

## Objetivo

Completar las 65 skills del reporte que no entraron antes de M3, organizadas por pack y en orden de prioridad, con un proceso de autoría y evaluación repetible.

## Depende de

F5 cerrada (puede solaparse con F6). Decisiones D-12 y D-18. Antes de empezar, el equipo indica qué stacks usa de verdad para ordenar los packs de stack.

## Proceso para cada skill

1. Partir de la descripción y el rol que da el reporte (capítulo 03) y de su lugar en el mapa fase → skills. **No hay cuerpos originales**: cada skill se escribe de nuevo.
2. Escribirla en formato canónico, con hasta 500 líneas y detalle en `references/`. Si la original era más larga (por ejemplo `software-solution`, 626 líneas), partirla.
3. Generalizar lo específico de la organización según D-12: estilo ejecutivo con tokens de marca configurables (`.arnes/brand.json`), herramientas corporativas (SonarQube, Fortify, Kibana, Xray) como integraciones opcionales que degradan.
4. Si la skill es de origen `ecc`, aplicar D-18 (escribir desde cero salvo licencia compatible confirmada).
5. Para las skills de prioridad 1 y 2, escribir tres prompts de evaluación en `tests/skill_evals/<skill>/`: uno que debe disparar la skill, uno que no, y uno con verificación de la salida.
6. `arnes validate` y `skill-reviewer` en verde.

## Packs y prioridades

| Prioridad | Pack | Skills | Notas |
|---|---|---|---|
| 1 | `sdd` (SPDD) | `reasons-canvas-author`, `prompt-spec-review`, `prompt-code-sync`, `context-anchoring`, `sdd-onboard` | Completa el overlay SPDD del §6.8: Canvas REASONS de 7 dimensiones en `<change-root>/canvas.md`, gate humano y sincronización prompt/código |
| 1 | `quality` | `judge-product`, `judge-business`, `judge-frontend`, `judge-team`, `comite-excelencia`, `review-4r` | Completa los jueces del §7.8 |
| 1 | `product` | `product-discovery` | Es conditional en explore, propose y spec |
| 1 | `frontend` | `accessibility-audit` | Gate de accesibilidad de `sdd-verify` (§6.7) |
| 1 | `core` | `parallel-dispatch`, `chained-pr` | Conditional en tasks; PRs encadenados cuando se supera el presupuesto de 400 líneas |
| 2 | Packs del stack del equipo | Ver abajo | El orden lo define el equipo |
| 3 | `ops` | `capacity-planning`, `chaos-engineering`, `debug-systematically`, `incident-response`, `kibana-logs`, `log-analysis`, `on-call-handoff`, `root-cause-5whys`, `runbook-writer`, `slo-design` | `kibana-logs` se generaliza a "logs en Elastic/OpenSearch/Kibana" |
| 3 | `security` | `secure-diagram-sanitizer` | — |
| 4 | `product` | `functional-flow-designer`, `jira-card-creator`, `jira-refinement-assistant`, `roadmap-generator` | Las de Jira solo se instalan con `tracker.type = jira`; Xray opcional |
| 4 | `design` | `architecture-diagram-designer`, `diagram-design`, `executive-visual-quality-gate`, `uml-visual-designer` | Estilo ejecutivo configurable |
| 4 | `agentic` | `agentic-reliability-review`, `context-engineering-review` | — |
| 4 | `core` | `cognitive-doc-design`, `comment-writer`, `issue-creation`, `skill-creator`, `skill-improver`, `software-solution` | `issue-creation` se adapta al tracker |

### Packs de stack (prioridad 2)

| Pack | Skills |
|---|---|
| `frontend` | `frontend-design`, `frontend-engineering`, `frontend-patterns`, `playwright`, `react-patterns`, `react-testing`, `security-scan-node`, `tailwind-4`, `typescript-reviewer`, `typescript`, `zod` |
| `java` | `backend-and-api`, `backend-engineering`, `java-build-resolver`, `java-coding-standards`, `java-reviewer`, `jpa-patterns`, `security-scan-jkp`, `springboot-patterns`, `springboot-security`, `springboot-verification` |
| `python` | `python-patterns`, `python-reviewer` |

Los escáneres `security-scan-node` y `security-scan-jkp` dependían de una cadena con SonarQube, Fortify y un lock de playbooks de scanning (ADR-0007 del reporte). Se generalizan a una cadena de herramientas abiertas (auditoría nativa del gestor de paquetes, OSV, dependency-check) con SonarQube y Fortify como pasos opcionales si están configurados.

## Criterios de aceptación (por pack)

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Contenido válido | `arnes validate` verde con el pack incluido |
| 2 | Degradación correcta | Test: con el pack sin instalar, las skills que lo referencian declaran la degradación; instalado, lo resuelven |
| 3 | Evals | Los prompts de evaluación de las skills de prioridad 1 y 2 pasan en la revisión manual con Claude Code, anotada en `PROGRESO.md` |
| 4 | Instalación por stack | `arnes init` sobre fixtures de cada stack sugiere el pack correcto (port de `curate`) |

## Referencias al reporte

Capítulo 03 completo, §2.7 (qué instalar según el stack), §6.4 (conditionals), §6.8 (SPDD), §7.8 (jueces).
