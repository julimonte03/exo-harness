# 01 — Visión y alcance

## Qué construimos

Un motor que se instala en un repositorio y lo vuelve **gobernado**: cada cambio pasa por un ciclo spec-driven proporcional a su riesgo, el contexto y las decisiones sobreviven entre sesiones gracias a una memoria persistente, el uso de IA queda trazado, los gates de calidad y seguridad corren siempre, y todo eso funciona con el agente que use cada persona del equipo (Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI, Windsurf/Devin u otro compatible con `AGENTS.md`).

Además, a diferencia del arnés original, el motor puede **llegar a un proyecto que ya existe**, entenderlo mediante ingeniería inversa con evidencia y dejarlo listo para trabajar con el ciclo gobernado.

## Principios de diseño

1. **Fuente canónica única, adaptadores generados.** Reglas, skills, subagentes y servidor MCP se escriben una sola vez. El instalador los traduce a los archivos que lee cada agente. Ningún archivo específico de un agente se edita a mano.
2. **Estándares abiertos primero.** `AGENTS.md` para reglas, Agent Skills (`SKILL.md`) para skills, MCP para herramientas. Lo propietario de cada agente vive solo en su adaptador.
3. **Determinista en código, juicio en skills.** Lo que se puede verificar con código (fitness, speclint, inventario del repo, guard de secretos, validación de artefactos) va al runtime. Lo que requiere juicio va a las skills.
4. **Enforced antes que advisory.** El capítulo 12.2 del reporte reconoce que casi todos los controles dependían del cumplimiento del agente. Acá se agrega enforcement agnóstico con git hooks y un `arnes check` que corre en CI.
5. **Núcleo sin dependencias, extras opcionales.** El núcleo sigue siendo solo biblioteca estándar (invariante del reporte). La memoria vectorial y los parsers avanzados son extras que, si faltan, degradan con un aviso claro.
6. **Por proyecto.** Config, specs, wiki, lock de archivos generados y skills viven en el repo y se versionan. La memoria personal vive en el usuario.
7. **Nunca pisar archivos del humano.** Bloques marcados en archivos compartidos y un lock con hashes que detecta cambios manuales.
8. **Degradación explícita.** Si un agente no tiene subagentes o hooks, la skill lo dice textualmente y aplica el camino inline (el protocolo de degradación del reporte, §2.5).

## Qué se conserva del reporte

| Pieza del reporte | Cómo queda en el motor |
|---|---|
| Runtime Python ≥ 3.10 solo stdlib, con sus 11 invariantes (§4.6) | Se conserva, con rutas y nombres nuevos, más 6 invariantes propias (ver `02-ARQUITECTURA.md`) |
| Ciclo SDD/SPDD por fases, tiers 1–4, reglas FM-01…FM-30, envelope, `change-root` | Se conserva el contrato completo |
| Jueces advisory, AI Usage Record, gates con comentario único por gate | Se conservan; además se verifican en `arnes check` |
| engram: API de 15 tools, `topic_key`, guard S1, export redactado | Se conserva la API; cambia el motor de búsqueda (F3) |
| Servidor MCP JSON-RPC stdio con 22 tools en 3 grupos | Se conservan los grupos; nombres sin prefijo `san_ai_toolkit` |
| 12 plugins de Devin con `requiredPlugins`/`optionalPlugins` | Pasan a ser **packs** del instalador con la misma semántica de dependencias |
| `validate_plugin.py`, smoke E2E, `_verify_p0.py` | Pasan a `arnes validate`, suite smoke y `arnes p0` |
| Matriz DPA, RACI, threat model lite | Se conservan como datos configurables por organización |

## Qué cambia

- Ya no depende de Devin: los caminos `.devin/config.json`, `.devin/skill-registry.md` y `.sdd/context.md` pasan a `.arnes/config.json`, `.arnes/skill-registry.md` y `.arnes/context.md`.
- El ticket deja de ser obligatoriamente de Jira: el tracker es configurable (Jira, GitHub Issues, GitLab, Linear o ninguno).
- La distribución deja de ser `git-subdir` con `ref` de rama: el motor tiene versión propia y cada proyecto registra en su lock qué versión generó sus archivos.
- Hay CI real del motor (el reporte admite que no la había, §8.4 y §12.1 #11).

## Qué se descarta y por qué

| Pieza | Motivo |
|---|---|
| Playbooks y knowledge notes (`shared/`) | Decisión del dueño: todo va en un mismo arnés. Su contenido útil ya estaba duplicado en skills (regla de gates del §8.1) |
| `tools/devin_sync.py`, Automations, bootstrap de org | Mecanismos propios de Devin sin equivalente agnóstico necesario |
| `plugins/core/src/index.py` (fastapi) | Sin propósito documentado en el reporte |
| Scaffolding de `.github/workflows/` de la plataforma de origen | Específico de la organización de origen |
| Overlays de persona | No se descartan del todo: quedan como opcionales de baja prioridad (D-17) |

## Qué se agrega

- **M-A. Agnóstico e instalable con un comando.** Detecta el agente (o pregunta), genera los archivos que corresponden y se puede desinstalar sin dejar rastros.
- **M-B. Ingeniería inversa y adopción.** Inventario determinista del repo, extracción asistida de specs "as-is" con evidencia `path:line`, auditoría de precisión, validación humana y backlog de adopción que se ejecuta con el propio ciclo SDD.
- **M-C. Memoria híbrida.** Búsqueda léxica (FTS5) más semántica (vectores), con SQLite como fuente de verdad, backends intercambiables (sqlite-vec local, Qdrant en servidor) y un experimento medible que decide el default.
- **M-D. Mejoras propuestas por este plan.** Enforcement con git hooks y CI, specs vivas por capacidad (los cambios producen deltas que se integran al archivar), hooks de sesión para memoria automática en los agentes que los soportan, y evals de comportamiento de las skills principales.

## Fuera de alcance de la v1

La GUI de observabilidad (ADR-0005 del reporte), una memoria de equipo compartida en servidor (solo se experimenta), el soporte detallado de más de seis agentes (el adaptador genérico cubre al resto vía `AGENTS.md` y `.agents/skills`) y la publicación en marketplaces.

## Definición de éxito (hito M4, v1.0)

| # | Criterio | Cómo se mide |
|---|---|---|
| 1 | Instalar el motor y adoptarlo en un repo de prueba en menos de 2 minutos, sin editar archivos a mano, para Claude Code y Copilot | Cronometrado en el checklist manual de F2/F8 |
| 2 | Agregar un segundo agente a un proyecto ya instalado sin romper el primero | `arnes add-agent cursor` + golden tests |
| 3 | Un cambio Tier 1 y uno Tier 3 completos con Claude Code producen artefactos válidos | `arnes speclint` y `arnes check` en verde |
| 4 | La ingeniería inversa sobre un repo de 20–50 mil líneas cubre al menos el 80 % de los módulos, con precisión de evidencia auditada de al menos 90 % | `.arnes/discovery/coverage.md` y reporte de auditoría |
| 5 | El experimento de memoria tiene reporte y decisión registrada en un ADR | `docs/evals/memory-*.md` + ADR |
| 6 | Suite verde en Linux, macOS y Windows con cobertura del runtime de al menos 85 % | CI |
