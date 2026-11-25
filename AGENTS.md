# AGENTS.md — Desarrollo del motor `exo`

Este repo construye un motor de desarrollo gobernado por proyecto y agnóstico de agente. El plan vive en `docs/plan/` y manda sobre todo lo demás. La transcripción del sistema original es privada: vive solo en local, en `docs/referencia/` (ignorada por git, D-46), y nunca se sube. Es referencia, no especificación; si contradice al plan, gana el plan.

**Nombre:** el plan usa `arnes` como nombre de trabajo; el motor se llama `exo` (D-01, `docs/adr/0001-nombre-y-layout.md`). Donde el plan dice `arnes`, `.arnes/`, `ARNES_` o `arnes-`, leé `exo`, `.exo/`, `EXO_` y `exo-`.

## Antes de trabajar

- Leé `docs/plan/PROGRESO.md` para saber cuál es la fase activa y trabajá **solo** dentro de esa fase (`docs/plan/fases/F<n>-*.md`).
- Si una tarea requiere una decisión que no está en `docs/plan/04-DECISIONES.md`, no la inventes: agregala como `D-xx` con opciones y recomendación, y preguntá.
- No inventes comportamiento que la referencia marca como `[No verificado]`.

## Invariantes (no negociables)

1. `src/exo` usa solo biblioteca estándar, salvo `memory/backends/` y `memory/embeddings/`, que importan de forma diferida y fallan con mensaje claro.
2. Escrituras atómicas (temporal + `os.replace`), en binario, preservando fines de línea del humano.
3. Idempotencia: si nada cambia, no se escribe ni se crea snapshot.
4. Snapshot antes de mutar cualquier archivo gestionado.
5. Los adaptadores son puros: calculan operaciones, nunca escriben.
6. Nunca se pisa un archivo generado que el humano modificó (hash distinto al del lock) sin `--force`.
7. Skills copiadas byte a byte; nunca se templatan.
8. SQLite es la fuente de verdad de la memoria; los índices son derivados.
9. Servidor MCP: stdout solo JSON-RPC, logs a stderr.
10. Ingeniería inversa: solo lectura sobre el código del proyecto analizado.
11. Nada sale a servicios remotos sin habilitación explícita: en la config del proyecto (por ejemplo `review.publish_command`, que además se aprueba por máquina), o en la base de la memoria para los embeddings remotos (`exo mem reindex --allow-remote`, ADR-0009), porque la memoria es una por usuario.
12. Todo nombre visible del motor sale de `src/exo/_meta.py`.

## Código

- Python ≥ 3.10, tipado, `pathlib`, compatible con Windows, macOS y Linux. Nada de APIs de 3.11+ (por ejemplo `tomllib`) sin alternativa para 3.10.
- Funciones chicas y puras donde se pueda; efectos (disco, red, procesos) en los bordes.
- Mensajes de error accionables: qué pasó, por qué, qué hacer.

## Tests

- Primero el test, después el código. Cada bug corregido trae su test.
- Golden tests para adaptadores; regenerarlos solo con `pytest --update-golden` y revisando el diff.
- Nada de red ni de agentes reales en la suite normal; esos tests llevan `@pytest.mark.agent_e2e` y se excluyen por defecto.
- Fixtures siempre sintéticos: nunca secretos, PII ni datos reales (usar CUIT/DNI de prueba generados).
- Cobertura mínima de `src/exo`: 80 % en F0, 85 % desde F1.

## Comandos

```bash
pip install -e ".[dev]"     # entorno de desarrollo
pytest                      # suite con cobertura y umbral
pytest --no-cov <archivo>   # un archivo suelto, sin umbral
ruff check .                # lint
exo validate                # contenido de content/ (desde F1)
exo p0                      # gate de controles P0 (desde F5)
```

## Contenido (`content/`)

- Skills con el frontmatter del estándar Agent Skills (`name`, `description`) y lo propio en `metadata` con prefijo `exo-`.
- `SKILL.md` de hasta 500 líneas; detalle en `references/`.
- `description` con disparadores explícitos en inglés (ADR-0011: todo lo que se instala en los proyectos va solo en inglés).
- No copiar texto de skills de terceros sin licencia compatible y atribución.

## Git

- Conventional Commits; un commit por unidad de trabajo revisable.
- Rama por fase: `feat/F<n>-<slug>`. Nunca push directo a `main` ni `--force`.
- Al cerrar una fase: correr cada criterio de aceptación con el comando exacto y registrar el resultado en `docs/plan/PROGRESO.md`.
- La rama de la fase llega a `main` solo por un PR, que el dueño abre y mergea en GitHub con la CI en verde (D-51). Nunca un merge local a `main` ni un push a `main`.
