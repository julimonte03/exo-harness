# Checklist F2 — Agentes reales (criterio 8)

Verifica que un proyecto adoptado con `exo init` funcione con los agentes de Tier 1 (ADR-0006).

## Claude Code — 2026-11-02, Windows 11, Claude Code 2.1.312

Pasos (repetibles):

1. Proyecto vacío con `git init`. Corré `exo init --agents claude-code --yes`.
2. Abrí una sesión nueva en el proyecto y pedile:
   - los nombres de las skills de proyecto;
   - el título de la primera sección `##` de sus instrucciones y de qué archivo vienen;
   - los subagentes que empiezan con `sdd-`;
   - que ejecute `exo change list --json` y copie la salida.
3. Si en vez de una sesión interactiva usás `claude -p`, sumá `--max-turns 6`.

| Verificación | Resultado |
|---|---|
| `exo init` genera solo lo de Claude Code | OK: 11 archivos. `AGENTS.md` y `.gitignore` con bloque; `.claude/skills/` (3); `.claude/agents/` (4); `.claude/settings.json`; `.exo/` (config, lock, registro). No crea `CLAUDE.md` ni `.agents/skills/` (ADR-0007) |
| Ve las skills | OK: `hello-exo`, `memory-protocol`, `sdd-status` |
| Carga las reglas sin `CLAUDE.md` | OK: cita `## Siempre` "de `AGENTS.md`, en la raíz del repo" |
| Ve los subagentes | OK: `sdd-explorer`, `sdd-implementer`, `sdd-judge`, `sdd-verifier` |
| Ejecuta `exo` sin pedir permiso | **Solo con el workspace confiable.** Con `claude -p` en una carpeta nueva, Claude Code avisa `Ignoring 1 permissions.allow entry from .claude/settings.json: this workspace has not been trusted` y el comando pide aprobación. La regla aplica después de aceptar la confianza una vez en modo interactivo |
| Regla de PowerShell | En Windows, el agente intentó primero con su herramienta de PowerShell. Con `--allowedTools "PowerShell(exo:*)"` ejecutó `exo change list --json` y devolvió `{"schema": 1, "changes": []}`. Por eso el adaptador ahora agrega `Bash(exo:*)` y `PowerShell(exo:*)` |
| MCP | No aplica: ADR-0005 (opcional y apagado) y política de la organización (D-23) |

Hallazgos que cambiaron el código:
- `PowerShell(exo:*)` se suma a `permissions.allow`.
- `exo doctor` tiene un chequeo `claude-trust`, que avisa si el workspace todavía no es confiable. Lee `~/.claude.json`, solo lectura.

## GitHub Copilot — pendiente (verificación manual)

En esta máquina no está confirmada la licencia de Copilot. Para verificarlo:

1. En un proyecto de prueba, corré `exo init --agents copilot --yes`, o `claude-code,copilot`.
2. En VS Code, abrí el chat de Copilot en modo agente y preguntá qué skills e instrucciones de proyecto tiene.
   - Esperado: las skills de `.claude/skills/` y las reglas de `AGENTS.md`.
3. Preguntá por los agentes personalizados.
   - Esperado: los de `.claude/agents/`.
4. Pedile que ejecute `exo change list --json` en la terminal.
   - Copilot puede pedir confirmación: es su política de herramientas, no un error del motor.
5. Anotá el resultado en este archivo y en `docs/plan/PROGRESO.md`.
