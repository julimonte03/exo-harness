# Reglas del proyecto

Este proyecto usa un motor de desarrollo gobernado. La configuración y el registro de skills están en la carpeta del motor del repo; las skills, en la carpeta de skills de tu agente.

## Siempre

- **Evidencia:** leé el código real y la cadena de datos completa antes de afirmar algo. Citá `path:line`.
- **Alcance:** hacé solo lo pedido. No refactorices fuera del alcance ni borres `TODO` ajenos.
- **Comandos destructivos:** antes de borrar, sobrescribir o reescribir historia, pedí confirmación.
- **Ramas protegidas** (`main`, `master`, `prod`, `production`): nunca push directo, ni `--force`, ni `--no-verify`.
- **Commits:** Conventional Commits. Si el proyecto usa tracker, el ticket lo confirma la persona; no lo infieras de la rama.
- **Secretos:** nunca escribas credenciales, tokens ni datos personales en código, commits o memoria.

## Herramientas del motor

Se usan por terminal con el comando `exo`, siempre con `--json` cuando necesites procesar la salida.

- `exo change list` y `exo change status <change>`: estado de los cambios en curso.
- `exo skills list`: skills disponibles.
- `exo fitness classify --evidence-json '<json>'`: riesgo de un cambio (tier 1–4).
- `exo speclint <ruta>`: valida los artefactos de un cambio.
- `exo doctor`: diagnóstico si algo no funciona.

## Si tu agente no tiene subagentes

Las skills que piden "contexto fresco" o delegación corren inline: decilo explícitamente en tu respuesta ("sin aislamiento").
