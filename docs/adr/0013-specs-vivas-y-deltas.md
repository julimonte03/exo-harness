# ADR-0013 — Specs vivas por capacidad y deltas por cambio

- **Estado:** Aceptada
- **Fecha:** 2026-11-14
- **Decisión:** D-11, con D-27 para los artefactos por tier

## Contexto

D-11 decidió tener specs vivas:
- `specs/capabilities/<capacidad>/spec.md` es la fuente de verdad del comportamiento vigente.
- Cada cambio escribe un delta y `sdd-archive` lo integra.

El plan no fija el formato, y la integración tiene que ser determinista (`exo specs merge`).

El `spec.md` que valida speclint desde F1 tiene `## Requirements` (ítems `FR-n`) y `## Scenarios` (`### S-n`) separados. Ese formato no sirve para integrar por ID, porque los escenarios de un requisito quedan lejos del requisito.

## Decisión

**Spec de capacidad** (`specs/capabilities/<cap>/spec.md`):

```markdown
# Capability: <cap>

## Purpose
<para qué existe la capacidad>

## Requirements

### CAP-<cap>-FR-1: <título>
<texto del requisito>

#### Scenario: <título>
- Given …
- When …
- Then …
```

- **ID del requisito:** `CAP-<cap>-FR-n` o `CAP-<cap>-NFR-n`, donde `<cap>` es el nombre kebab-case de la carpeta.
- **Bloque:** cada requisito va desde su `###` hasta el próximo `###` o `##`, e incluye sus escenarios.
- **`## Removed Requirements`:** las lápidas de los requisitos borrados (ver Integración).
- **Fuera de los bloques:** el título, `Purpose` y cualquier otra sección se preservan byte a byte. Ahí entra lo que agregue F6, como el `status` y la procedencia.

**Delta** (el `spec.md` de un cambio):

```markdown
# Spec: <change-name>

## ADDED Requirements
### CAP-auth-FR-3: Sign in with SSO
…
#### Scenario S-1: …

## MODIFIED Requirements
### CAP-auth-FR-1: <título>
<texto nuevo completo, con sus escenarios>

## REMOVED Requirements
### CAP-auth-FR-2: <título>
Reason: <por qué>
```

- Las tres secciones son opcionales, pero tiene que haber al menos un requisito.
- **Escenarios:** en el delta llevan `S-n`, únicos dentro del cambio, para que `design.md` (Test Plan) y `test-spec.md` los citen. Al integrar, el `S-n` se quita: `#### Scenario S-1: x` → `#### Scenario: x`.
- **Varias capacidades:** el ID identifica la capacidad, así que un delta puede tocar varias.

**Integración** (`exo specs merge <change>`):
- **Validación previa:** primero valida todo y después escribe.
- **ADDED** con un ID que ya existe es error, salvo que el bloque sea idéntico (ya integrado). Si no existe, se agrega al final de `## Requirements`; si la capacidad no existe, se crea su `spec.md`.
- **MODIFIED** reemplaza el bloque. Con un ID inexistente es error.
- **REMOVED** saca el bloque de `## Requirements` y deja una lápida en `## Removed Requirements` (la sección se crea si no existe). La lápida tiene el encabezado del requisito, `Removed by change <change>.` y el `Reason:` del delta. Con un ID que no está ni en los requisitos ni en las lápidas, es error.
- **Lápidas:**
  - Si el ID ya tiene lápida, un REMOVED repetido no hace nada.
  - Un ID con lápida no se reusa: un ADDED o un MODIFIED con ese ID es error.
  - Así, integrar dos veces el mismo delta no cambia nada, incluso si solo tiene REMOVED, y un ID mal escrito sigue fallando.
- **Idempotencia:** si nada cambia, no escribe ni crea snapshot. Si cambia algo, hace snapshot de las specs tocadas y escribe de forma atómica, preservando los fines de línea de cada archivo.
- **Lo que no es mecánico** queda para `sdd-archive`, que lo resuelve con juicio: textos que chocan o una capacidad mal elegida.

**Speclint:**
- El `spec.md` de un cambio es de tipo `delta`; el de una capacidad, de tipo `capability`.
- El cross-check de referencias acepta `CAP-<cap>-N?FR-n` y `S-n`.

## Alternativas

- **Requisitos y escenarios separados** (el formato de F1): no permite integrar un requisito con sus escenarios como una unidad.
- **Integración con juicio, sin comando:** no es determinista ni se puede testear.
- **Numerar los escenarios dentro de la capacidad:** los números chocarían entre cambios y obligarían a renumerar.

## Consecuencias

- La plantilla `spec.md` pasa a ser un delta y se suma `capability-spec.md`. Las dos se instalan en `.exo/shared/templates/`.
- Un `spec.md` de cambio con el formato de F1 deja de validar. No hay proyectos con cambios todavía.
- F6 escribe specs de capacidad con este formato y suma sus campos fuera de los bloques.
