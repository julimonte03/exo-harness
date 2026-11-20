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
- **Estado:** Decidida (ADR-0012), 2026-11-13: agnóstico. Sin integración con ningún tracker; cada proyecto define el patrón de su ID de ticket (o ninguno) y el motor solo lo valida y lo usa en cambios, ramas y commits.

### D-10 — Idiomas
- **Default:** chat en el idioma de la persona (español), artefactos SDD en inglés (regla del reporte §6.6), cuerpo de las skills en español con disparadores bilingües en la `description`.
- **Alternativa:** todo en español, o skills en inglés.
- **Estado:** Decidida (ADR-0011), 2026-11-13: inglés, y solo inglés, para todo lo que va a los proyectos (reglas, skills con disparadores en inglés, subagentes, plantillas y artefactos SDD) y para los mensajes del CLI. Los docs de este repo siguen en español. El agente responde en el idioma de la persona.

### D-11 — Specs vivas por capacidad
- **Default:** sí. `specs/capabilities/<capacidad>/spec.md` es la fuente de verdad; cada cambio escribe un delta (`ADDED`/`MODIFIED`/`REMOVED` por ID de requisito) y `sdd-archive` lo integra. Es lo que permite que la ingeniería inversa de F6 se conecte con el ciclo.
- **Estado:** Decidida, 2026-11-13: sí, el default. El formato del delta y de la spec de capacidad está en ADR-0013.

### D-13 — Alcance de skills antes de F7
- **Default:** 34 skills del reporte + 5 nuevas de ingeniería inversa hasta M3; las otras 65 en F7 por prioridad. Detalle en `99-TRAZABILIDAD.md`.
- **Estado:** Decidida, 2026-11-13: el default (las del ciclo SDD en F4, gobierno en F5, ingeniería inversa en F6 y las de cada stack en F7).

## Bloquean F5

### D-12 — Contenido específico de la organización de origen
- **Contexto:** el reporte tiene piezas propias de la organización de origen: un estilo ejecutivo propio, detectores de CUIT/CUIL/DNI, una matriz DPA propia, SonarQube/Fortify, Kibana, Xray y su plataforma interna de CI.
- **Default:** generalizar como **perfiles de organización**: `dpa_profile: legacy-profile` (incluye los detectores argentinos y la matriz del reporte), estilo visual con tokens de marca configurables, herramientas corporativas como integraciones opcionales que degradan.
- **Estado:** Decidida por el dueño (ADR-0014), 2026-11-15: nada atado a bancos ni a un país. Los secretos siempre se protegen. Los datos personales se protegen con detectores genéricos (tarjetas e IBAN por defecto); los documentos de cada país, el email y el teléfono son opcionales. La matriz de niveles por destino es definición propia y sale el perfil `legacy-profile`. La memoria sigue sin perfiles ni detectores (D-24, ADR-0009). El estilo visual y las herramientas corporativas quedan para F7, como integraciones opcionales.
- **F7** (ADR-0016), 2026-11-17:
  - **Estilo ejecutivo:** las skills de diseño y producto usan un estilo neutro por defecto. Un `.exo/brand.json` opcional (colores, tipografía, logo, tono) lo reemplaza; su forma está en el contrato `executive-style.md` del pack `design`.
  - **Herramientas corporativas:** SonarQube, Fortify y Kibana son pasos opcionales que se usan si el proyecto los tiene. Sin ellos, las skills degradan a herramientas abiertas (la auditoría del gestor de paquetes, OSV, dependency-check, los logs que haya).

### D-21 — Git hooks por defecto
- **Default:** sí, instalados con `core.hooksPath=.arnes/githooks`. Si el proyecto ya usa husky o el framework pre-commit, el motor se integra con ese mecanismo en vez de reemplazarlo.
- **Estado:** Decidida por el dueño (ADR-0014), 2026-11-15: el default.
  - Con husky, el motor se suma a husky.
  - Con el framework pre-commit, imprime el bloque a agregar (stdlib no edita su YAML sin riesgo) y `exo doctor` lo verifica.
  - Se apagan con `governance.githooks: false`, y `exo uninstall` revierte `core.hooksPath`.

## Bloquean F6

### D-14 — Parsers para ingeniería inversa
- **Default:** heurísticas con stdlib en la v1 (`ast` para Python, expresiones regulares para imports de JS/TS y Java, nivel de archivo para el resto). tree-sitter como extra opcional más adelante.
- **Estado:** Decidida (ADR-0015), 2026-11-16: el default.

### D-19 — Ejecutar build/tests durante la ingeniería inversa
- **Default:** solo con confirmación explícita del humano, para medir la línea base de calidad. Sin confirmación, se infiere desde archivos de test y configuración.
- **Estado:** Decidida (ADR-0015), 2026-11-16: en F6 el pipeline no corre build ni tests. Medir la línea base queda como item del backlog de adopción, con confirmación.

## No bloquean (se pueden decidir más tarde)

### D-17 — Overlays de persona
- **Default:** se posponen a F8 como opcionales.
- **Estado:** Decidida por el dueño, 2026-11-19: entran en F8. El diseño está en ADR-0018 (propuesta) y se confirma antes del código.

### D-18 — Licencia de las skills de origen `ecc`
- **Contexto:** 14 skills del reporte dicen venir de un catálogo externo adaptado.
- **Default:** escribirlas desde cero en F7 a partir de su rol, salvo que se confirme una licencia compatible.
- **Estado:** Decidida (ADR-0016), 2026-11-17: el default. Igual no hay cuerpos originales: el reporte solo trae la descripción, el tamaño y las referencias de cada skill.

### D-20 — Memoria compartida de equipo
- **Default:** no en la v1. El experimento con Qdrant en servidor (F3) deja la evidencia para decidir. Compartir sigue siendo posible con `mem export`/`mem import` redactado, como en el reporte.
- **Estado:** Decidida (ADR-0009), 2026-11-13: no en la v1. La memoria es por máquina de usuario y F3 no incluye Qdrant. Compartir sigue siendo posible con `mem export`/`mem import`, sin redactar (D-24).

### D-22 — Distribución pública
- **Default:** repo privado hasta M2; después instaladores por `curl`/`irm` y `uvx`. PyPI y marketplaces de agentes, opcionales en F8.
- **Estado:** Decidida por el dueño (ADR-0017), 2026-11-19:
  - repo **público** en GitHub, `https://github.com/julimonte03/exo-harness`;
  - `main` y las ramas de fase se subieron al empezar F8; los tags y los releases, al cierre;
  - instaladores por `curl`/`irm` y `uvx` desde ese repo;
  - PyPI entra en F8; los marketplaces de agentes, no.

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

### D-26 — Ticket en el nombre del cambio
- **Contexto:** ADR-0012 permite patrones como `#123` o `AB#123`. El `#` complica los nombres de carpeta y de rama: en un shell, al principio de una palabra es un comentario.
- **Opciones:** (a) normalizar el ID en el nombre; (b) incluirlo solo si ya es seguro; (c) no incluirlo nunca.
- **Estado:** Decidida por el dueño, 2026-11-14: (a). Todo carácter que no sea letra, dígito o guion pasa a guion, y se recortan los guiones de los extremos: `AB#123` → `AB-123-add-login` y `#123` → `123-add-login`. La épica se normaliza igual. El ID exacto queda en `ticket_key` (y `epic_key`) del AI Usage Record y, desde F5, en el commit.

### D-27 — Artefactos obligatorios por tier
- **Contexto:** el reporte tiene dos inconsistencias. En §6.3 el Tier 1 no tiene fase de spec, pero las specs vivas (D-11) necesitan el delta. En §6.4 el Tier 2 exige `test-spec.md`, pero no tiene la fase de tasks que lo escribe.
- **Opciones para el Tier 1:** (a) delta siempre; (b) delta solo si el cambio altera comportamiento.
- **Estado:** Decidida por el dueño, 2026-11-14:
  - **Tier 1:** (b). Exige `proposal.md`; `spec.md` es opcional y, si falta, `exo check` avisa que el cambio no debe alterar comportamiento.
  - **Tier 2:** exige `proposal.md`, `spec.md` y `test-spec.md`. Este último lo escribe `sdd-spec` con `test-strategy`.
  - **Tier 3 y 4:** suman `design.md` y `tasks.md`; `test-spec.md` lo escribe `sdd-tasks`.
  - **Todos los tiers:** exigen `ai-usage-record.json` válido. Sin `fitness-assessment.json`, el tier es 4.

### D-28 — Meta-comandos del orquestador
- **Contexto:** F4 pide los meta-comandos `/sdd-new`, `/sdd-continue`, `/sdd-ff` y `/sdd-status`. El repo usa skills como comandos y no genera prompt files ni `.claude/commands/` (`03-MATRIZ-AGENTES.md`).
- **Opciones:** (a) un archivo de comando por agente; (b) skills finas `sdd-continue` y `sdd-ff`, que cargan el orquestador; (c) argumentos del orquestador (`/sdd-orchestrator continue`).
- **Estado:** Decidida, 2026-11-14: (b). Sigue la política de la matriz de agentes. `/sdd-new` y `/sdd-status` ya salen de sus skills.

### D-29 — Ticket en el mensaje de commit
- **Contexto:** el reporte pone el ticket como prefijo del asunto (`PROJ-123 feat(auth): …`). Eso rompe el formato de Conventional Commits, y un ID tipo `#123` al principio de una línea es un comentario para git. La skill `work-unit-commits` de F4 ya usa un footer.
- **Opciones:** (a) footer `Refs: <ID>`; (b) prefijo en el asunto; (c) cualquiera de los dos.
- **Estado:** Decidida por el dueño (ADR-0014), 2026-11-15: (a). El hook `commit-msg` exige que un `Refs:` cumpla el patrón del proyecto. Sin `Refs:` acepta el commit, porque la persona puede haber confirmado que no hay ticket.

### D-30 — CI y comentarios de gates en el PR
- **Contexto:** el plan de F5 traía plantillas de GitHub Actions y GitLab y publicaba con `gh` y `glab`. ADR-0008 señala Azure DevOps.
- **Opciones:** (a) solo Azure DevOps; (b) Azure DevOps y GitHub; (c) agnóstico.
- **Estado:** Decidida por el dueño (ADR-0014), 2026-11-15: (c).
  - **CI:** `exo check --base <destino>` es el único paso que una CI tiene que correr. Los contratos traen ejemplos para Azure Pipelines, GitHub Actions y GitLab CI.
  - **Host:** el motor detecta el host desde el remoto y lo guarda en la config. El comportamiento es el mismo en cualquiera.
  - **Publicación:** `exo gate publish` le pasa cada texto a un comando que configura el proyecto, o lo imprime.

### D-31 — Hooks de agente
- **Contexto:** F5 pedía hooks de agente como segunda línea (bloquear `git push --force` y borrados antes de ejecutarlos). La política de la organización bloquea los hooks de proyecto en Claude Code (`allowManagedHooksOnly`, D-25).
- **Opciones:** (a) escribirlos igual, para otras organizaciones; (b) no escribirlos.
- **Estado:** Decidida, 2026-11-15: (b), con el mismo criterio que D-25. Los git hooks y `exo check` en la CI cubren lo mismo para cualquier agente.

### D-32 — Qué verifica `exo p0`
- **Contexto:** el `_verify_p0.py` del reporte era la regresión de S1 (guarda de memoria) y S2 (validación de entradas). S1 ya no existe (ADR-0009).
- **Estado:** Decidida, 2026-11-15. `exo p0` corre tres regresiones e imprime `P0 GATE: PASSED (3/3)`:
  1. el escáner de secretos y datos sobre un dataset sintético empaquetado;
  2. S2 con entradas maliciosas;
  3. los git hooks instalados y activos en el proyecto (o husky).

### D-33 — El pack `discovery` y la instalación por defecto
- **Contexto:** `discovery` sirve para adoptar un proyecto que ya existe; en un repo vacío no tiene sentido.
- **Opciones:** (a) por defecto siempre; (b) solo si el repo ya tiene código; (c) nunca por defecto.
- **Estado:** Decidida por el dueño (ADR-0015), 2026-11-16: (b). El wizard lo **ofrece** cuando detecta código, sin instalarlo solo; se suma con `--packs`.

### D-34 — ¿Se commitea `.exo/discovery/`?
- **Contexto:** la ingeniería inversa deja inventario, grafo, plan, unidades, muestra y auditoría.
- **Opciones:** (a) se commitea; (b) va a `.gitignore`.
- **Estado:** Decidida por el dueño (ADR-0015), 2026-11-16: (a). Es conocimiento del proyecto, y otra persona u otra máquina retoma desde ahí. Por eso el estado no tiene datos que varíen entre corridas ni un archivo compartido que se pise.

### D-35 — Prueba de escala de la adopción
- **Contexto:** el criterio 8 de F6 pide adoptar un repo real de 20 a 50 mil líneas y medir una cobertura de módulos ≥ 80 %.
- **Opciones:** (a) un repo público que se descarga; (b) uno que ya tenga el dueño; (c) diferirla.
- **Estado:** Decidida por el dueño, 2026-11-16: (c), a F8, junto con el resto de las pruebas de escala.
- **F8** (del dueño), 2026-11-19: sobre el propio exo, que tiene 17 mil líneas de código más 13 mil de tests. Se adopta una copia, con los datos aislados.

### D-36 — `exo uninstall` y lo que produjo la ingeniería inversa
- **Contexto:** `uninstall` borra toda la carpeta del motor. `discovery/` y `context.md` son conocimiento del proyecto, no instalación del motor.
- **Estado:** Decidida (ADR-0015), 2026-11-16: `uninstall` los conserva y lo informa.

### D-37 — Memoria en la ingeniería inversa
- **Contexto:** el plan de F6 guardaba un resumen por unidad en memoria (`discovery/<unidad>`). La memoria es por usuario (ADR-0009) y el estado ya se commitea (D-34).
- **Estado:** Decidida (ADR-0015), 2026-11-16: las skills de discovery no escriben memoria. Es un desvío del plan.

### D-38 — Stacks del equipo
- **Contexto:** F7 pide que el equipo diga qué stacks usa de verdad, para ordenar los packs de stack (prioridad 2).
- **Estado:** Decidida por el dueño, 2026-11-17: los tres. El orden es `java`, `python` y `frontend`.

### D-39 — Las skills de Jira
- **Contexto:** el reporte trae `jira-card-creator` y `jira-refinement-assistant`, atadas a Jira y a Xray. ADR-0012 dejó el motor sin integración con ningún tracker, y la clave `tracker.type` ya no existe.
- **Opciones:** (a) generalizarlas; (b) sacarlas de F7; (c) dejarlas atadas a Jira en un pack aparte.
- **Estado:** Decidida por el dueño (ADR-0016), 2026-11-17: (a).
  - `jira-card-creator` pasa a `work-item-creator` y `jira-refinement-assistant` pasa a `refinement-assistant`.
  - El formato del ID sale de `tickets.pattern`.
  - Jira, Azure Boards y GitHub Issues quedan como ejemplos en `references/`.

### D-40 — La skill `review`
- **Contexto:** la skill `review` de F5 (revisión del diff antes de commitear) se instala en `.claude/skills/review/` y choca con el comando integrado `/review` de Claude Code.
- **Estado:** Decidida por el dueño (ADR-0016), 2026-11-17: pasa a `pre-commit-review`.

### D-41 — Cómo se corren los evals de las skills
- **Contexto:** F7 pide tres prompts de evaluación por skill de prioridad 1 y 2 (unas 38 skills, 114 prompts), revisados con Claude Code.
- **Opciones:** (a) un runner que corre todos con Claude Code real; (b) una muestra; (c) solo escribirlos, y que los corra el dueño.
- **Estado:** Decidida por el dueño (ADR-0016), 2026-11-17: (a). El runner es un test `agent_e2e`, fuera de la suite normal, con los datos aislados. Los resultados se revisan y se anotan en PROGRESO.

### D-42 — Nombres de las skills instaladas
- **Contexto:** ADR-0011 pide inglés para todo lo que se instala. El reporte tiene `comite-excelencia`.
- **Estado:** Decidida (ADR-0016), 2026-11-17:
  - `comite-excelencia` pasa a `excellence-committee`;
  - `kibana-logs` conserva el nombre y cubre también OpenSearch Dashboards y Elastic.

### D-43 — Gates de accesibilidad y de SPDD
- **Contexto:** el plan pide un gate de accesibilidad en verify (§6.7) y un gate humano del Canvas SPDD (§6.8). Ninguno de los dos aplica a todo change de un tier: dependen de que haya UI o canvas.
- **Estado:** Decidida (ADR-0016), 2026-11-17: son **gates condicionales**, fuera de `governance.gates`.
  - `accessibility_review` lo escribe `accessibility-audit` en verify cuando el change toca UI. Un hallazgo Critical (impide completar la tarea) o High bloquea `ready`, salvo que se descarte con su motivo.
  - `prompt_spec_review` lo escribe `prompt-spec-review` cuando el change tiene `canvas.md`, y `exo check` lo exige en ese caso.
  - `exo check` revisa todo gate presente, aunque el tier no lo pida.

### D-44 — Escaneo de dependencias en Python
- **Contexto:** `security-scan-jkp` cubre Java, Kotlin y Python, pero vive en el pack `java`. Un proyecto solo Python no lo recibe por la sugerencia de stack.
- **Estado:** Decidida (ADR-0016), 2026-11-17: queda en `java`, como dice el plan. Su fila de degradación en el mapa trae el criterio inline para Python (pip-audit u OSV-Scanner), así un proyecto solo Python escanea igual.

### D-45 — CI del motor
- **Contexto:** ADR-0008 ponía la CI en Azure Pipelines, pero el repo quedó en GitHub (D-22), que no corre `azure-pipelines.yml`.
- **Estado:** Decidida por el dueño (ADR-0017), 2026-11-19: GitHub Actions, con Windows, macOS y Linux y Python 3.10 a 3.13. `azure-pipelines.yml` queda como ejemplo para quien use Azure.

### D-46 — Limpieza antes del primer push
- **Contexto:** el repo iba a ser público. Los commits tenían el email de trabajo del dueño, y `docs/referencia/` era la transcripción del sistema original, con contenido propio de la organización de origen.
- **Estado:** Decidida por el dueño, 2026-11-19. Antes del primer push se reescribió toda la historia con `git filter-repo`:
  - el autor de todos los commits pasó al noreply de GitHub del dueño;
  - `docs/referencia/` salió de toda la historia (queda en local, ignorada por git);
  - todo lo que nombraba a la organización de origen o a sus herramientas pasó a un término genérico, en todas las versiones y en los mensajes.

  El pedido del dueño fue dejarlo "limpio de ese contexto, así es agnóstico".

### D-47 — Copilot para la v1.0
- **Contexto:** el criterio 1 de la v1.0 pide Claude Code y Copilot, y en esta máquina no había Copilot CLI.
- **Estado:** Decidida por el dueño, 2026-11-19: se instala Copilot CLI acá y el dueño inicia sesión. Con él se corren los escenarios de la v1.0 y los checklists de Copilot pendientes desde F2.

### D-48 — Idioma de la documentación de usuario
- **Contexto:** el repo es público. Los docs del plan están en español, y lo que se instala, en inglés (ADR-0011).
- **Estado:** Decidida (ADR-0017), 2026-11-19: los docs para quien usa el motor van en inglés, como lo instalado: README, QUICK-START, las guías, troubleshooting, CONTRIBUTING y CHANGELOG. El plan, los ADRs y los docstrings siguen en español.
