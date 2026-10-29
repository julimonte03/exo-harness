# 03 — Matriz de agentes

> Relevada el 2026-10-28 con fuentes públicas y **re-verificada el 2026-10-29 en la tarea 0.4 de F0** contra documentación oficial y una prueba empírica con Claude Code. El detalle, con la URL de cada celda, está en `docs/agent-matrix.md`; la prueba, en `docs/spikes/agent-probe.md`. Esta versión corrige lo que la verificación contradijo (criterio 7 de F0). Lo que sigue sin confirmar se marca `[No verificado]`.

## La respuesta corta a "¿alcanza con un AGENTS.md?"

Casi. `AGENTS.md` resuelve las **reglas** en todos los agentes de la matriz, salvo Gemini CLI, que necesita configuración. La carpeta `.agents/skills/` resuelve las **skills** en Copilot, Cursor, Codex, Gemini y Devin. El estándar Agent Skills pasó el 2026-10-22 a la Agentic AI Foundation, bajo la Linux Foundation, sin cambios de formato. Pero siguen siendo específicas de cada agente estas cosas:

1. **Claude Code** lee `AGENTS.md` de forma nativa desde v2.1.277, pero solo si no hay ningún `CLAUDE.md`. Si lo hay, hay que importarlo con `@AGENTS.md`. Además, Claude Code no escanea `.agents/skills/`: necesita `.claude/skills/`.
2. **La configuración MCP** cambia de ruta y formato según el agente, y varios agentes la cargan solo en carpetas confiables.
3. **Subagentes, hooks y comandos** tienen formatos distintos en cada agente.
4. **Hay lecturas cruzadas.** Copilot, Cursor y Devin también leen `CLAUDE.md`, `.claude/skills/`, `.claude/agents/` y los hooks de `.claude/settings.json`. Generar el mismo contenido en dos lugares puede duplicarlo o hacerlo correr dos veces.

Por eso el instalador sigue siendo necesario, pero delgado: genera `AGENTS.md` y las skills para todos, y por agente solo lo que falta, cuidando de no duplicar.

## Matriz (resumen verificado)

| Agente | Reglas | Skills (proyecto) | Subagentes | MCP (proyecto) | Hooks | Comandos |
|---|---|---|---|---|---|---|
| **Genérico** (compatible con AGENTS.md) | `AGENTS.md` | `.agents/skills/` | — | Se imprime el snippet | — | — |
| **Claude Code** | `CLAUDE.md`; `AGENTS.md` solo si no hay ningún `CLAUDE.md` (≥ 2.1.277), o vía `@AGENTS.md` | `.claude/skills/` (no lee `.agents/skills/`) | `.claude/agents/**/*.md` | `.mcp.json`, clave `mcpServers` | `.claude/settings.json` (33 eventos: `SessionStart`, `PreToolUse`, `PreCompact`, `Stop`…) | Skills como `/nombre` |
| **Copilot CLI / VS Code (Copilot harness, default)** | Fusiona `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.github/instructions/**`, `.claude/rules/**` | `.github/skills/` > `.agents/skills/` > `.claude/skills/` (gana el primero) | `.github/agents/` > `.claude/agents/` (`.agent.md` o `.md`) | **`.mcp.json`, clave `mcpServers`** (requiere confianza; Copilot exige `tools`) | `.github/hooks/*.json` + `.claude/settings*.json` (corren todas) | Skills como `/nombre`; **sin prompt files** |
| **VS Code (Local harness, legacy)** | `AGENTS.md` (anidados con setting), `CLAUDE.md` con setting | `.github/`, `.claude/`, `.agents/skills/` | `.github/agents/`, `.claude/agents/` | `.vscode/mcp.json`, clave `servers` | Preview (`chat.useHooks`) | `.github/prompts/*.prompt.md` |
| **Copilot cloud agent** | `copilot-instructions.md`, `instructions/`, `AGENTS.md`, un `CLAUDE.md` o `GEMINI.md` en la raíz | `.github/`, `.claude/`, `.agents/skills/` | `.github/agents/*.agent.md` | Settings del repo (no archivo), secretos `COPILOT_MCP_*` | Solo `.github/hooks/*.json`, solo bash | Sin prompt files |
| **Cursor** | `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/**/*.mdc` | `.agents/`, `.cursor/`, `.claude/`, `.codex/skills/` | `.cursor/agents/` > `.claude/agents/` (Markdown) | `.cursor/mcp.json`, clave `mcpServers` (`type: "stdio"`) | `.cursor/hooks.json` + `.claude/settings*.json` | `.cursor/commands/` (legacy, migra a skills) |
| **Codex CLI** | `AGENTS.md` / `AGENTS.override.md` (tope 32 KiB) | `.agents/skills/` | `.codex/agents/*.toml` | `.codex/config.toml`, `[mcp_servers.<nombre>]`, **solo en proyectos confiables** | `.codex/hooks.json` (confianza por hash) | Prompts deprecados (solo usuario); skills |
| **Gemini CLI** (Antigravity CLI para el tier gratuito) | `GEMINI.md`; `AGENTS.md` con `context.fileName` | `.gemini/skills/` + alias `.agents/skills/` | `.gemini/agents/*.md` | `.gemini/settings.json`, clave `mcpServers`, **solo en carpetas confiables** | `hooks` en `settings.json` (`BeforeTool`, `AfterTool`…) | `.gemini/commands/*.toml` |
| **Devin Local / CLI** (ex Windsurf; Cascade eliminado el 2026-09-08) | `AGENTS.md`, `CLAUDE.md`, `.devin/rules/` (+ lee las de Cursor y Windsurf) | `.agents/`, `.devin/`, `.windsurf/`, `.claude/skills/` | `.devin/agents/`, `.agents/agents/` | `.devin/mcp_config.json`, clave `mcpServers` (+ importa `.mcp.json`) | `.devin/hooks.v1.json` + `.claude/settings*.json` (corren todas) | Skills como `/nombre` |

## Conclusiones de diseño

Son propuestas para F2 y se deciden ahí con D-04, D-05 y D-06.

**Reglas.**
- La fuente es `AGENTS.md` (bloque `exo:core`).
- **Claude Code:** si el proyecto no tiene `CLAUDE.md`, no se crea. Claude ≥ 2.1.277 ya lee `AGENTS.md`, y un `CLAUDE.md` adicional duplicaría el contexto en Copilot, Cursor y Devin, que leen los dos. Si el humano ya tiene `CLAUDE.md`, se le inyecta un bloque con `@AGENTS.md`. `exo doctor` verifica la versión de Claude Code.
- **Gemini:** se configura `context.fileName: ["AGENTS.md", "GEMINI.md"]` en `.gemini/settings.json`; solo rige en carpetas confiables, y si no, se agrega un bloque puntero en `GEMINI.md`.
- **Copilot:** no hace falta un bloque en `.github/copilot-instructions.md`, porque todas sus superficies leen `AGENTS.md`.

**Skills.**
- Sin duplicar sin necesidad. Si los destinos son solo Claude Code y Copilot, una única copia en `.claude/skills/` llega a los dos.
- Si hay Codex, Gemini o un agente genérico, va `.agents/skills/`, más `.claude/skills/` si está Claude Code.
- Las copias son idénticas, así que la sombra en Copilot ("gana el primero") no hace daño.
- **A verificar en F2:** si Cursor y Devin listan dos veces una skill que está en `.agents/skills/` y en `.claude/skills/`.

**Subagentes.**
- `.claude/agents/*.md` es el denominador común: lo leen Claude Code, Copilot CLI, VS Code y Cursor.
- Se generan además, según destino:
  - `.github/agents/*.agent.md` (cloud agent);
  - `.codex/agents/*.toml`;
  - `.gemini/agents/*.md`;
  - `.devin/agents/*.md`.

**MCP.**
- Se merge por clave según el agente:
  - `.mcp.json` → `mcpServers.exo`, común a Claude Code, Copilot CLI, el Copilot harness de VS Code y Devin, que lo importa;
  - `.cursor/mcp.json` → `mcpServers.exo`;
  - `.gemini/settings.json` → `mcpServers.exo`;
  - `.codex/config.toml` → tabla `[mcp_servers.exo]` entre marcadores `# BEGIN/END:exo:mcp`, sin dependencias de TOML.
- `.vscode/mcp.json` solo se genera si se apunta al Local harness.
- Si el archivo existente no se puede parsear, no se toca y se imprime el snippet.
- **Riesgo nuevo (D-23):** la organización puede bloquear servidores MCP fuera de una lista permitida; en esta máquina pasa.

**Hooks.**
- Copilot, Cursor y Devin también corren los hooks de `.claude/settings.json`. Para no ejecutar dos veces, un hook se escribe en un solo lugar por proyecto.
- El enforcement que importa sigue siendo agnóstico: git hooks y CI.

**Comandos.**
- Las skills funcionan como comandos en todos los agentes.
- No se generan prompt files, `.cursor/commands/` ni prompts de Codex, porque están deprecados o no los leen la mayoría de las superficies.

**Capacidades y degradación.**
- Cada adaptador declara sus capacidades. El bloque que se agrega al archivo propio de cada agente dice explícitamente "en este agente hay subagentes: sí/no".
- Los agentes que solo leen `AGENTS.md` asumen "sin subagentes", salvo que tengan una herramienta de delegación. En ese caso, las skills del ciclo SDD corren inline y declaran que no hubo aislamiento (reporte §6.5 A).

## Tiers de soporte en la v1 (ver D-04)

| Tier | Agentes | Qué incluye |
|---|---|---|
| 1 | Claude Code, GitHub Copilot (CLI, VS Code Copilot harness y cloud agent) | Reglas, skills, subagentes, MCP, hooks, golden tests, checklist manual de verificación |
| 2 | Cursor, Codex CLI, Gemini CLI, Devin Local/CLI (ex Windsurf) | Reglas, skills, MCP; subagentes cuando el formato es compatible; golden tests |
| 3 | Cualquier otro compatible con AGENTS.md | Adaptador genérico + snippet MCP impreso |

Candidato a evaluar en D-04: Antigravity CLI, sucesor de Gemini CLI para el tier gratuito. Lee `.agents/skills/` y `AGENTS.md`, y su MCP de workspace está en `.agents/mcp_config.json`.

## Señales de detección

| Agente | Artefactos en el repo | Ejecutable | Variable de entorno (verificado 2026-10-29) |
|---|---|---|---|
| Claude Code | `CLAUDE.md`, `.claude/`, `.mcp.json` | `claude` | `CLAUDECODE=1`; `CLAUDE_CODE_CHILD_SESSION=1` solo en procesos que lanza el agente |
| Copilot | `.github/copilot-instructions.md`, `.github/agents/`, `.github/skills/`, `.github/hooks/` | `copilot`, `code` | `COPILOT_CLI=1` (changelog); VS Code: `AI_AGENT=github_copilot_vscode_agent` (verificación parcial) |
| Cursor | `.cursor/` | `cursor`, `agent` | `CURSOR_AGENT` (no vacío) |
| Codex | `.codex/` | `codex` | `[No verificado]` (en código: `CODEX_THREAD_ID`) |
| Gemini CLI | `GEMINI.md`, `.gemini/` | `gemini` | `GEMINI_CLI=1` |
| Devin Local/CLI | `.devin/`, `.windsurf/` | `devin` `[No verificado]` | `AI_AGENT=devin_<versión>_agent` |

`AI_AGENT` (Claude Code, Devin, VS Code) se perfila como convención común: se compara por prefijo. Ninguna señal de detección se usa para decisiones de seguridad.

## Fuentes

Las fuentes con URL por celda están en `docs/agent-matrix.md`. Las principales:

- https://code.claude.com/docs
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference
- https://code.visualstudio.com/docs/agent-customization
- https://cursor.com/docs
- https://learn.chatgpt.com/docs (Codex)
- https://geminicli.com/docs
- https://docs.devin.ai
- https://agents.md
- https://agentskills.io/specification
