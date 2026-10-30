# ADR-0006 — Agentes de la v1: base agnóstica con detección

- **Estado:** Aceptada
- **Fecha:** 2026-10-30
- **Decisión:** D-04 (`docs/plan/04-DECISIONES.md`)

## Contexto

El dueño quiere que el motor sea agnóstico: que funcione con el agente que use cada persona y que, al instalarlo, detecte cuál se está usando. Si no se pudiera, el alcance serían solo Claude Code y GitHub Copilot.

La verificación de F0 (`docs/agent-matrix.md`) muestra que sí se puede:

- `AGENTS.md` lo leen Copilot, Cursor, Codex, Devin y Claude Code; Claude Code, desde v2.1.277 y si no hay `CLAUDE.md`.
- `.agents/skills/` lo leen Copilot, Cursor, Codex, Gemini y Devin.
- Lo único específico de cada agente son la carpeta de skills de Claude Code, los subagentes, los hooks, los permisos y la config MCP. Esta última ya es opcional por ADR-0005.
- Cada agente deja señales detectables: archivos en el repo, ejecutables en el `PATH` y variables de entorno.

Las variables verificadas son `CLAUDECODE` (Claude Code), `COPILOT_CLI` (Copilot CLI), `AI_AGENT` (VS Code, Devin, Claude Code), `CURSOR_AGENT` (Cursor) y `GEMINI_CLI` (Gemini).

## Decisión

1. **Base agnóstica, siempre:** el bloque de reglas en `AGENTS.md`, la config y el lock del motor, y las skills en la carpeta que lean los agentes destino (ADR-0007). Cualquier agente compatible con `AGENTS.md` recibe reglas y skills sin un adaptador propio.
2. **Adaptadores específicos de la v1:** solo **Claude Code** y **GitHub Copilot** (VS Code y CLI), con soporte completo, golden tests y checklist manual con agentes reales. El cloud agent de Copilot queda fuera porque los repos van a estar en Azure DevOps (ADR-0008).
3. **Detección al instalar** (`exo init`), en este orden:
   1. `--agents a,b`;
   2. la config previa;
   3. archivos del repo (`CLAUDE.md`, `.claude/`, `.github/copilot-instructions.md`, `.cursor/`, `.codex/`, `GEMINI.md`, `.devin/`…);
   4. ejecutables en el `PATH` (`claude`, `copilot`, `code`, `cursor`, `codex`, `gemini`, `devin`);
   5. variables de entorno del agente que está corriendo el comando.

   En terminal interactiva muestra lo detectado preseleccionado para confirmar; sin terminal, instala lo detectado con señales fuertes y lo informa.
4. **Agentes detectados sin adaptador propio** (Cursor, Codex, Gemini/Antigravity, Devin): se informan y quedan cubiertos por la base agnóstica. Si a uno le falta algo para leer las reglas, el instalador imprime el paso manual. Por ejemplo, Gemini lee `GEMINI.md` por defecto y necesita `context.fileName` para leer `AGENTS.md`.

## Alternativas

- **Adaptadores propios para los seis agentes (Tier 2 del plan).** Más trabajo y mantenimiento constante, porque las convenciones cambian casi cada semana. El valor extra (subagentes, hooks) es chico frente a la base agnóstica.
- **Solo Claude Code y Copilot, sin base agnóstica.** No cumple el objetivo de que el motor sirva con otro agente.

## Consecuencias

- F2 se achica: el genérico más dos adaptadores. La interfaz de adaptadores (`02-ARQUITECTURA.md` §2.8) se mantiene, así que sumar uno después es agregar un módulo y sus golden tests.
- Los tests de detección cubren los seis agentes, aunque solo dos tengan adaptador.
- El checklist manual de F2 se hace con Claude Code y Copilot. Copilot requiere confirmar la licencia en esta máquina.
- La detección por variables de entorno nunca se usa para decisiones de seguridad.
