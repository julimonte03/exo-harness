# F5 — Gobierno, seguridad y gates

## Objetivo

Instalar las reglas always-on, los gates de calidad y seguridad y los jueces del reporte, y cerrar la principal debilidad que el propio reporte reconoce (§12.2): que casi todo dependía de que el agente cumpliera. Acá lo verificable pasa a estar **enforced** con git hooks locales y con `arnes check` en CI, que funcionan igual con cualquier agente o sin agente.

## Depende de

F4 cerrada. Decisiones D-12 y D-21.

## Alcance

Entra: `AGENTS.base.md` definitivo, skills de los packs `quality` y `security` necesarias para los gates, skills de gobierno de `core`, judge-common, git hooks, `arnes check` completo, publicación de gates en PRs, plantillas de CI, CODEOWNERS y roles, matriz DPA como datos, `arnes p0`, hooks de agente como segunda línea.

No entra: jueces de producto, negocio, frontend y equipo, `comite-excelencia`, `review-4r` (F7).

## Reglas always-on (`content/rules/AGENTS.base.md`, hasta 60 líneas)

Adaptación del resumen del §7.1 del reporte, en términos agnósticos:

- **Commits:** Conventional Commits con prefijo de ticket cuando hay tracker (`<TICKET> <type>(<scope>): <descripción>`). Sin ticket confirmado por la persona, no commitear; el ticket no se infiere de la rama ni de commits previos. Si la persona confirma que no hay ticket, Conventional Commits sin prefijo.
- **Ramas y PR:** rama desde la rama destino con solo el diff del ticket (`feature/<TICKET>-<slug>` o `<type>/<slug>`); todo por PR con título convencional; CI en verde antes de darlo por terminado.
- **Ramas protegidas:** nunca push directo, ni `--force`, ni `--no-verify`.
- **Comandos destructivos:** verificar contra patrones peligrosos y pedir confirmación.
- **Evidencia:** leer el código real y la cadena de datos completa antes de afirmar.
- **Contexto con fuentes:** usar `context-retrieval` antes de la primera búsqueda; citas junto a cada afirmación y línea final `Fuentes:`.
- **Gates:** un gate siempre corre su skill; resultado no aprobado requiere al rol `tech_lead`; en corridas desatendidas no se frena pero queda marcado.
- **Alcance:** no refactorizar fuera de lo pedido ni borrar `TODO`.
- **Memoria:** protocolo de `memory-protocol`.
- **Idioma:** el de la config.
- **Dónde está todo:** `.arnes/` y la lista de skills.

El validador falla si supera 60 líneas.

## Skills a escribir

**Pack `quality`:** `harness-review` (revisión integral en cuatro dimensiones: ingeniería, seguridad, UX/UI y accesibilidad), `review` (revisión del diff antes de commitear, solo lectura), `judgment-day` (revisión adversarial doble y ciega hasta `APPROVED` o `ESCALATED`; obligatoria en Tier 4), `judge-code-reviewer`, `judge-security`.

**Pack `security`:** `secure-coding-baseline`, `security-code-review`, `threat-modeling` (STRIDE, límites de confianza, DFD, casos de abuso), `data-classification` (aplica la matriz DPA y bloquea Restringido/Crítico hacia destinos no permitidos salvo waiver), `prompt-hygiene`.

**Pack `core`:** `skill-reviewer` (gate de supply chain de skills antes de distribuirlas).

**Contrato `judge-common.md`:** advisory-first (proponen followups tipados con prefijo `J*-` y no modifican nada), veredicto `APPROVED`/`ESCALATED`, independencia del generador, anti-cascada (validan contra la etapa anterior en `specs/`), descartes registrados en `dismissed_followups` (§7.8).

## Enforcement agnóstico

**Git hooks** en `.arnes/githooks/`, activados con `git config core.hooksPath .arnes/githooks` por `arnes init` (D-21). Si el proyecto ya usa husky o el framework pre-commit, el motor agrega sus pasos a ese mecanismo en lugar de reemplazarlo.

| Hook | Qué hace |
|---|---|
| `commit-msg` | Valida Conventional Commits y, si hay tracker, el prefijo de ticket con los prefijos aceptados |
| `pre-commit` | Escanea el diff en stage con el escáner de secretos y datos personales (`core/scan.py`; el guard S1 de la memoria salió con ADR-0009); corre `arnes speclint` sobre specs en stage; bloquea archivos tipo `.env` |
| `pre-push` | Bloquea push a ramas protegidas y force-push (leyendo las referencias que git pasa al hook); corre `arnes check --fast` |

Como cualquiera puede saltear hooks locales con `--no-verify`, **la CI es el gate real** y esto se documenta así.

**`arnes check` completo** (local y en CI): config válida; speclint de los changes del diff; AI Usage Record presente, válido y con `capabilities_used` no vacío; artefactos obligatorios por tier; registro de `judgment-day` en Tier 4; archivos de gate presentes para los gates configurados; escaneo de secretos del diff. Salida humana y `--json`, código de salida distinto de cero si falla.

**Gates como artefacto agnóstico.** Cada gate escribe `<change-root>/gates/<gate>.md` con el marcador `<!-- arnes-gate:<gate> -->`, la tabla Severidad | Archivo:línea | Hallazgo | Regla/OWASP, la línea "Requiere aprobación de tech_lead: sí|no" y la fuente. `arnes gate publish` publica o edita **un único comentario por gate** en el PR usando `gh` o `glab` si están disponibles; si no, imprime el texto (§7.2 del reporte).

**Hooks de agente como segunda línea** (Claude Code y Copilot): bloquear antes de ejecutar comandos como `git push --force`, push a ramas protegidas o borrados recursivos fuera del proyecto.

**Plantillas de CI** en `content/ci/`: GitHub Actions y GitLab CI que instalan el motor y corren `arnes check` y los tests del proyecto. Se instalan con `arnes init --ci github|gitlab`.

**Roles.** `governance.roles` en la config y plantilla `CODEOWNERS` para que `tech_lead` sea aprobador efectivo. Igual que en el reporte (§7.3), el motor no verifica roles: la garantía real es CODEOWNERS + branch protection, y se documenta cómo configurarlos.

**Matriz DPA como datos** en `content/shared/dpa-matrix.md` con el perfil `legacy-profile` (niveles Público, Interno, Restringido, Crítico y destinos memoria, LLM, GitHub y Jira, §7.5). **Actualizado por ADR-0014:** sale el perfil; la matriz genérica de niveles por destino vive en `content/packs/core/shared/data-protection.md` y los detectores en `data_protection.pii` de la config.

**`arnes p0`** (port de `_verify_p0.py`): regresión del escáner sobre un dataset sintético y de S2, más la verificación de que los git hooks están instalados y activos. S1 ya no existe (ADR-0009), así que no tiene regresión (D-32).

## Tareas (en orden)

1. `AGENTS.base.md` definitivo + test de longitud.
2. Git hooks + integración con husky/pre-commit + tests en repos git temporales.
3. `arnes check` completo + fixtures de changes completos e incompletos.
4. Gates como artefacto + `arnes gate publish`.
5. Skills de `security` y `data-classification` con la matriz DPA.
6. `judge-common`, jueces de código y seguridad, `harness-review`, `review`, `judgment-day`.
7. `skill-reviewer` + pre-chequeo determinista en `arnes validate` (secretos, instrucciones sospechosas, pedidos de datos sensibles).
8. Plantillas de CI, CODEOWNERS y guía de branch protection.
9. Hooks de agente en los adaptadores de Claude Code y Copilot.
10. `arnes p0`.
11. Checklist manual de proyecto nuevo de punta a punta en `docs/checklists/F5-proyecto-nuevo.md`.

## Criterios de aceptación

| # | Criterio | Comando / evidencia |
|---|---|---|
| 1 | Reglas acotadas | `arnes validate` confirma `AGENTS.base.md` ≤ 60 líneas |
| 2 | Hooks efectivos | En repos temporales: mensaje de commit inválido rechazado y válido aceptado; secreto sintético en stage rechazado; push a `main` y force-push rechazados |
| 3 | Check estricto | `arnes check` falla en un change Tier 2 sin `test-spec.md` o sin AI Usage Record, y pasa cuando están completos |
| 4 | Gates publicables | `arnes gate publish --dry-run` produce exactamente un comentario por gate, con su marcador |
| 5 | CI de proyecto | La plantilla de GitHub Actions corre `arnes check` en verde sobre el fixture completo y en rojo sobre el incompleto |
| 6 | P0 | `arnes p0` imprime `P0 GATE: PASSED` |
| 7 | Proyecto nuevo de punta a punta | Checklist manual con Claude Code y con Copilot: `install` → `arnes init` → cambio Tier 1 → PR con gates y AI Usage Record → `arnes check` en CI verde |

**Hito M2 (v0.1)** al cerrar esta fase.

## Referencias al reporte

Capítulo 07 completo, §6.7 (Gate summary), §8.1 (regla de gates), §12.1 #11 y §12.2.
