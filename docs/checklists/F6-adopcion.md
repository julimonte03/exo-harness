# Checklist F6: adopción de un proyecto existente (criterios 3, 4 y 5)

Verifica con un agente real que exo adopta un proyecto que ya tiene código, sin tocarlo. Recorre inventario, plan, extracción con evidencia, specs as-is, auditoría independiente y backlog de adopción. Se usa el fixture `tests/fixtures/repos/py-invoices/`. Su verdad conocida (`tests/fixtures/ground-truth/py-invoices.md`) vive afuera del fixture, así el agente no lee la respuesta.

## Preparación

1. Copiá el fixture a una carpeta temporal fuera del repo del motor y aislá los datos del usuario (`EXO_DATA_DIR` y `EXO_MEMORY_DB` a una carpeta temporal).
2. En esa carpeta:
   ```bash
   git init -q -b main && git config core.autocrlf false
   git add -A && git commit -qm "chore: existing project"
   exo init --agents claude-code --yes --packs core,sdd,quality,security,design,discovery
   git add -A && git commit -qm "chore: adopt exo"
   exo discover status    # steps that ran: none
   ```
3. Corré Claude Code sin `python` en las herramientas, para que no pueda correr el build ni los tests del proyecto (D-19):
   ```bash
   claude -p "<pedido>" --allowedTools "Bash(exo:*) Bash(git:*) Bash(ls:*) Bash(cat:*) Bash(mkdir:*) PowerShell(exo:*) PowerShell(git:*) Read Edit Write Grep Glob TodoWrite Task Agent" --max-turns 400
   ```
4. El pedido arranca con `/exo-adopt` y da las respuestas por adelantado:
   - profundidad `standard`;
   - la wiki y los ADRs recuperados quedan aprobados;
   - en R6, el análisis de brechas y el backlog, pero sin validar capacidades ni crear changes;
   - sin build, sin tests y sin commits.
5. Al terminar, chequeá contra la verdad conocida (el script está en el scratchpad de la fase, `check_adopt.py`):
   - el criterio 3, con el match de capacidades por archivos clave;
   - el criterio 4, con la precisión por capacidad de `exo discover coverage`;
   - el criterio 5, con `outside_changes` de `exo discover status` y `git status`.

## Corrida: `py-invoices` (Claude Code 2.1.325, 2026-11-16)

| Verificación | Esperado | Resultado |
|---|---|---|
| R0 a R2 | El motor arma el inventario, el grafo y el plan; la persona elige la profundidad | OK: 10 unidades, 1188 líneas, unos 20 mil tokens, todas en detalle (`standard`) |
| R3 | Cada unidad se extrae en `re-extractor`, con hasta 3 en paralelo, y cierra con `exo discover done` | 9 de 10 cerradas. La de `auth` quedó pendiente: Claude Code pidió un permiso para leer `src/invoices/auth/tokens.py`, que una corrida desatendida no puede dar. El agente no lo esquivó y lo dejó como pregunta abierta (OQ-1). Es una protección del harness, no del motor |
| R4 | Specs as-is con evidencia, la wiki y los ADRs recuperados | OK: 5 capacidades (invoicing, payments, customers, access-control, quotes) y 52 FR, todos con evidencia. `.exo/context.md` con Architecture (Mermaid), Modules, Main flows e Integrations. 7 ADRs `docs/adr/000N-recovered-*.md` con `Status: Recovered` |
| Criterio 3: una spec por capacidad del ground truth | Las 5 capacidades esperadas tienen al menos una spec que cita sus archivos clave | OK: invoice-totals, invoice-lifecycle, card-payments, access-control y customer-directory |
| R5 y criterio 4 | La muestra auditada en `re-auditor` con contexto fresco da ≥ 90 % por capacidad | OK: la muestra de 30 FR (semilla 2728934915) dio `quotes` al 75 % y la marcó. El agente reabrió sus unidades, las re-extrajo, re-sintetizó la capacidad y la re-auditó: al final, las 5 capacidades quedaron al 100 % |
| Criterio 5: solo lectura | `git status` muestra cambios solo en las rutas permitidas | OK: `outside_changes: []`; los cambios son solo `.exo/context.md`, `.exo/discovery/`, `docs/adr/*-recovered-*` y `specs/capabilities/` |
| R6 | Brechas y backlog, sin validar ni crear changes | OK: 16 ítems en `adoption-backlog.md`, entre ellos tests de caracterización por capacidad, fallar cerrado en el modo sandbox y la línea base de tests (sin correrla). Además, la auditoría de la config de agentes. Ninguna capacidad se validó y no se creó ningún change |
| D-19 y D-37 | Sin build ni tests del proyecto, y sin memoria | OK: no corrió tests, y no leyó ni escribió `exo mem` |

**Lo que encontró en el proyecto:** el modo sandbox queda activo cuando no se define `INVOICES_SANDBOX`, y en sandbox `POST /auth/token` entrega un token de cualquier rol sin contraseña. Lo registró como deuda (DEBT-1) y como ítem del backlog (ADOPT-6, Tier 3), con su evidencia `path:line`.

## Lo que la corrida mostró del contenido (corregido en el cierre)

- **La auditoría tiene que ser de la muestra entera.** En la segunda ronda, el agente re-auditó solo los 4 FR de `quotes` y conservó los otros 26 veredictos. Ahora `exo-adopt` y `re-audit` mandan la muestra entera, porque `exo discover audit` reemplaza el registro.
- **El chequeo final de `exo-adopt`** usaba `exo speclint` sobre la carpeta `capabilities`, que speclint no acepta. Ahora usa `exo check`.
- **Una unidad que no se puede cerrar** dejaba a R4 sin salida. Ahora `exo discover skip` la saca del ciclo y la cuenta como no cubierta.

## Copilot (opcional)

No se corrió. Para hacerlo: la misma preparación con `--agents copilot` y el mismo pedido en Copilot en modo agente.
