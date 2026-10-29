# ADR-0003 — Fuente canónica única y adaptadores generados

- **Estado:** Aceptada
- **Fecha:** 2026-10-29
- **Origen:** principio 1 de `docs/plan/01-VISION-Y-ALCANCE.md`; diseño en `docs/plan/02-ARQUITECTURA.md` §2.1, §2.8

## Contexto

Cada persona del equipo puede usar un agente distinto: Claude Code, Copilot, Cursor, Codex, Gemini CLI, Windsurf/Devin u otro. Los estándares abiertos (`AGENTS.md`, Agent Skills, MCP) cubren buena parte, pero no todo. La prueba empírica de F0 (`docs/spikes/agent-probe.md`) confirmó que Claude Code no lee `AGENTS.md` si hay un `CLAUDE.md` sin `@AGENTS.md`, y que no escanea `.agents/skills/`. Además, la configuración MCP, los subagentes y los hooks tienen formato y ruta propios en cada agente (`docs/agent-matrix.md`).

## Decisión

- Reglas, skills, subagentes, contratos y plantillas se escriben **una sola vez** en `content/`, en formatos abiertos: `AGENTS.md`, `SKILL.md` del estándar Agent Skills y subagentes en Markdown con frontmatter estilo Claude Code.
- El runtime tiene **un adaptador por agente**. Es **puro**: recibe el bundle canónico y devuelve operaciones (`WriteFile`, `MergeBlock`, `MergeKey`, `MirrorDir`, `Remove`), nunca escribe. Un motor común aplica esas operaciones con snapshot, escritura atómica y lock con hashes.
- Ningún archivo específico de un agente se edita a mano en los proyectos; si el humano lo modifica, el lock lo detecta como conflicto.
- Lo que es propio de cada agente vive solo en su adaptador. El adaptador genérico (`AGENTS.md` + `.agents/skills/`) siempre se instala.

## Alternativas

- **Mantener archivos por agente a mano.** Diverge enseguida y multiplica el mantenimiento por la cantidad de agentes.
- **Depender solo de `AGENTS.md` + `.agents/skills/`.** No alcanza: Claude Code no lee esa carpeta y el MCP es distinto en cada agente.
- **Symlinks hacia una única copia.** Frágiles en Windows. D-06 los deja como opción en POSIX.

## Consecuencias

- Hace falta un instalador (F2), aunque es delgado: el genérico más lo que le falta a cada agente.
- Los golden tests por adaptador y por fixture son obligatorios, y regenerarlos es explícito (`pytest --update-golden`).
- Cuando cambian las convenciones de un agente, se toca solo su adaptador y `docs/agent-matrix.md`, que lleva fecha de verificación.
- Claude Code necesita el espejo `.claude/skills/` y el bloque `@AGENTS.md` en `CLAUDE.md`. Ambos están confirmados empíricamente.
