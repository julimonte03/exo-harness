# Matriz de agentes verificada

- **Verificado:** 2026-10-29, contra documentación oficial (sitios de cada proveedor y sus repos o changelogs oficiales), más una prueba empírica con Claude Code en Windows.
- **Alcance:** las 8 columnas de la tarea 0.4 de F0, para los agentes de Tier 1 y Tier 2.
- **Convención:** cada celda cita su fuente, o dice `[No verificado]`. Lo que solo aparece en código fuente o en un changelog se aclara como tal.
- **Vigencia:** las convenciones cambian casi cada semana (VS Code publica semanalmente). Antes de tocar un adaptador, re-verificar su sección y actualizar la fecha.

Columnas: **1** reglas y precedencia · **2** directorios de skills · **3** skill con el mismo nombre en dos directorios · **4** subagentes · **5** config MCP de proyecto · **6** hooks · **7** comandos invocables · **8** variables de entorno que define el agente en el shell.

## Cambios de producto que afectan al plan

- **Windsurf ahora es Devin Desktop** (2026-06-02). Cascade se eliminó en la v3.9.19 (2026-09-08) y el único agente es **Devin Local**, que usa el mismo motor y la misma config que **Devin CLI**: https://docs.devin.ai/desktop/devin-desktop-faq.md, https://docs.devin.ai/desktop/changelog.md
- **Gemini CLI fue reemplazado por Antigravity CLI** para el tier gratuito y Google One (2026-06-18). Sigue disponible con API key paga y Code Assist Standard/Enterprise. El banner está en todas las páginas de https://geminicli.com/docs/
- **VS Code tiene dos "harness".** El default es el **Copilot harness**, que comparte el runtime de Copilot CLI (`chat.defaultToCopilotHarness`); el comportamiento anterior quedó en el **Local harness**: https://code.visualstudio.com/docs/agents/concepts/agent-harnesses
- **GitHub ahora llama "Copilot cloud agent" al antes llamado "coding agent".** Así figura en las rutas y títulos de su documentación, por ejemplo https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/create-custom-agents. No encontré un anuncio del cambio: `[No verificado]`.
- **El estándar Agent Skills pasó a la Agentic AI Foundation (Linux Foundation)** el 2026-10-22, sin cambios de formato: https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation. `name` tiene de 1 a 64 caracteres `a-z0-9-` e igual a la carpeta; `description` de 1 a 1024. Los campos opcionales son `license`, `compatibility`, `metadata` (mapa string→string) y `allowed-tools`: https://agentskills.io/specification
- **AGENTS.md** también está bajo la AAIF. "The closest AGENTS.md to the edited file wins": https://agents.md

## Resumen

| Agente | 1 Reglas | 2 Skills (proyecto) | 4 Subagentes | 5 MCP (proyecto) | 8 Detección |
|---|---|---|---|---|---|
| Claude Code | `CLAUDE.md`; `AGENTS.md` solo si no hay `CLAUDE.md` (≥ 2.1.277, con salvedades) | `.claude/skills/` | `.claude/agents/*.md` | `.mcp.json` · `mcpServers` | `CLAUDECODE=1` |
| Copilot CLI / VS Code (Copilot harness) | Fusiona `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `copilot-instructions.md`, `.github/instructions/` | `.github/skills/` > `.agents/skills/` > `.claude/skills/` | `.github/agents/` > `.claude/agents/` | `.mcp.json` · `mcpServers` | `COPILOT_CLI=1` (CLI); `AI_AGENT` en VS Code, verificación parcial |
| Copilot cloud agent | `copilot-instructions.md`, `instructions/`, `AGENTS.md`, `CLAUDE.md` o `GEMINI.md` | `.github/` · `.claude/` · `.agents/skills/` | `.github/agents/*.agent.md` | Settings del repo (no archivo) | `COPILOT_AGENT_PROMPT` |
| Cursor | `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/*.mdc` | `.agents/` · `.cursor/` · `.claude/` · `.codex/skills/` | `.cursor/agents/` > `.claude/agents/` | `.cursor/mcp.json` · `mcpServers` | `CURSOR_AGENT` |
| Codex CLI | `AGENTS.md` (+ `AGENTS.override.md`) | `.agents/skills/` | `.codex/agents/*.toml` | `.codex/config.toml` · `[mcp_servers.x]` (confiable) | `[No verificado]` |
| Gemini CLI | `GEMINI.md`; `AGENTS.md` con `context.fileName` | `.gemini/skills/` + alias `.agents/skills/` | `.gemini/agents/*.md` | `.gemini/settings.json` · `mcpServers` (confiable) | `GEMINI_CLI=1` |
| Devin Local / CLI (ex Windsurf) | `AGENTS.md`, `CLAUDE.md`, `.devin/rules/` | `.agents/` · `.devin/` · `.windsurf/` · `.claude/skills/` | `.devin/agents/` · `.agents/agents/` | `.devin/mcp_config.json` · `mcpServers` (+ importa `.mcp.json`) | `AI_AGENT=devin_…` |

El detalle con fuentes está en las secciones siguientes.

---

## Claude Code

Versión instalada en esta máquina: 2.1.312. Docs: https://code.claude.com/docs

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>Carga `CLAUDE.md`, `.claude/CLAUDE.md` y `CLAUDE.local.md` del cwd y de cada padre, concatenados; los de subdirectorios, bajo demanda.</li><li>**`AGENTS.md` nativo desde v2.1.277**, solo si no existe ningún `CLAUDE.md`, `.claude/CLAUDE.md` ni `CLAUDE.local.md` en el cwd o más arriba (setting por defecto `claude-md-or-agents-md`; `claude-md-and-agents-md` lee los dos).</li><li>**Salvedades:** no lee `AGENTS.md` si el plugin incorporado está desactivado (`cc-plugin-agents-md@builtin`; antes de v2.1.285, `agents-md@builtin`), ni a veces en la primera sesión después de actualizar desde ≤ 2.1.276. Antes de v2.1.281, algunas sesiones (Bedrock, telemetría desactivada) leen solo `CLAUDE.md`.</li><li>`@AGENTS.md` dentro de `CLAUDE.md` lo importa sin duplicar, y funciona en todos esos casos.</li><li>No lee `GEMINI.md` ni `.github/copilot-instructions.md`.</li><li>**Empírico:** con `CLAUDE.md` sin import, `AGENTS.md` no se carga; con `@AGENTS.md`, se cargan los dos.</li></ul> | https://code.claude.com/docs/en/memory (§"How CLAUDE.md files load", §"When Claude Code reads AGENTS.md", §"Choose which instruction files load"); prueba empírica |
| 2 | <ul><li>Proyecto: `.claude/skills/` (del cwd a la raíz del repo; los `<subdir>/.claude/skills` anidados, bajo demanda).</li><li>Usuario: `~/.claude/skills/`; además managed y plugins.</li><li>**No lee `.agents/skills/` ni `.github/skills/`.** Confirmado empíricamente.</li></ul> | https://code.claude.com/docs/en/skills (§"Choose where skills load"); spike |
| 3 | <ul><li>Enterprise > personal > proyecto.</li><li>Una skill le gana a un `.claude/commands` con el mismo nombre.</li><li>Raíz y anidado conviven con namespace (`/apps/web:deploy`).</li></ul> | https://code.claude.com/docs/en/skills (§"Resolve skills that share a name") |
| 4 | <ul><li>`.claude/agents/**/*.md` (recursivo) y `~/.claude/agents/`.</li><li>Frontmatter obligatorio: `name` y `description`; opcionales `tools`, `model`, `skills`, `mcpServers`, `hooks`, etc.</li><li>Prioridad: managed > `--agents` > proyecto > usuario > plugin.</li><li>Empírico: OK.</li></ul> | https://code.claude.com/docs/en/sub-agents; spike |
| 5 | <ul><li>`.mcp.json` en la raíz, clave `mcpServers`, JSON con `${VAR}`.</li><li>En sesión interactiva pide aprobación; `-p` y el SDK cargan sin preguntar.</li><li>`enableAllProjectMcpServers` en los settings del proyecto se ignora hasta confiar en el workspace.</li><li>**Empírico:** una política administrada puede bloquear los servidores MCP del proyecto (ADR-0005).</li></ul> | https://code.claude.com/docs/en/mcp; spike |
| 6 | <ul><li>Archivos: `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json`, managed, plugins y frontmatter de skills o subagentes.</li><li>Formato: `{"hooks":{"<Evento>":[{"matcher":"…","hooks":[{"type":"command","command":"…","timeout":30}]}]}}`.</li><li>33 eventos, entre ellos `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `Stop` y `SessionEnd`.</li><li>En sesión interactiva requieren confianza en el workspace.</li></ul> | https://code.claude.com/docs/en/hooks (§"Hook locations", §"Hook events", §"Workspace trust") |
| 7 | <ul><li>Skills como `/nombre` (con `$ARGUMENTS`).</li><li>`.claude/commands/*.md` es legacy y sigue funcionando.</li><li>Los prompts MCP aparecen como comandos.</li></ul> | https://code.claude.com/docs/en/skills; https://code.claude.com/docs/en/commands |
| 8 | <ul><li>Documentadas:<ul><li>`CLAUDECODE=1`, también en las terminales de la extensión IDE.</li><li>`CLAUDE_CODE_CHILD_SESSION=1`, solo en procesos que lanza Claude Code.</li><li>`CLAUDE_CODE_SESSION_ID`, `CLAUDE_PID`, `CLAUDE_EFFORT`.</li><li>`CLAUDE_PROJECT_DIR`, en hooks y MCP.</li><li>En la nube, `CLAUDE_CODE_REMOTE=true`.</li></ul></li><li>Observadas sin documentar:<ul><li>`CLAUDE_CODE_ENTRYPOINT=claude-vscode`.</li><li>`AI_AGENT=claude-code_<versión>_agent`.</li></ul></li></ul> | https://code.claude.com/docs/en/env-vars; spike |

## GitHub Copilot

Tres superficies con comportamiento distinto. **Copilot CLI** y el **Copilot harness de VS Code** (el default) comparten runtime. El **Local harness de VS Code** es el comportamiento anterior. El **cloud agent** corre en GitHub.com.

### Copilot CLI (y VS Code con Copilot harness)

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>**Lee y fusiona todo**, sin orden de precedencia:<ul><li>`AGENTS.md` (raíz, cwd, intermedios y anidados por la ruta del archivo editado).</li><li>`CLAUDE.md` y `.claude/CLAUDE.md`.</li><li>`GEMINI.md`.</li><li>`.github/copilot-instructions.md` y `.github/instructions/**/*.instructions.md`.</li><li>`.claude/rules/**/*.md`.</li><li>Los equivalentes en `~/.copilot/`.</li></ul></li><li>Elimina solo las copias idénticas.</li><li>Los `@` imports funcionan en `AGENTS.md`, `CLAUDE.md` y `copilot-instructions.md`.</li></ul> | https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference (§"Custom instructions locations"); https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions |
| 2 | Orden: `.github/skills/` > `.agents/skills/` > `.claude/skills/` > `.github/skills/` de los padres > `~/.copilot/skills/` > `~/.agents/skills/` > plugins | cli-command-reference (§"Skill locations") |
| 3 | **Gana la primera que encuentra**, sin aviso (sombra silenciosa). No la lista dos veces | cli-command-reference (§"Skill locations") |
| 4 | <ul><li>`~/.copilot/agents/` > `.github/agents/` > **`.claude/agents/`**.</li><li>Acepta `.agent.md` o `.md`.</li><li>El ID sale de la ruta; si se repite, gana el primero.</li></ul> | cli-command-reference (§"Custom agent locations") |
| 5 | <ul><li>`.mcp.json` y `.github/mcp.json` (clave `mcpServers`); de usuario, `~/.copilot/mcp-config.json`.</li><li>Requiere confianza en la carpeta; con `-p`, además `GITHUB_COPILOT_PROMPT_MODE_WORKSPACE_MCP=true`.</li><li>**Ya no lee `.vscode/mcp.json`.**</li><li>Para servers locales exige `command`, `args` y `tools`.</li></ul> | cli-command-reference (§"MCP server loading priority", §"MCP server trust levels", §"Migrating from .vscode/mcp.json") |
| 6 | <ul><li>Fuentes: `.github/hooks/*.json`, `.github/copilot/settings(.local).json`, **`.claude/settings(.local).json`**, `~/.copilot/` y plugins. **Corren todas.**</li><li>Formato: `{"version":1,"hooks":{"preToolUse":[{"type":"command","bash":"…","powershell":"…","timeoutSec":30}]}}`.</li><li>Eventos: `sessionStart`, `userPromptSubmitted`, `preToolUse`, `postToolUse`, `preCompact`, `agentStop`, `sessionEnd`, entre otros.</li></ul> | https://docs.github.com/en/copilot/reference/hooks-reference |
| 7 | <ul><li>Skills como `/nombre`; `.claude/commands/*.md` funcionan como comandos.</li><li>**Los prompt files no están soportados.**</li></ul> | cli-command-reference; https://docs.github.com/en/copilot/reference/customization-cheat-sheet |
| 8 | `COPILOT_CLI=1` y `COPILOT_AGENT_SESSION_ID`. Solo figuran en el changelog oficial; la doc de variables lista únicamente las de entrada | https://github.com/github/copilot-cli/blob/main/changelog.md |

### VS Code

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>**Copilot harness:** `.github/copilot-instructions.md`, `AGENTS.md` (incluidos los anidados) y `.github/instructions/**`, sumados. Que lea `CLAUDE.md`/`GEMINI.md` en VS Code: `[No verificado]` (el runtime de CLI sí los lee).</li><li>**Local harness:** `AGENTS.md` raíz (`chat.useAgentsMdFile`, activo); anidados con `chat.useNestedAgentsMdFiles` (inactivo por defecto); `CLAUDE.md` con `chat.useClaudeMdFile`.</li></ul> | https://code.visualstudio.com/docs/agent-customization/custom-instructions |
| 2 | <ul><li>Proyecto: `.github/skills/`, `.claude/skills/`, `.agents/skills/`.</li><li>Usuario: `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/`.</li></ul> | https://code.visualstudio.com/docs/agent-customization/agent-skills |
| 3 | `[No verificado]`. Solo está documentado que una skill del Marketplace y otra local con el mismo nombre aparecen las dos en la página de Skills | agent-skills (§"Install a skill") |
| 4 | <ul><li>`.github/agents/` (`.agent.md` o `.md`) y `~/.copilot/agents/`.</li><li>**`.claude/agents/*.md` en formato Claude**, en los dos harness.</li></ul> | https://code.visualstudio.com/docs/agent-customization/custom-agents; https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference |
| 5 | <ul><li>**`.mcp.json` (`mcpServers`, portable)** lo lee directamente el Copilot harness.</li><li>`.vscode/mcp.json` (clave `servers`) es el formato de VS Code/Local. Se reenvía al Copilot harness, salvo los servers con `${input:}` o `${command:}`.</li><li>Los dos dependen de Workspace Trust.</li><li>JSONC: `[No verificado]`.</li></ul> | https://code.visualstudio.com/docs/agents/reference/mcp-configuration; https://code.visualstudio.com/docs/agents/run/manage-mcp-servers |
| 6 | <ul><li>En preview.</li><li>El Copilot harness usa el formato y las fuentes de Copilot CLI, incluido `.claude/settings*.json`.</li><li>El Local harness usa `chat.useHooks` y `chat.hookFilesLocations`.</li></ul> | https://code.visualstudio.com/docs/agent-customization/hooks |
| 7 | <ul><li>Skills como `/nombre`.</li><li>`.github/prompts/*.prompt.md` **solo funciona en el Local harness**.</li></ul> | https://code.visualstudio.com/docs/agent-customization/prompt-files |
| 8 | Las release notes de la 1.121 anuncian `VSCODE_AGENT`; issues posteriores lo cambian a `AI_AGENT=github_copilot_vscode_agent`. La doc vigente no lo menciona: verificación parcial | https://code.visualstudio.com/updates/v1_121; https://github.com/microsoft/vscode/issues/320127; https://github.com/microsoft/vscode/issues/326069 |

### Copilot cloud agent (GitHub.com)

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>`.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md` (`applyTo`), `AGENTS.md` en cualquier lugar ("the nearest… takes precedence"), un único `CLAUDE.md` o `GEMINI.md` en la raíz, e instrucciones de la organización.</li><li>No hay precedencia definida entre tipos.</li></ul> | https://docs.github.com/en/copilot/reference/custom-instructions-support |
| 2 | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills |
| 3 | `[No verificado]` | — |
| 4 | <ul><li>`.github/agents/NOMBRE.agent.md` (caracteres `.-_a-zA-Z0-9`); el cuerpo admite hasta 30 000 caracteres.</li><li>`.claude/agents/`: `[No verificado]`.</li></ul> | https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/create-custom-agents |
| 5 | <ul><li>**Settings del repo → Copilot → MCP servers**: JSON con `mcpServers`, `tools` y `type` obligatorios; secretos `COPILOT_MCP_*`.</li><li>Sin aprobación: usa las tools solo.</li><li>No está documentado que lea `.mcp.json`.</li></ul> | https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers |
| 6 | Solo `.github/hooks/*.json` y solo `bash`/`command` (ignora `powershell`) | https://docs.github.com/en/copilot/reference/hooks-reference (§"Cloud agent execution environment") |
| 7 | <ul><li>Sin prompt files.</li><li>Elige las skills solo; los agentes se eligen en el panel.</li><li>`/nombre`: `[No verificado]`.</li></ul> | customization-cheat-sheet |
| 8 | `COPILOT_AGENT_PROMPT` y `GITHUB_COPILOT_API_TOKEN` en el sandbox. No hay una variable dedicada a la detección | hooks-reference (§"Cloud agent execution environment") |

## Cursor

Editor y CLI `agent`. Docs: https://cursor.com/docs

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>`.cursor/rules/**/*.mdc`: **la extensión `.mdc` es obligatoria**; un `.md` se ignora. Frontmatter `description`, `globs`, `alwaysApply`.</li><li>`AGENTS.md` raíz y anidados; el más específico gana.</li><li>**También lee `CLAUDE.md`**, siempre aplicado.</li><li>`.cursorrules` es legacy.</li><li>Precedencia: Team → Project → User.</li></ul> | https://cursor.com/docs/rules; https://cursor.com/help/customization/rules |
| 2 | <ul><li>Proyecto: `.agents/skills/`, `.cursor/skills/`.</li><li>Por compatibilidad: `.claude/skills/`, `.codex/skills/` y sus `~/`.</li></ul> | https://cursor.com/docs/skills |
| 3 | `[No verificado]` para skills. La regla documentada de "por ruta completa, aplican las dos" es para reglas | https://cursor.com/help/customization/rules |
| 4 | <ul><li>`.cursor/agents/`, `.claude/agents/`, `.codex/agents/` y sus `~/`.</li><li>Markdown + YAML: `name`, `description`, `model`, `readonly`, `is_background`.</li><li>Proyecto > usuario; `.cursor/` > `.claude/` > `.codex/`.</li><li>Que entienda el TOML de Codex: `[No verificado]` (probablemente no).</li></ul> | https://cursor.com/docs/subagents |
| 5 | <ul><li>`.cursor/mcp.json` y `~/.cursor/mcp.json`, clave `mcpServers`; si se repite un nombre, gana el del proyecto.</li><li>La tabla marca `type: "stdio"` como obligatorio, aunque los ejemplos lo omiten.</li><li>La CLI exige `agent mcp enable <id>` o `--approve-mcps` para servers del proyecto.</li><li>JSONC: `[No verificado]`.</li></ul> | https://cursor.com/docs/mcp; https://cursor.com/docs/cli/mcp |
| 6 | <ul><li>`.cursor/hooks.json`: `{"version":1,"hooks":{…}}`, eventos camelCase (`sessionStart`, `preToolUse`, `beforeShellExecution`, `afterFileEdit`, `preCompact`, `stop`…). Solo en un workspace confiable.</li><li>**También carga por defecto los hooks de `.claude/settings*.json`.**</li></ul> | https://cursor.com/docs/hooks; https://cursor.com/docs/reference/third-party-hooks |
| 7 | `.cursor/commands/*.md` es legacy: las docs empujan la migración a skills (`/migrate-to-skills`) | https://cursor.com/changelog/1-6; https://cursor.com/docs/skills |
| 8 | `CURSOR_AGENT` (no vacío; el valor no está documentado); `CURSOR_SANDBOX` cuando corre en sandbox | https://cursor.com/docs/agent/tools/terminal; https://cursor.com/docs/agent/security/run-modes |

## Codex CLI (OpenAI)

La extensión IDE y la app de escritorio comparten la config. Las URLs `developers.openai.com/codex/*` redirigen a `learn.chatgpt.com/docs/*`.

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>Global: `~/.codex/AGENTS.override.md` o `AGENTS.md`.</li><li>Proyecto: recorre de la raíz del repo al cwd; en cada directorio toma el primero entre `AGENTS.override.md`, `AGENTS.md` y los nombres de `project_doc_fallback_filenames`. Concatena hasta un tope de **32 KiB**.</li><li>`CLAUDE.md` no se lee por defecto.</li></ul> | https://learn.chatgpt.com/docs/agent-configuration/agents-md |
| 2 | <ul><li>`.agents/skills/` (del cwd a la raíz), `~/.agents/skills/`, `/etc/codex/skills`.</li><li>`~/.codex/skills` está deprecado; solo aparece en el código (`codex-rs/ext/skills/src/host_roots.rs`, commit `184c9c5`): `[No verificado]`.</li></ul> | https://learn.chatgpt.com/docs/build-skills; https://github.com/openai/codex |
| 3 | "If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors" | https://learn.chatgpt.com/docs/build-skills |
| 4 | <ul><li>**TOML**: `.codex/agents/*.toml` y `~/.codex/agents/`, con `name`, `description` y `developer_instructions` obligatorios.</li><li>No lee `.claude/agents/`.</li></ul> | https://learn.chatgpt.com/docs/agent-configuration/subagents |
| 5 | <ul><li>`[mcp_servers.<nombre>]` en `.codex/config.toml`, **solo en proyectos confiables** (`projects."<ruta>".trust_level`), o en `~/.codex/config.toml`.</li><li>stdio: `command`, `args`, `env`, `cwd`; sin clave `type`.</li></ul> | https://learn.chatgpt.com/docs/extend/mcp; https://learn.chatgpt.com/docs/config-file/config-basic |
| 6 | <ul><li>`.codex/hooks.json` o `[hooks]` en `config.toml`.</li><li>Eventos `SessionStart`, `PreToolUse`, `PostToolUse`, `PreCompact`, `Stop`…</li><li>Confianza por hash de contenido (`/hooks`); solo en proyectos confiables.</li></ul> | https://learn.chatgpt.com/docs/hooks |
| 7 | Los custom prompts están **deprecados** y solo existen a nivel usuario (`~/.codex/prompts/`). El reemplazo son las skills (`$skill`, `/skills`) | https://learn.chatgpt.com/docs/custom-prompts |
| 8 | `[No verificado]`. El código fuente define `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, `CODEX_VERSION` y `CODEX_SANDBOX` (commit `184c9c5`: `core/src/exec_env.rs`, `core/src/spawn.rs`), pero no están documentadas | https://learn.chatgpt.com/docs/config-file/environment-variables; https://github.com/openai/codex |

## Gemini CLI

Para el tier gratuito y Google One fue reemplazado por Antigravity CLI. Docs: https://geminicli.com/docs

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>`GEMINI.md` por defecto: global, workspace y padres, más los "JIT" de los directorios que toca una tool. Se concatenan.</li><li>`context.fileName` acepta una lista, por ejemplo `["AGENTS.md","GEMINI.md"]`.</li></ul> | https://geminicli.com/docs/cli/gemini-md/ |
| 2 | <ul><li>`.gemini/skills/` o el alias **`.agents/skills/`**.</li><li>Usuario: `~/.gemini/skills/` o `~/.agents/skills/`.</li></ul> | https://geminicli.com/docs/cli/skills/ |
| 3 | <ul><li>workspace > user > extension > built-in.</li><li>En el mismo nivel, `.agents/skills/` le gana a `.gemini/skills/`.</li></ul> | https://geminicli.com/docs/cli/skills/ (§"Precedence and aliases") |
| 4 | `.gemini/agents/*.md` con YAML: `name` y `description` obligatorios; opcionales `tools`, `mcpServers`, `model`… | https://geminicli.com/docs/core/subagents/ |
| 5 | <ul><li>`.gemini/settings.json`, clave `mcpServers` (`command`, `args`, `env`, `cwd`, `trust`…).</li><li>**En una carpeta no confiable ignora los settings del workspace y no conecta MCP.**</li><li>La confianza de carpetas viene activada por defecto (`security.folderTrust.enabled`, `default: true`) según la referencia de configuración y el schema, aunque la página de trusted folders dice "disabled by default".</li></ul> | https://geminicli.com/docs/tools/mcp-server/; https://geminicli.com/docs/cli/trusted-folders/; https://geminicli.com/docs/reference/configuration/; https://github.com/google-gemini/gemini-cli/blob/main/packages/cli/src/config/settingsSchema.ts |
| 6 | `hooks` en `settings.json`; eventos `SessionStart`, `BeforeTool`, `AfterTool`, `PreCompress`, `SessionEnd`…; timeout en ms | https://geminicli.com/docs/hooks/ |
| 7 | `.gemini/commands/*.toml` (`prompt`, `description`), con namespaces por subcarpeta. No se cargan en carpetas no confiables | https://geminicli.com/docs/cli/custom-commands/ |
| 8 | `GEMINI_CLI=1` | https://geminicli.com/docs/tools/shell/ |

## Windsurf / Devin (Cognition)

**Devin Local / Devin CLI** reemplaza a Windsurf/Cascade.

| # | Verificado | Fuente |
|---|---|---|
| 1 | <ul><li>`AGENTS.md` (recomendado), `AGENTS.local.md`, `CLAUDE.md`, `.windsurfrules`, `.devin/rules/*.md`, `.windsurf/rules/`, `.cursor/rules/`.</li><li>`read_config_from` (`agents_standard`, `cursor`, `windsurf`, `claude`) está todo en `true` por defecto.</li><li>No lee `GEMINI.md`.</li></ul> | https://docs.devin.ai/cli/extensibility/rules.md; https://docs.devin.ai/cli/reference/configuration/read-config-from.md |
| 2 | <ul><li>Proyecto: `.agents/skills/`, `.devin/skills/`, `.windsurf/skills/` y `.claude/skills/` (por la importación de Claude).</li><li>Usuario: `~/.agents/skills/`, `~/.config/devin/skills/`.</li></ul> | https://docs.devin.ai/cli/extensibility/skills/overview.md |
| 3 | `[No verificado]` | — |
| 4 | <ul><li>`.devin/agents/`, `.agents/agents/`, `~/.config/devin/agents/`.</li><li>`<nombre>.md` o `<nombre>/AGENT.md`, con `name`, `description`, `model`, `allowed-tools`.</li></ul> | https://docs.devin.ai/cli/subagents.md |
| 5 | <ul><li>`.devin/mcp_config.json` (y `.local.json`), clave `mcpServers`.</li><li>**Por defecto también importa `.mcp.json`, `.claude/settings*.json` y `.cursor/mcp.json`**, lo que puede duplicar servers.</li><li>La doc es inconsistente: `devin-local.md` todavía dice `.devin/config.json`.</li></ul> | https://docs.devin.ai/cli/extensibility/mcp/configuration.md; https://docs.devin.ai/desktop/devin-local.md |
| 6 | <ul><li>`.devin/hooks.v1.json` o `hooks` en `.devin/config.json` / `.claude/settings*.json`.</li><li>Eventos `PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`…</li><li>**Corren todas las fuentes.**</li></ul> | https://docs.devin.ai/cli/extensibility/hooks/overview.md |
| 7 | <ul><li>No hay directorio de comandos: las skills funcionan como `/nombre`.</li><li>`.claude/commands/` se importa como skills.</li><li>Los workflows no existen en Devin Local.</li></ul> | https://docs.devin.ai/cli/extensibility/skills/creating-skills.md; https://docs.devin.ai/desktop/devin-local.md |
| 8 | `AI_AGENT=devin_<versión>_agent`, salvo que otro agente ya la haya definido (CLI v3000.11.1) | https://docs.devin.ai/cli/changelog/stable |

**Cascade (legacy, solo plugin de JetBrains en mantenimiento):**
- Reglas en `.devin/rules/` o `.windsurf/rules/`.
- Skills en `.devin/skills/`, `.windsurf/skills/` y `.agents/skills/`.
- MCP solo de usuario, en `~/.config/devin/mcp_config.json`.

Fuente: https://docs.devin.ai/desktop/cascade/skills, https://docs.devin.ai/desktop/cascade/mcp

**Devin Cloud:**
- Reglas en `AGENTS.md` (primeros 16 KiB).
- Skills: `.agents/skills/` recomendado; escanea nueve rutas, entre ellas `.claude/`, `.github/`, `.cursor/` y `.codex/`.
- MCP solo desde la UI o plugins.
- Sin subagentes.

Fuente: https://docs.devin.ai/product-guides/skills.md, https://docs.devin.ai/work-with-devin/mcp.md

---

## Contradicciones con la matriz del plan

1. **VS Code / Copilot MCP:** el plan generaba `.vscode/mcp.json` con `servers`. El Copilot harness (default) y Copilot CLI leen **`.mcp.json` con `mcpServers`**, y la CLI ya no lee `.vscode/mcp.json`.
2. **Prompt files de Copilot** (`.github/prompts/`): solo funcionan en el Local harness de VS Code; en CLI, cloud y Copilot harness, no.
3. **Riesgo de "skill listada dos veces" en Copilot:** no ocurre en CLI; gana la primera (`.github/` > `.agents/` > `.claude/`). En el cloud agent y en el Local harness: `[No verificado]`.
4. **`.claude/agents/`** lo leen Claude Code, Copilot CLI, VS Code (los dos harness) y Cursor. No era solo VS Code.
5. **Copilot también lee `CLAUDE.md`, `GEMINI.md` y `.claude/rules/`.** Cursor y Devin también leen `CLAUDE.md`. Un `CLAUDE.md` con `@AGENTS.md` puede **duplicar el contexto** en esos agentes.
6. **Claude Code lee `AGENTS.md` de forma nativa desde v2.1.277**, si no hay `CLAUDE.md`.
7. **Windsurf → Devin Local/CLI.** Tiene MCP de proyecto (`.devin/mcp_config.json`), subagentes, hooks y lee `.agents/skills/`. Los hooks, subagentes y comandos que el plan daba por desconocidos están documentados.
8. **Cursor:** las reglas propias exigen `.mdc`; tiene hooks documentados; los comandos son legacy.
9. **Codex:** subagentes en TOML; MCP y hooks de proyecto solo en proyectos confiables; prompts deprecados y solo de usuario.
10. **Gemini CLI:** hay que agregarle las notas de confianza de carpeta, y considerar a Antigravity CLI como sucesor.

## Implicancias para F2

Son **propuestas**: se deciden en F2 con D-04, D-05 y D-06.

- **Reglas.**
  - `AGENTS.md` es la fuente única.
  - Para Claude Code ≥ 2.1.281 con el plugin de `AGENTS.md` activo, **no crear `CLAUDE.md` si no existe**, porque Claude ya lee `AGENTS.md` y Copilot, Cursor y Devin cargarían los dos. Si `doctor` no puede confirmar esas condiciones, usar `CLAUDE.md` con `@AGENTS.md`.
  - Si el humano ya tiene `CLAUDE.md`, inyectar el bloque con `@AGENTS.md`, porque sin el import Claude no lo lee.
  - `exo doctor` verifica que Claude Code sea ≥ 2.1.281 y que el plugin `cc-plugin-agents-md@builtin` esté activo.
- **Skills.**
  - Si los destinos son solo Claude Code y Copilot, **una única copia en `.claude/skills/`** llega a los dos.
  - Con Codex o Gemini como destino, hace falta `.agents/skills/`. Si además está Claude Code, también `.claude/skills/`. Como las copias son idénticas, la sombra en Copilot no hace daño.
  - En Cursor y Devin, los duplicados son `[No verificado]`: probar en el checklist de F2.
- **MCP.**
  - `.mcp.json` con `mcpServers` es común a Claude Code, Copilot CLI, el Copilot harness de VS Code y Devin (que lo importa). Copilot exige `tools`; que Claude Code tolere esa clave es `[No verificado]` (probar en F2).
  - Cursor usa `.cursor/mcp.json` (incluir `"type":"stdio"`).
  - Codex usa un bloque marcado en `.codex/config.toml`. **Sin `tomlkit`: invariante 4 de 02-ARQUITECTURA §2.13 (solo stdlib).**
  - Gemini usa `.gemini/settings.json`.
  - Avisar que Codex y Gemini cargan el MCP de proyecto solo en carpetas confiables.
  - Ver también D-23 (bloqueo por política).
- **Subagentes.**
  - `.claude/agents/*.md` cubre Claude Code, Copilot CLI y VS Code, y Cursor.
  - Hay que generar `.github/agents/*.agent.md` (cloud agent), `.codex/agents/*.toml`, `.gemini/agents/*.md` y `.devin/agents/*.md` o `.agents/agents/`.
- **Hooks.** Copilot, Cursor y Devin **también corren los hooks de `.claude/settings.json`**. No duplicar el mismo hook en `.github/hooks/` para no ejecutarlo dos veces.
- **Comandos.** Usar skills como comandos en todos los agentes; no generar prompt files ni `.cursor/commands/`.
- **Detección.**
  - Variables por agente: `CLAUDECODE` / `CLAUDE_CODE_CHILD_SESSION` (Claude Code), `COPILOT_CLI` (Copilot CLI), `CURSOR_AGENT` (Cursor), `GEMINI_CLI` (Gemini).
  - `AI_AGENT` (Claude Code, Devin, VS Code) se está volviendo una convención común: comparar por prefijo.
  - Ninguna de estas señales se usa para seguridad.
