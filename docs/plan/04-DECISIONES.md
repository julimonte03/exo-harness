# 04 — Decisiones abiertas

Cada decisión tiene una **opción recomendada (default)**. Si no la cambiás, Claude Code usa el default. Cuando una decisión se toma, se registra como ADR en `docs/adr/` y se marca acá como **Decidida**.

Estado: `Abierta` | `Decidida (ADR-xxxx)`.

## Bloquean F0

### D-01 — Nombre del motor
- **Opciones:** mantener `arnes` · otro nombre.
- **Default:** `arnes` como nombre de trabajo (CLI `arnes`, carpeta `.arnes/`, variables `ARNES_`). Todo nombre visible sale de `_meta.py`, así que cambiarlo después cuesta poco.
- **Nota:** evitar `.harness/`, que ya usa la plataforma Harness para sus pipelines.
- **Estado:** Decidida (ADR-0001), 2026-10-29: el motor se llama **`exo`** (CLI `exo`, `.exo/`, `EXO_`, bloques `exo`, metadata `exo-`); la distribución se llama `exo-harness`. En el resto del plan, `arnes` se lee como `exo`.

### D-02 — Lenguaje del runtime
- **Opciones:** (a) Python ≥ 3.10 con núcleo stdlib y extras opcionales · (b) Go con binario único.
- **Default:** (a). Da continuidad con el reporte (runtime Python, 729 tests diseñados, invariantes pensadas para stdlib), facilita el ecosistema de embeddings locales y es un lenguaje en el que Claude Code itera rápido. El costo es que la máquina necesita Python: el instalador lo resuelve usando `uv` si está, o un venv propio.
- **Cuándo elegir (b):** si la instalación sin ningún prerequisito es crítica para usuarios no técnicos.
- **Estado:** Decidida (ADR-0002), 2026-10-29: opción (a).

### D-03 — Relación con gentle-ai y Engram (upstream)
- **Contexto:** el reporte dice que el arnés original es una réplica en Python de `gentleman-programming/gentle-ai` (Go). gentle-ai ya es agnóstico: detecta los agentes instalados, instala skills, configura MCP, inyecta un orquestador SDD y usa Engram como memoria, con soporte para más de diez agentes. Engram usa SQLite + FTS5 (búsqueda léxica).
- **Opciones:**
  - (a) **Construir propio** en Python siguiendo el reporte y usar gentle-ai solo como referencia de la matriz de agentes y rutas.
  - (b) **Fork o extensión de gentle-ai** (Go) sumando la capa de gobierno del sistema de referencia, ingeniería inversa y memoria vectorial.
  - (c) **Híbrido:** usar el binario de Engram como memoria y construir el resto.
- **Default:** (a). La capa de adaptadores es una parte chica del trabajo total; el valor diferencial está en el gobierno (fitness, gates, AI Usage Record, DPA, jueces), la ingeniería inversa y la memoria híbrida, que no existen upstream o existen distinto. Mantener un fork en otro lenguaje con un upstream muy activo genera divergencia constante. (c) no sirve porque la memoria vectorial es justamente una de las mejoras.
- **Antes de reusar cualquier texto o código upstream:** verificar licencia (F0, tarea 0.5).
- **Estado:** Decidida (ADR-0004), 2026-10-29: opción (a). Licencias verificadas en el ADR.

### D-15 — Sistema operativo de esta computadora y del equipo
- **Opciones:** Windows · macOS · Linux · mixto.
- **Default:** mixto (los tres en CI). Si esta computadora es Windows, `install.ps1` pasa a prioridad 1 en F2 y las pruebas manuales se hacen ahí primero.
- **Estado:** Decidida (ADR-0002), 2026-10-29: mixto. Esta computadora es Windows 11, así que `install.ps1` es prioridad 1 en F2 y las pruebas manuales se hacen primero en Windows.

## Bloquean F2

### D-04 — Agentes de la v1
- **Default:** Tier 1 = Claude Code y GitHub Copilot (VS Code y CLI). Tier 2 = Cursor, Codex CLI, Gemini CLI, Windsurf/Devin. Tier 3 = genérico.
- **Hallazgos de F0** (`docs/agent-matrix.md`, 2026-10-29) a considerar al decidir:
  - Windsurf ahora es Devin Desktop: Cascade se eliminó y el agente es Devin Local/CLI. El adaptador pasa a llamarse `devin`.
  - Gemini CLI fue reemplazado por Antigravity CLI para el tier gratuito, que es candidato a Tier 2.
  - VS Code tiene dos harness: Copilot (default, mismo runtime que Copilot CLI) y Local (legacy).
- **Estado:** Decidida (ADR-0006), 2026-10-30: base agnóstica para cualquier agente que lea `AGENTS.md`, con detección al instalar. Adaptadores específicos solo para Claude Code y GitHub Copilot (VS Code y CLI). Cursor, Codex, Gemini y Devin se detectan y quedan cubiertos por la base; sus adaptadores propios salen de la v1.

### D-05 — Dónde viven las skills de un proyecto
- **Opciones:** (a) copia en el repo, versionada · (b) instalación global por usuario.
- **Default:** (a). Todo el equipo usa la misma versión, el lock la registra y la CI puede validarla. Global queda como opción (`--scope user`).
- **Estado:** Decidida (ADR-0007), 2026-10-30: opción (a), por proyecto, copiadas y versionadas en el repo.

### D-06 — Espejo `.claude/skills/`
- **Opciones:** (a) copia gestionada por el lock · (b) symlink/junction.
- **Default:** (a). Funciona igual en Windows y en todos los agentes; el lock evita que diverja. Symlinks quedan como opción en sistemas POSIX.
- **Estado:** Decidida (ADR-0007), 2026-10-30: copias gestionadas por el lock, solo las necesarias. Con Claude Code y/o Copilot alcanza `.claude/skills/`; con otros agentes se suma `.agents/skills/`.

### D-16 — Hosting de git y CI de los proyectos
- **Opciones:** GitHub · GitLab · Azure DevOps · Bitbucket.
- **Default:** GitHub para el repo del motor; plantillas de CI para GitHub Actions y GitLab CI en los proyectos; el resto vía `arnes check` en un script genérico.
- **Estado:** Decidida (ADR-0008), 2026-10-30: Azure DevOps (Azure Repos + Azure Pipelines con un pipeline propio). La CI del motor pasa a `azure-pipelines.yml`; los proyectos invocan `exo check` desde su pipeline.

## Bloquean F3

### D-07 — Backend de memoria por defecto
- **Opciones:** `lexical` (FTS5) · `hybrid-sqlite` (FTS5 + sqlite-vec) · `qdrant`.
- **Default provisorio:** `auto` = `hybrid-sqlite` si el extra `[vector]` está instalado, si no `lexical`. **El default definitivo lo decide el experimento de F3** con un ADR.
- **Por qué no Qdrant como default:** Qdrant es open source y se puede correr gratis con Docker, y su cliente Python tiene un modo local sin servidor. Pero ese modo local toma un lock de proceso único sobre la carpeta, y en este motor conviven el servidor MCP (uno por sesión de agente abierta) y el CLI. Por eso Qdrant entra como backend de servidor (Docker) para experimentar memoria de equipo, y el modo local solo para tests.
- **Actualización (ADR-0009), 2026-11-13:** Qdrant sale de F3, porque la memoria es por usuario. Quedan `lexical` y `hybrid-sqlite`.
- **Estado:** Decidida (ADR-0010), 2026-11-13: `hybrid-sqlite` por el experimento (Recall@5 80,0 contra 62,2 de la léxica; p95 67 ms con 5 000 memorias). `auto` usa la híbrida si la base tiene índice semántico y la léxica si no.

### D-08 — Embeddings
- **Default:** solo locales. Candidatos a comparar en el experimento: embeddings estáticos livianos (model2vec), ONNX en CPU (FastEmbed) y Ollama. Requisito: modelo **multilingüe** (las memorias van a mezclar español e inglés). Proveedores remotos solo con `allow_remote: true`.
- **Actualización (ADR-0009), 2026-11-13:** los modelos se bajan de Hugging Face solo con `exo mem model pull`. Ollama no está instalado en la máquina del experimento: su proveedor existe, pero queda fuera de la comparación.
- **Estado:** Decidida (ADR-0010), 2026-11-13: `onnx` (FastEmbed, `paraphrase-multilingual-MiniLM-L12-v2`) como primera opción de `local`, `static` (model2vec) como alternativa. Extra `[vector]` = sqlite-vec + FastEmbed.

## Bloquean F4

### D-09 — Tracker de tickets
- **Default:** configurable en el wizard (`jira`, `github`, `gitlab`, `linear`, `none`). El formato del `change-name` y del commit se adapta al tracker. Si es `none`, se usa Conventional Commits sin prefijo (regla del reporte cuando no hay ticket).
- **Estado:** Abierta.

### D-10 — Idiomas
- **Default:** chat en el idioma de la persona (español), artefactos SDD en inglés (regla del reporte §6.6), cuerpo de las skills en español con disparadores bilingües en la `description`.
- **Alternativa:** todo en español, o skills en inglés.
- **Estado:** Abierta.

### D-11 — Specs vivas por capacidad
- **Default:** sí. `specs/capabilities/<capacidad>/spec.md` es la fuente de verdad; cada cambio escribe un delta (`ADDED`/`MODIFIED`/`REMOVED` por ID de requisito) y `sdd-archive` lo integra. Es lo que permite que la ingeniería inversa de F6 se conecte con el ciclo.
- **Estado:** Abierta.

### D-13 — Alcance de skills antes de F7
- **Default:** 34 skills del reporte + 5 nuevas de ingeniería inversa hasta M3; las otras 65 en F7 por prioridad. Detalle en `99-TRAZABILIDAD.md`.
- **Estado:** Abierta.

## Bloquean F5

### D-12 — Contenido específico de la organización de origen
- **Contexto:** el reporte tiene piezas propias de la organización de origen: un estilo ejecutivo propio, detectores de CUIT/CUIL/DNI, una matriz DPA propia, SonarQube/Fortify, Kibana, Xray y su plataforma interna de CI.
- **Default:** generalizar como **perfiles de organización**: `dpa_profile: legacy-profile` (incluye los detectores argentinos y la matriz del reporte), estilo visual con tokens de marca configurables, herramientas corporativas como integraciones opcionales que degradan.
- **Estado:** Parcial (ADR-0009), 2026-11-13: la memoria no tiene perfiles ni detectores (D-24). El resto (estilo, matriz DPA, herramientas corporativas) sigue abierto para F5.

### D-21 — Git hooks por defecto
- **Default:** sí, instalados con `core.hooksPath=.arnes/githooks`. Si el proyecto ya usa husky o el framework pre-commit, el motor se integra con ese mecanismo en vez de reemplazarlo.
- **Estado:** Abierta.

## Bloquean F6

### D-14 — Parsers para ingeniería inversa
- **Default:** heurísticas con stdlib en la v1 (`ast` para Python, expresiones regulares para imports de JS/TS y Java, nivel de archivo para el resto). tree-sitter como extra opcional más adelante.
- **Estado:** Abierta.

### D-19 — Ejecutar build/tests durante la ingeniería inversa
- **Default:** solo con confirmación explícita del humano, para medir la línea base de calidad. Sin confirmación, se infiere desde archivos de test y configuración.
- **Estado:** Abierta.

## No bloquean (se pueden decidir más tarde)

### D-17 — Overlays de persona
- **Default:** se posponen a F8 como opcionales.

### D-18 — Licencia de las skills de origen `ecc`
- **Contexto:** 14 skills del reporte dicen venir de un catálogo externo adaptado.
- **Default:** escribirlas desde cero en F7 a partir de su rol, salvo que se confirme una licencia compatible.

### D-20 — Memoria compartida de equipo
- **Default:** no en la v1. El experimento con Qdrant en servidor (F3) deja la evidencia para decidir. Compartir sigue siendo posible con `mem export`/`mem import` redactado, como en el reporte.
- **Estado:** Decidida (ADR-0009), 2026-11-13: no en la v1. La memoria es por máquina de usuario y F3 no incluye Qdrant. Compartir sigue siendo posible con `mem export`/`mem import`, sin redactar (D-24).

### D-22 — Distribución pública
- **Default:** repo privado hasta M2; después instaladores por `curl`/`irm` y `uvx`. PyPI y marketplaces de agentes, opcionales en F8.

## Surgidas durante la construcción

### D-23 — Servidor MCP bloqueado por política de la organización
- **Contexto:** en la prueba empírica de F0 (`docs/spikes/agent-probe.md`), Claude Code respondió `MCP server blocked by enterprise policy` para un server MCP de proyecto. La organización solo permite servidores de una lista, mediante settings administrados. Si `exo mcp` no está en esa lista, el agente no carga las tools de skills, observabilidad, memoria ni discovery.
- **Opciones:**
  - (a) **Paridad CLI:** cada tool MCP tiene un subcomando equivalente (`exo … --json`); las skills usan MCP si está disponible y, si no, el CLI por shell, declarando la degradación. `exo doctor` detecta y explica el bloqueo.
  - (b) Pedir que la organización agregue `exo` a la lista permitida y depender solo de MCP.
  - (c) Las dos: (a) como base y (b) como gestión paralela.
- **Default:** (c). (a) no depende de terceros y suma poco costo, porque el plan ya prevé CLI para casi todo (`exo mem`, `exo change status`, `exo discover`). (b) mejora la experiencia donde se consiga.
- **Bloquea:** F1 (diseño de `mcp/tools/` con su par en el CLI) y F2 (chequeo de doctor y checklist manual).
- **Estado:** Decidida (ADR-0005), 2026-10-30: opción (a), con el CLI como interfaz principal. Las skills usan `exo … --json` por terminal y el servidor MCP queda opcional, apagado por defecto (`mcp.enabled: false`). Donde el plan (§2.10, fases) dice "tool MCP", se lee "subcomando del CLI, también expuesto por MCP si está habilitado".

### D-24 — Guard S1 en la memoria
- **Contexto:** el plan de F3 ponía un guard S1 que rechaza secretos y PII al guardar y los redacta al exportar, con perfiles de organización (D-12).
- **Opciones:** (a) guard con perfil `legacy-profile`; (b) guard solo de secretos, sin PII; (c) sin guard.
- **Estado:** Decidida (ADR-0009), 2026-11-13: (c). La memoria es por máquina de usuario, sin auth ni perfiles. La regla de `AGENTS.md` de no guardar secretos queda como pauta para el agente. Riesgo aceptado: un export comparte el contenido sin redactar.

### D-25 — Hooks de sesión para la memoria
- **Contexto:** la config administrada de esta máquina tiene `allowManagedHooksOnly: true`, que bloquea los hooks de proyecto en Claude Code. Además, Claude Code y Copilot esperan salidas distintas, y ninguno permite pedirle algo al agente con `PreCompact` o `SessionEnd`.
- **Opciones:** (a) hooks donde la política lo permita, más reglas, más aviso de `exo doctor`; (b) solo reglas.
- **Estado:** Decidida (ADR-0009), 2026-11-13: (b). La sección «Memoria» de `AGENTS.base.md` y la skill `memory-protocol` le dicen al agente cuándo correr `exo mem context`, `exo mem save` y `exo mem session summary`.
