# 03 — Matriz de agentes

> Relevado el 2026-10-28 con fuentes públicas. Las convenciones de los agentes cambian casi todas las semanas, así que **la tarea 0.4 de F0 vuelve a verificar cada celda contra la documentación oficial** y produce `docs/agent-matrix.md` con URL y fecha. Las celdas marcadas `[verificar]` no tienen todavía confirmación suficiente.

## La respuesta corta a "¿alcanza con un AGENTS.md?"

Casi. `AGENTS.md` resuelve las **reglas** en la gran mayoría de los agentes, y la carpeta `.agents/skills/` resuelve las **skills** en muchos de ellos (el estándar Agent Skills pasó a la Linux Foundation el 22 de octubre de 2026 y varios agentes ya leen esa carpeta directamente). Pero quedan tres cosas que siempre son específicas de cada agente:

1. **Claude Code** no lee `AGENTS.md` si existe un `CLAUDE.md` (hay que importarlo con `@AGENTS.md`) y no escanea `.agents/skills/` (necesita `.claude/skills/`).
2. **La configuración MCP** tiene una ruta y un formato distinto en cada agente.
3. **Subagentes, hooks y comandos** tienen formatos distintos o no existen en algunos agentes.

Por eso el instalador sigue siendo necesario, pero es delgado: genera `AGENTS.md` + `.agents/skills/` para todos y, por agente, solo lo que falta.

## Matriz

| Agente | Reglas | Skills (proyecto) | Subagentes | MCP (proyecto) | Hooks | Comandos |
|---|---|---|---|---|---|---|
| **Genérico** (compatible con AGENTS.md) | `AGENTS.md` | `.agents/skills/` | — | Se imprime el snippet | — | — |
| **Claude Code** | `CLAUDE.md` con `@AGENTS.md` (lee `AGENTS.md` solo si no hay `CLAUDE.md`) | `.claude/skills/` (no escanea `.agents/skills/`) | `.claude/agents/*.md` | `.mcp.json` en la raíz, clave `mcpServers` | `.claude/settings.json` (eventos como `SessionStart`, `PreToolUse`, `PreCompact`, `Stop`) | Las skills se invocan como `/nombre` |
| **GitHub Copilot** (VS Code, CLI, cloud agent) | `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` | `.github/skills/`, `.claude/skills/` o `.agents/skills/` | `.github/agents/*.agent.md`; VS Code también lee `.claude/agents/` en formato Claude | `.vscode/mcp.json` (VS Code, clave `servers` `[verificar]`); cloud agent por configuración del repo `[verificar]` | `.github/hooks/*.json` (soporte parcial según superficie) | `.github/prompts/*.prompt.md` |
| **Cursor** | `AGENTS.md`, `.cursor/rules/` | `.agents/skills/` (+ `.cursor/skills/`) `[verificar]` | `.cursor/agents/`, compatible con `.claude/agents/` y `.codex/agents/` | `.cursor/mcp.json`, clave `mcpServers` | `[verificar]` | `.cursor/commands/` `[verificar]` |
| **Codex CLI** | `AGENTS.md` | `.agents/skills/` | Definiciones TOML `[verificar]` | `.codex/config.toml`, tabla `[mcp_servers.<nombre>]` | `[verificar]` | `[verificar]` |
| **Gemini CLI** | `GEMINI.md` por defecto; configurable para leer `AGENTS.md` `[verificar]` | `.agents/skills/` | `.gemini/agents/` `[verificar]` | `.gemini/settings.json`, clave `mcpServers` | `[verificar]` | `.gemini/commands/*.toml` |
| **Windsurf / Devin** (Cognition) | `AGENTS.md` | `.windsurf/skills/` con compatibilidad `.agents/skills/` | `[verificar]` | Windsurf: config global de usuario; Devin: config de organización/plugin `[verificar]` | `[verificar]` | `[verificar]` |

## Conclusiones de diseño

**Reglas.** La fuente es `AGENTS.md` (bloque `arnes:core`). El adaptador de Claude Code agrega un bloque con `@AGENTS.md` en `CLAUDE.md` (lo crea si no existe). El de Gemini configura la lectura de `AGENTS.md` o, si no es posible, agrega un bloque puntero en `GEMINI.md`. Para Copilot, F0 decide si hace falta un bloque puntero en `.github/copilot-instructions.md` o si `AGENTS.md` ya alcanza en todas sus superficies.

**Skills.** La copia canónica instalada va a `.agents/skills/`. Solo si Claude Code es destino se genera el espejo `.claude/skills/` (por defecto como copia gestionada por el lock; ver D-06). **Riesgo a verificar en F0:** Copilot lee tanto `.claude/skills/` como `.agents/skills/`, así que con el espejo podría listar cada skill dos veces. Si pasa, las opciones son aceptarlo (mismo contenido), o usar `.claude/skills/` como única copia cuando el equipo solo usa Claude Code y Copilot.

**Subagentes.** El formato de Claude Code (`.claude/agents/*.md`) es el denominador común de hecho: lo leen Claude Code, VS Code con Copilot y Cursor. Por eso es el formato canónico. Para Copilot en GitHub.com se genera además `.github/agents/*.agent.md`.

**MCP.** Siempre se genera por agente con merge por clave (`mcpServers.arnes`, `servers.arnes` o la tabla TOML entre marcadores `# BEGIN/END:arnes:mcp`). Si el archivo existente no se puede parsear (por ejemplo JSON con comentarios), no se toca y se imprime el snippet para pegar.

**Hooks.** Son heterogéneos. En la v1 se implementan para Claude Code y Copilot (memoria automática en F3, guardas en F5). El enforcement que importa es agnóstico: git hooks y CI.

**Capacidades y degradación.** Cada adaptador declara sus capacidades. El bloque que se agrega al archivo propio de cada agente (por ejemplo `CLAUDE.md`) dice explícitamente "en este agente hay subagentes: sí/no". Los agentes que solo leen `AGENTS.md` asumen "sin subagentes" salvo que tengan una herramienta de delegación, y las skills del ciclo SDD corren inline declarando que no hubo aislamiento (comportamiento del reporte, §6.5 A).

## Tiers de soporte en la v1 (ver D-04)

| Tier | Agentes | Qué incluye |
|---|---|---|
| 1 | Claude Code, GitHub Copilot | Reglas, skills, subagentes, MCP, hooks, golden tests, checklist manual de verificación |
| 2 | Cursor, Codex CLI, Gemini CLI, Windsurf/Devin | Reglas, skills, MCP; subagentes cuando el formato es compatible; golden tests |
| 3 | Cualquier otro compatible con AGENTS.md | Adaptador genérico + snippet MCP impreso |

## Señales de detección

| Agente | Artefactos en el repo | Ejecutable | Variable de entorno |
|---|---|---|---|
| Claude Code | `CLAUDE.md`, `.claude/`, `.mcp.json` | `claude` | `[verificar en F0]` |
| Copilot | `.github/copilot-instructions.md`, `.github/agents/`, `.github/skills/`, `.vscode/mcp.json` | `copilot`, `code` | `[verificar en F0]` |
| Cursor | `.cursor/` | `cursor` | `[verificar en F0]` |
| Codex | `.codex/` | `codex` | `[verificar en F0]` |
| Gemini CLI | `GEMINI.md`, `.gemini/` | `gemini` | `[verificar en F0]` |
| Windsurf/Devin | `.windsurf/`, `.devin/` | `windsurf` | `[verificar en F0]` |

## Fuentes usadas (re-verificar en F0)

- GitHub Docs, *Copilot customization cheat sheet*: https://docs.github.com/en/enterprise-cloud@latest/copilot/reference/customization-cheat-sheet
- VS Code, *Custom agent file reference*: https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference.md
- Claude Code, subagentes: https://code.claude.com/docs/en/sub-agents (y el resto de la documentación de Claude Code sobre memoria, skills, MCP y hooks)
- Especificación AGENTS.md: https://agents.md
- Estándar Agent Skills: https://agentskills.io
- Matriz de agentes y rutas de gentle-ai (proyecto del que deriva el reporte): https://github.com/gentleman-programming/gentle-ai
- Fuentes secundarias consultadas para el cruce: artículos y herramientas de terceros sobre `.agents/skills` y comportamiento de `CLAUDE.md`/`AGENTS.md` (se usan solo para saber qué verificar, no como fuente final).
