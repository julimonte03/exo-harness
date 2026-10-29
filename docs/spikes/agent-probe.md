# Spike F0 — Prueba empírica de agentes (`agent-probe`)

Tarea 0.4 de F0. Objetivo: ver qué carga **de verdad** cada agente instalado en esta máquina, para contrastarlo con la documentación (`docs/agent-matrix.md`).

- **Fecha:** 2026-10-29
- **Máquina:** Windows 11 Enterprise 10.0.26200, Git Bash, Python 3.14.5
- **Agentes instalados:** Claude Code 2.1.312 (CLI `claude` + extensión de VS Code). VS Code con Copilot integrado, sin probar (ver "Pendientes"). No hay Copilot CLI, Cursor, Codex, Gemini CLI ni Windsurf.

## Cómo repetirla

1. Crear un repo temporal **fuera** de este repo, para que sus `.claude/` no contaminen la sesión: `mkdir agent-probe && cd agent-probe && git init`.
2. Crear estos archivos:

| Archivo | Contenido | Qué prueba |
|---|---|---|
| `AGENTS.md` | `Marca de control: MARCA-AGENTS-7731.` | ¿Se carga `AGENTS.md` cuando hay `CLAUDE.md`? |
| `CLAUDE.md` | `Marca de control: MARCA-CLAUDE-4410.` (sin `@AGENTS.md`) | Carga de `CLAUDE.md` |
| `.agents/skills/hello-probe/SKILL.md` | `name: hello-probe`, `description: … ORIGEN=agents-dir …` | Duplicado: mismo nombre en dos directorios |
| `.claude/skills/hello-probe/SKILL.md` | `name: hello-probe`, `description: … ORIGEN=claude-dir …` | Duplicado: mismo nombre en dos directorios |
| `.agents/skills/probe-agents-only/SKILL.md` | `name: probe-agents-only`, `ORIGEN=agents-dir` | ¿Se escanea `.agents/skills/`? |
| `.claude/skills/probe-claude-only/SKILL.md` | `name: probe-claude-only`, `ORIGEN=claude-dir` | ¿Se escanea `.claude/skills/`? |
| `.claude/agents/probe-sub.md` | Frontmatter `name: probe-sub`, `description`, `tools: Read` | Subagentes de proyecto |
| `echo_server.py` | Servidor MCP mínimo por stdio: `initialize`, `tools/list`, `tools/call` con una tool `echo` que devuelve `ECO: <text>` (stdlib, un mensaje JSON por línea) | MCP de proyecto |
| `.mcp.json` | `{"mcpServers": {"probe-echo": {"command": "python", "args": ["<ruta>/echo_server.py"]}}}` | MCP de proyecto |
| `.claude/settings.json` | `{"enableAllProjectMcpServers": true}` | Aprobación automática de servers del proyecto |

3. Verificar el server a mano: mandar por stdin una línea `initialize` y una `tools/call`, que deben devolver `ECO: hola`.
4. Correr, desde la raíz del repo temporal:

```bash
claude mcp list
claude -p '<preguntas 1–4: skills con "probe" y su ORIGEN, marcas MARCA-*, subagentes "probe", llamar a echo con text="ping">' \
  --max-turns 4 --allowedTools "mcp__probe-echo__echo"
claude -p 'Llamá a echo con text="ping"…' --mcp-config .mcp.json --max-turns 3 --allowedTools "mcp__probe-echo__echo"
```

5. Variables de entorno: en un shell que haya abierto el agente, correr `env | cut -d= -f1 | sort` y listar solo los **nombres**, nunca los valores, porque algunos son tokens.

## Resultados — Claude Code 2.1.312 (Windows, extensión de VS Code + CLI)

| # | Pregunta | Observado | Coincide con `03-MATRIZ-AGENTES.md` |
|---|---|---|---|
| 1 | Reglas | Con `CLAUDE.md` presente y sin `@AGENTS.md`, **`AGENTS.md` no se carga**: solo aparece `MARCA-CLAUDE-4410`. En este repo, con `@AGENTS.md`, se cargan los dos (verificado en la tarea 0.2) | Sí |
| 2 | Skills | Solo ve las de `.claude/skills/` (`hello-probe` con ORIGEN=claude-dir y `probe-claude-only`). **`.agents/skills/` no se escanea**: `probe-agents-only` no aparece | Sí |
| 3 | Duplicados | Como `.agents/skills/` no se lee, no hay duplicado: queda una sola `hello-probe`, la de `.claude/skills/` | — |
| 4 | Subagentes | `.claude/agents/probe-sub.md` aparece como subagente disponible | Sí |
| 5 | MCP de proyecto | `.mcp.json` **no se cargó**: `claude mcp list` no muestra `probe-echo`. Con `--mcp-config .mcp.json`, el CLI responde `Warning: MCP server blocked by enterprise policy: probe-echo`. **Esta organización bloquea servidores MCP fuera de una lista permitida** mediante settings administrados (no están en el registro ni en `~/.claude`) | No se pudo verificar el formato; ver hallazgo |
| 8 | Variables de entorno | `CLAUDECODE=1`, `CLAUDE_CODE_ENTRYPOINT=claude-vscode` (desde la extensión), `AI_AGENT=claude-code_<versión>_agent`, además de `CLAUDE_CODE_SESSION_ID`, `CLAUDE_PID` y otras `CLAUDE_CODE_*` | Completa el `[verificar en F0]` |

Otras señales en el mismo shell: `VSCODE_PID`, `VSCODE_IPC_HOOK` y `VSCODE_CWD` (VS Code) y `COPILOT_OTEL_FILE_EXPORTER_PATH`. Esta última sugiere que Copilot está integrado en VS Code, aunque `code --list-extensions` no lo lista como extensión.

## Hallazgo que afecta el diseño

**Una política empresarial puede bloquear el servidor MCP `exo`.** En esta máquina la organización solo permite servidores MCP de una lista. Si el servidor `exo mcp` no está en esa lista, el agente no lo carga, y las tools de memoria, observabilidad y discovery dejan de estar disponibles por MCP. Queda registrado como **D-23** en `docs/plan/04-DECISIONES.md`. La propuesta es que toda tool MCP tenga un subcomando equivalente del CLI (`exo …`, salida `--json`), que las skills sepan caer al CLI por shell, y que `exo doctor` (F2) detecte el bloqueo y lo explique.

## Pendientes

- **Formato y aprobación de `.mcp.json`:** repetir en una máquina sin esta política, o con `exo` en la lista permitida. Sale en el checklist manual de F2.
- **Copilot en VS Code:** la licencia está sin confirmar. Si está disponible, repetir los pasos 1–4 en modo agente y anotar qué skills, subagentes y servers MCP ve, en particular si lista dos veces `hello-probe`.
- **Confianza del proyecto:** según la documentación, `-p` carga los servers de proyecto sin preguntar y trata la carpeta como confiable (https://code.claude.com/docs/en/mcp, https://code.claude.com/docs/en/hooks §"Workspace trust"). Por eso la causa del bloqueo es la política y no la falta de confianza. Para descartarlo del todo, repetir en sesión interactiva.

## Anexo — archivos y prompts exactos

### `echo_server.py`

```python
"""Servidor MCP mínimo de eco (JSON-RPC 2.0 por stdio, un mensaje por línea)."""
import json
import sys

TOOLS = [{
    "name": "echo",
    "description": "Devuelve el texto recibido con el prefijo ECO:",
    "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
}]

def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    if not line.strip():
        continue
    msg = json.loads(line)
    method, msg_id = msg.get("method"), msg.get("id")
    if msg_id is None:
        continue  # notificación
    if method == "initialize":
        reply(msg_id, {
            "protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "probe-echo", "version": "0.0.1"},
        })
    elif method == "tools/list":
        reply(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        text = msg["params"].get("arguments", {}).get("text", "")
        reply(msg_id, {"content": [{"type": "text", "text": f"ECO: {text}"}]})
    else:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id,
                                     "error": {"code": -32601, "message": "method not found"}}) + "\n")
        sys.stdout.flush()
```

### `SKILL.md` (plantilla; mismo formato para las cuatro skills)

```markdown
---
name: hello-probe
description: Skill de prueba hello-probe. ORIGEN=agents-dir. Usala cuando te pidan el probe de skills.
---

# hello-probe

Respondé exactamente: "probe hello-probe desde agents-dir".
```

### `.claude/agents/probe-sub.md`

```markdown
---
name: probe-sub
description: Subagente de prueba del spike F0. Solo responde "probe-sub ok".
tools: Read
---

Respondé exactamente "probe-sub ok".
```

### Prompts

Prueba principal:

```bash
claude -p 'Esto es un spike de verificación. Respondé en una lista numerada, sin inventar y sin leer archivos del disco: (1) Copiá los nombres EXACTOS de todas las skills disponibles cuyo nombre contenga "probe", y para cada una copiá el texto ORIGEN=... de su descripción; si hay dos con el mismo nombre, decilo. (2) Copiá todas las marcas de control MARCA-... que aparezcan en tus instrucciones de proyecto (CLAUDE.md / AGENTS.md); si no ves alguna, decí cuál no ves. (3) Listá los subagentes disponibles cuyo nombre contenga "probe". (4) Llamá a la tool MCP echo del servidor probe-echo con text="ping" y copiá la respuesta literal.' --max-turns 4 --allowedTools "mcp__probe-echo__echo"
```

MCP explícito:

```bash
claude -p 'Llamá a la tool MCP echo del servidor probe-echo con text="ping" y respondé solo con el texto literal que devuelve.' --mcp-config .mcp.json --max-turns 3 --allowedTools "mcp__probe-echo__echo"
```

Verificación de las reglas de este repo (tarea 0.2), desde la raíz de `exo`:

```bash
claude -p "Sin usar herramientas ni leer archivos, respondé solo con lo que ya tenés cargado como instrucciones de proyecto, en 4 líneas: (1) qué archivos de reglas de proyecto tenés cargados, (2) cómo se llama el motor y qué nombre de trabajo usa el plan, (3) el texto de la invariante 12, (4) la regla de ramas por fase." --max-turns 1
```
