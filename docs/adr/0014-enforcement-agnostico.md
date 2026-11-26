# ADR-0014 — Enforcement agnóstico: git hooks, `exo check` y gates sin integraciones

- **Estado:** Aceptada
- **Fecha:** 2026-11-15
- **Decisiones:** D-12, D-21, D-29, D-30, D-31 y D-32

## Contexto

Casi todo dependía de que el agente cumpliera: solo la guarda de memoria (S1) y la validación de entradas (S2) estaban en código. F5 tiene que pasar lo verificable a controles que funcionen con cualquier agente o sin agente.

El plan de F5 traía piezas atadas a productos o a una organización:
- plantillas de GitHub Actions y GitLab CI;
- publicación de gates con `gh` y `glab`;
- un perfil de datos por organización (`legacy-profile`);
- hooks de agente.

ADR-0008 ya había señalado Azure DevOps. El dueño pidió que el motor sea agnóstico, igual que con los tickets (ADR-0012).

## Decisión

**Tres líneas de control, de la más cercana a la más fuerte:**

1. **Git hooks locales, por defecto** (D-21). `exo init` instala en la carpeta del motor:
   - `commit-msg`: formato del commit;
   - `pre-commit`: secretos y datos personales en lo que se commitea, y archivos de credenciales;
   - `pre-push`: ramas protegidas y force-push.

   Se activan con `core.hooksPath`. Si el proyecto usa husky, el motor se suma a husky en lugar de reemplazarlo. Cualquiera puede saltearlos con `--no-verify`, así que son ayuda temprana, no el gate.
2. **`exo check` en la CI: el gate real.** Es el único paso que una CI tiene que correr (`exo check --base <rama destino>`), en cualquier plataforma.
3. **Gates como artefactos del change** (`<change-root>/gates/<gate>.md`), con un formato fijo y su marcador.

**Sin integraciones con plataformas** (D-30):
- El motor detecta el host del repo desde el remoto (`github`, `azure-devops`, `gitlab` u `other`) y lo guarda en la config. El comportamiento es el mismo en todos.
- Los contratos traen ejemplos para las plataformas más comunes. Son ejemplos, no plantillas.
- `exo gate publish` arma un texto por gate. Si el proyecto configura un comando propio, el motor lo corre una vez por gate y el comando se encarga de crear o editar el comentario. Sin comando, el texto se imprime.
- Publicar sale a un servicio remoto, así que necesita la configuración explícita (invariante 11).

**Commits** (D-29): Conventional Commits con el ticket como footer `Refs: <ID exacto>`, no como prefijo del asunto.
- Es el formato estándar.
- Un ID tipo `#123` al principio de una línea es un comentario para git.
- Jira y Azure Boards encuentran el ID en cualquier parte del mensaje.

**Protección de datos agnóstica** (D-12):
- **Secretos y credenciales:** siempre activos, nivel Crítico.
- **Datos personales:** detectores genéricos, nivel Restringido. Por defecto, tarjetas (Luhn) e IBAN (mod 97), que validan dígito.
- **Documentos de un país** (CUIT, DNI, CPF, NIF, SSN), email y teléfono: opcionales.
- **La matriz de niveles por destino** es definición propia. Restringido se bloquea salvo waiver; Crítico se prohíbe siempre.
- Sale el perfil `legacy-profile`.

**Sin hooks de agente** (D-31): la política de la organización los bloquea en Claude Code (`allowManagedHooksOnly`, D-25), y los git hooks y la CI cubren lo mismo para cualquier agente.

**`exo p0`** (D-32): el gate de regresión mínima pasa a ser:
- el escáner sobre un dataset sintético;
- la validación de entradas (S2);
- los hooks activos en el proyecto.

## Alternativas

- **Plantillas por plataforma y publicación integrada:** atan el motor a productos y multiplican lo que hay que mantener.
- **Hooks opcionales:** en la mayoría de los proyectos no estarían.
- **Solo CI:** los errores aparecen recién en el PR.
- **Perfil de la organización por defecto:** genera falsos positivos fuera de su dominio y confundió al agente en F4.

## Consecuencias

- **Config, esquema 3:**
  - `governance.gates` (los gates por tier);
  - `data_protection.pii`;
  - `review.host` y `review.publish_command`;
  - sale `governance.dpa_profile`.
- **Instalación:**
  - el lock registra el bit de ejecución de los hooks;
  - `.gitattributes` fija `eol=lf` para ellos;
  - `exo uninstall` revierte `core.hooksPath`.
- **Fuera de alcance:** la tarea 9 de F5 (hooks de agente). Los ejemplos de CI y de publicación quedan sin verificar hasta que exista un remoto.
