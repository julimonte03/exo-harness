# F3 — Memoria v2 (engram híbrido)

## Objetivo

Portar engram tal como lo describe el reporte (API de 15 tools, `topic_key`, sesiones, proyectos, guard S1, export redactado) sobre una interfaz con backends intercambiables, agregar búsqueda semántica y **medir** si la búsqueda híbrida realmente recupera mejor que la léxica para este uso. La decisión del backend por defecto sale de ese experimento, no de una preferencia.

## Depende de

F1 cerrada. Decisiones D-07 y D-08. Puede correr en paralelo con F2 y F4.

## Alcance

Entra: store léxico, guard S1, sesiones y proyectos, export/import, interfaz de backends, backend híbrido con sqlite-vec, backend Qdrant en servidor, proveedores de embeddings, `reindex`, experimento con dataset y reporte, tools MCP de memoria, CLI `arnes mem`, skill `memory-protocol`, hooks de sesión para Claude Code y Copilot.

No entra: memoria compartida de equipo en producción (D-20).

## Diseño

### Modelo y fuente de verdad

SQLite en modo WAL, en `~/.arnes/memory.db` (override con `ARNES_MEMORY_DB`; en Windows bajo el directorio de datos del usuario). Tablas: `observations` (id, tipo, título, contenido, `topic_key`, scope `project`/`personal`, proyecto, timestamps, hash de contenido), `sessions`, `projects`, `meta` (versión de esquema, modelo y dimensión de embeddings). El proyecto se detecta desde `git remote origin` normalizado, como en el reporte. Upsert por `(proyecto, topic_key)`. **Todos los índices son derivados**: se pueden borrar y reconstruir con `arnes mem reindex` sin perder nada.

### Guard S1

Corre antes de guardar y antes de calcular cualquier embedding. Detectores (del §5.5 del reporte): asignaciones de credenciales por palabra clave, tokens con prefijos conocidos, CUIT/CUIL con dígito verificador, DNI con contexto, tarjetas con Luhn, biometría y scoring. Política: **rechazar al guardar** (`SecretDetectedError`) y **redactar al exportar** (`[REDACTED:<clase>]`). Detectores organizados por perfil (`legacy-profile` por defecto, D-12). El mismo escáner lo reutiliza el `pre-commit` de F5.

### Interfaz de store

```python
class MemoryStore(Protocol):
    def save(self, obs: Observation) -> SaveResult: ...           # upsert por topic_key; incluye "similares" si hay índice semántico
    def search(self, q: Query) -> list[Hit]: ...                    # modo lexical | semantic | hybrid; devuelve previews
    def get(self, obs_id: int) -> Observation: ...
    def delete(self, obs_id: int) -> None: ...
    def list(self, filters: Filters) -> list[Observation]: ...
    def context(self, project: str, limit: int) -> str: ...
    # sesiones, proyectos, stats, export(redact=True), import_
```

Recuperación en dos pasos, como en el reporte: `mem_search` devuelve previews truncados y `mem_get` el contenido completo.

### Backends

| Backend | Qué es | Dependencias | Uso |
|---|---|---|---|
| `lexical` | FTS5 con tabla de contenido externo y triggers | Ninguna | Siempre disponible. Si el Python de la máquina no trae FTS5, cae a búsqueda `LIKE` y `doctor` avisa |
| `hybrid-sqlite` | FTS5 + tabla virtual de sqlite-vec en el mismo archivo | Extra `[vector]` | Candidato a default: un solo archivo, sin procesos extra, WAL permite servidor MCP y CLI a la vez |
| `qdrant` | Vectores en un servidor Qdrant (Docker); SQLite sigue siendo la fuente de verdad | Extra `[qdrant]` + servidor | Experimento de memoria de equipo. Payload mínimo (id, proyecto, tipo, scope), **sin el contenido**, para reducir superficie de fuga. Incluir `tools/qdrant/docker-compose.yml` |

El modo local sin servidor del cliente de Qdrant se usa **solo en tests**, porque toma un lock de proceso único sobre la carpeta (incompatible con varias sesiones de agente abiertas).

Chequeo de doctor importante: algunos Python (por ejemplo builds de sistema en macOS) deshabilitan la carga de extensiones de SQLite, que sqlite-vec necesita. Si pasa, `auto` cae a `lexical` y doctor explica cómo usar un Python que lo permita.

### Fusión

Reciprocal Rank Fusion con k = 60 entre el ranking léxico y el semántico, pesos configurables, filtros por proyecto, scope y tipo aplicados **antes** de rankear. Opcional: refuerzo por recencia acotado.

### Proveedores de embeddings

```python
class EmbeddingProvider(Protocol):
    model_id: str
    dim: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

Proveedores: `none`, `static` (model2vec, muy liviano), `onnx` (FastEmbed en CPU), `ollama` (HTTP a localhost) y `openai-compatible` (remoto, **deshabilitado** salvo `allow_remote: true`, con aviso de la matriz DPA). El modelo y la dimensión se guardan en `meta`; si cambian, el motor exige `reindex`. Requisito para los candidatos: multilingüe.

### Detección de duplicados y contradicciones (extensión)

Con índice semántico disponible, `save` devuelve las observaciones más parecidas del mismo proyecto por encima de un umbral, para que la skill `memory-protocol` decida si actualizar en lugar de duplicar o si hay una contradicción que preguntar al humano.

### Hooks de sesión

Para agentes con hooks (Claude Code, Copilot): al inicio de sesión, inyectar `arnes mem context --format hook` (contexto reciente del proyecto); antes de compactar o al terminar, recordar `mem_session_summary`. Para el resto, la regla equivalente vive en `AGENTS.base.md` y en la skill `memory-protocol` (ex `engram-protocol`): guardar decisiones, bugs resueltos y descubrimientos de forma proactiva, buscar antes de resolver de nuevo, cerrar la sesión con resumen.

## El experimento

**Dataset** en `tests/memory_eval/`, todo **sintético** (nunca datos reales):

- 80 memorias: decisiones, bugs resueltos, gotchas, convenciones; mezcla de español e inglés; con identificadores técnicos (`PROJ-1234`, nombres de clases y endpoints).
- 50 consultas etiquetadas: 15 exactas (por identificador), 20 paráfrasis o sinónimos, 10 cruzadas de idioma (consulta en español, memoria en inglés o al revés), 5 sin respuesta correcta.

**Métricas:** Recall@5, MRR@10, nDCG@10, tasa de falsos positivos en las consultas sin respuesta (con umbral de score), latencia p50/p95 sobre 5 000 memorias, tamaño instalado y tiempo de arranque en frío.

**Comparación:** `lexical` vs `hybrid-sqlite` con al menos dos modelos vs `qdrant`.

**Regla de decisión propuesta** (ajustable antes de correr, nunca después): el híbrido pasa a ser default si mejora el Recall@5 global en al menos 10 puntos, no empeora las consultas exactas en más de 2 puntos y mantiene p95 por debajo de 150 ms. El resultado se publica en `docs/evals/memory-<fecha>.md` y se registra en un ADR.

## Tareas (en orden)

1. Esquema SQLite, migraciones y store `lexical` + tests.
2. Guard S1 por perfiles + dataset dorado de positivos y negativos sintéticos.
3. Sesiones, proyectos (detección, merge, consolidate), stats, export/import con redacción.
4. CLI `arnes mem {save,search,list,get,context,delete,session …,projects …,stats,export,import,reindex}` y las 15 tools MCP.
5. Interfaz de backends, indexador derivado, `reindex`.
6. Proveedores de embeddings (con import diferido) + `hybrid-sqlite` con RRF.
7. Backend `qdrant` + docker-compose + tests con modo local.
8. Dataset del experimento, comando de desarrollo `arnes mem eval`, reporte y ADR.
9. Skill `memory-protocol` y hooks de sesión en los adaptadores de Claude Code y Copilot.
10. Chequeos de doctor de memoria (FTS5, carga de extensiones, modelo descargado, coherencia de `meta`).

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Guard sin fugas | 100 % de los positivos del dataset dorado rechazados al guardar, 0 falsos positivos en los negativos, export redactado |
| 2 | Funciona sin extras | Sin `[vector]` instalado, `memory.backend=auto` usa `lexical` y toda la suite de memoria pasa |
| 3 | Índices reconstruibles | Con `[vector]`, `arnes mem reindex` reconstruye desde SQLite y una batería de búsquedas devuelve los mismos resultados antes y después |
| 4 | Concurrencia | Test con dos procesos (servidor MCP y CLI) escribiendo y leyendo a la vez sin errores de lock en `hybrid-sqlite` |
| 5 | Experimento cerrado | `docs/evals/memory-<fecha>.md` con la tabla de métricas y ADR con la decisión del default |
| 6 | Rendimiento | p95 de búsqueda menor a 150 ms con 5 000 memorias en el backend elegido |
| 7 | Nada sale sin permiso | Con `allow_remote: false`, configurar un proveedor remoto falla con mensaje claro |
| 8 | Paridad de API | Las 15 tools MCP de memoria responden con los nombres del §5.3 del reporte |

## Referencias al reporte

§4.6 invariante 8, §5.3 (tools de memoria), §5.5 (engram y guard S1), §5.6 (convención para SDD), §7.4 (S1 como control en código), §7.5 (matriz DPA).
