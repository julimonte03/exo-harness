# ADR-0015 — Ingeniería inversa: estado en el repo, evidencia verificable y specs as-is

- **Estado:** Aceptada
- **Fecha:** 2026-11-16
- **Decisiones:** D-14, D-19 y D-33 a D-37 (`docs/plan/04-DECISIONES.md`)

## Contexto

F6 hace que exo entienda un proyecto que ya existe sin tocar su código (`docs/plan/fases/F6-ingenieria-inversa.md`). Las specs reconstruidas desde código suelen tener errores si salen de una sola pasada. Por eso el pipeline es determinista donde puede, exige evidencia y tiene una auditoría independiente.

Cuatro restricciones vienen de antes:
- **CLI primero (ADR-0005):** el bucle tiene que sobrevivir a la compactación de contexto, a cortes y a cambios de agente.
- **Specs vivas (ADR-0013):** fijan el formato de la capacidad y reservan lugar fuera de los bloques para un status y la procedencia.
- **Solo lectura:** la ingeniería inversa no modifica el código del proyecto analizado.
- **Commit con escáner:** todo lo que se commitea pasa por el escáner de secretos y datos personales del `pre-commit` (ADR-0014).

## Decisión

### Dónde vive el estado

Todo lo que produce el pipeline vive en `<carpeta del motor>/discovery/` y **se commitea** (D-34): es conocimiento del proyecto, y otra persona u otra máquina retoma desde ahí.

| Archivo | Etapa |
|---|---|
| `inventory.json` | R0, inventario |
| `structure.json`, `module-graph.mmd`, `hotspots.json`, `ownership.json` | R1, estructura |
| `plan.json` | R2, unidades de trabajo y estimación |
| `units/<id>.md`, `units/<id>.json` | R3: la extracción de cada unidad y los hashes de sus archivos al cerrarla |
| `capabilities/<capacidad>.json` | R4: los hashes de los archivos que citan los FR de la capacidad al sintetizarla, y cuántas veces se sintetizó (`rounds`) |
| `sample.json`, `audit.json`, `coverage.md` | R5, auditoría |
| `open-questions.md`, `debt.md`, `pending-approval.md`, `adoption-backlog.md` | R4 y R6 (`pending-approval.md`: lo que una corrida desatendida dejó sin aprobar) |

- **No hay un `state.json` compartido ni un estado "en curso".** El estado de cada unidad se deriva: está cerrada si su `units/<id>.json` existe, y stale si un hash cambió. Dos personas o dos ramas no se pisan, y una extracción cortada se rehace entera.
  - **`exo discover reopen`** borra el registro de una unidad, o el de las unidades de una capacidad por debajo del umbral, para extraerla otra vez. Esas unidades son las que tienen archivos citados por sus FR o, si no hay ninguna, las de su `Source:`.
  - **`exo discover skip <unidad> --reason`** saca del ciclo una unidad que no se puede cerrar. Su registro guarda la razón, que pasa por el escáner porque se commitea. La unidad cuenta como no cubierta, `reopen` la devuelve, y si sus archivos cambian, `status` y `update` lo informan.
  - **`exo discover synthesized <capacidad>`** valida la spec (preámbulo y sin errores) y registra los hashes de los archivos citados. Una capacidad es stale cuando cambia uno de esos archivos, y lo sigue siendo hasta que se vuelve a sintetizar, aunque sus unidades ya se hayan cerrado otra vez. Una spec con preámbulo que nunca se registró aparece como `unrecorded_capabilities`.
- **`exo discover status`** es de solo lectura. Muestra:
  - las etapas que corrieron, las unidades por estado y las salteadas con su razón;
  - las unidades cerradas que ninguna capacidad lista en su `Source:`;
  - las capacidades por status, las stale, las no registradas y sus `rounds`;
  - si hay cobertura, los FR de la muestra sin auditar y las capacidades marcadas;
  - los cambios fuera de las rutas permitidas.

  Es lo que lee `exo-adopt` para retomar.
- **Cada JSON lleva `"schema": 1`.** Un motor más viejo rechaza un esquema más nuevo, como con la config.
- **Nada que varíe entre corridas iguales:** ni el sha de HEAD, ni la versión del motor, ni fechas.

### Determinismo

- **La lista de archivos** sale de `git ls-files` (solo lo versionado; lo sin trackear, con un flag) y se excluyen:
  - la carpeta del motor, `specs_dir` y los archivos del lock;
  - lo vendorizado y lo generado;
  - los binarios y lo que pasa de 1 MB;
  - lo que diga `discovery.ignore`.

  Sin git, solo esas exclusiones y un aviso.
- **Los hashes** normalizan los fines de línea, así dan igual en Windows y en Linux.
- **La ventana de churn** se ancla en el último commit que toca código analizado, no en HEAD ni en "ahora". Commitear los resultados no los cambia.
- **Las unidades** se parten solo entre archivos. Sus IDs son estables, en minúscula, con un sufijo de hash ante colisiones o nombres reservados de Windows. `plan` no pisa un plan con unidades cerradas sin `--replan`, y `update` nunca replanifica.
- **Los parsers** son heurísticos con stdlib (D-14). El resultado de `ast` puede depender de la versión de Python; si no parsea, se cae al nivel de archivo.

### Evidencia

Cada afirmación de una unidad o de una spec recuperada lleva una de estas marcas:
- `[Code] path:line` o `[Code] path:start-end`: el archivo es de la unidad y la línea existe;
- `[Doc] path`;
- `[Inferred: high|medium|low]`.

`exo discover done` valida las marcas y corre el escáner. **Se cita la ubicación, nunca se copia un valor:** un secreto copiado bloquearía el commit, y un Crítico no tiene waiver. Leer esas líneas igual las manda al modelo; la skill lo dice y aplica `data-classification` y `prompt-hygiene`.

### Specs as-is (extiende ADR-0013)

- **Preámbulo de la capacidad**, fuera de los bloques y antes de `## Purpose`:
  - `Status: as-is` o `Status: as-is-validated`;
  - `Source:` con las unidades de origen.

  Una capacidad sin preámbulo es una spec viva normal.
- **Severidad:** los problemas de una spec tienen severidad (`error` o `warning`), y speclint, `exo check` y el `pre-commit` la respetan.
- **Un FR que trae evidencia puede no tener escenario:** es un warning. Un FR con `Status: as-is` sin evidencia ni marca de inferencia es un error.
- **`exo specs merge`** sobre una capacidad `as-is` sin validar falla: primero la valida una persona.
- **La re-síntesis** después de `update` solo reescribe specs `as-is`. Las validadas cambian por delta.

### Auditoría

- La población de la muestra son **los FR de las specs `as-is`**, que es lo que la persona valida, no las notas intermedias.
- La muestra se rankea por `sha256(semilla|id)`, ponderada por criticidad y con un mínimo por capacidad. La semilla queda registrada.
- El auditor, con contexto fresco y solo lectura, devuelve un veredicto por FR: correcto, incorrecto o no verificable. El motor calcula la precisión por capacidad.

### Rutas que escribe

La ingeniería inversa escribe solo en:
- `<carpeta del motor>/discovery/`;
- `<specs_dir>/capabilities/`;
- `<carpeta del motor>/context.md`, por secciones y con la aprobación de la persona: es suya (`project-wiki-guard`);
- los ADRs `*-recovered-*` en la carpeta de ADRs que ya use el proyecto, o `docs/adr/` (queda registrada en el inventario).

Cualquier cambio al proyecto es un change SDD del backlog de adopción. `exo discover status` avisa si `git status` muestra cambios fuera de esas rutas.

### Lo que no hace

- **No corre build ni tests del proyecto** (D-19). Medir la línea base es un item del backlog, con confirmación.
- **No escribe memoria** (D-37). Lo commiteado es la fuente compartida, y la memoria es por usuario.
- **No se instala por defecto** (D-33). El wizard ofrece el pack `discovery` cuando el repo ya tiene código.
- **`exo uninstall` conserva lo producido** (D-36): `discovery/` y `context.md` quedan y se informa.

## Consecuencias

- **Lo que vale para todos los proyectos:** la severidad en specs, el preámbulo y la guarda de merge cambian el motor aunque no se use discovery. Una capacidad sin preámbulo se comporta igual que antes.
- **Los subagentes de solo lectura** devuelven el texto de cada unidad, y el orquestador lo escribe. En repos grandes eso pasa dos veces por su contexto: la prueba de escala (D-35, F8) evalúa un extractor que escriba solo su unidad.
- **Los parsers heurísticos** tienen límites conocidos (imports dinámicos, alias que no están en la config). tree-sitter queda como extra posterior (D-14).
