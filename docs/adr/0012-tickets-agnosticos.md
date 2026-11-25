# ADR-0012 — Tickets agnósticos: patrón configurable, sin integración

- **Estado:** Aceptada
- **Fecha:** 2026-11-13
- **Decisión:** D-09

## Contexto

El motor usa el ID de ticket en tres lugares:
- en el nombre de cada cambio SDD (`PROJ-123-agregar-login`);
- en la rama;
- en el mensaje de commit.

El ticket lo confirma la persona; no se infiere de la rama.

El default de D-09 era elegir en el wizard un tracker de una lista (`jira`, `github`, `gitlab`, `linear`, `none`) y adaptar el formato a cada uno. ADR-0008 sugería sumar Azure Boards (`AB#123`). El dueño pidió no atar el motor a ningún tracker.

## Decisión

- **Sin integración:** el motor no se conecta a ningún tracker. No llama APIs ni lee ni crea tickets.
- **Patrón por proyecto:**
  - Cada proyecto define, en su config, cómo es un ID de ticket: una expresión regular, más un ejemplo para los mensajes.
  - El motor solo reconoce, valida y usa ese ID en los nombres de cambios, ramas y commits.
  - Sin patrón, no hay tickets: se usa Conventional Commits sin ID.
- **Ejemplos de patrones:**
  - `PROJ-123`, estilo Jira y otros: `[A-Z][A-Z0-9]*-\d+`.
  - `#123`, estilo GitHub o GitLab.
  - `AB#123`, Azure Boards.

  Son sugerencias para el wizard, no tipos con comportamiento propio.
- **La config** cambia en F4, con migración del esquema:
  - `tracker.type` y su lista cerrada se reemplazan por un patrón;
  - `tracker.prefix` y `tracker.prefixes` quedan cubiertos por el patrón.

## Alternativas

- **Lista cerrada de trackers** (default de D-09): ata el formato a productos concretos y obliga a tocar el motor por cada tracker nuevo.
- **Sin tickets:** el dueño eligió el patrón configurable, que también permite no tener tickets.

## Consecuencias

- F4 implementa la validación del ID y la pregunta única por ticket con el patrón del proyecto.
- **Nombres de cambio y épica** (D-26): el ID va normalizado. Todo carácter que no sea letra, dígito o guion pasa a guion (`AB#123` → `AB-123`). El ID exacto queda en el AI Usage Record.
- F5 usa el mismo patrón en los gates de commit. Cualquier mención a un tracker concreto en el plan se lee como un ejemplo de patrón.
