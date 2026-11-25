# Checklist F5 — Proyecto nuevo de punta a punta (criterio 7)

Verifica, con un agente real, que un proyecto nuevo queda gobernado desde el primer commit: `exo init` instala los packs por defecto y activa los git hooks, el ciclo SDD corre con los gates de su tier, cada commit pasa por los hooks y el paso de CI (`exo check --base`) da verde. Se usa el proyecto de juguete `tests/fixtures/repos/toy-python/`.

## Preparación (una vez por corrida)

1. Copiá el fixture a una carpeta temporal fuera del repo del motor, por ejemplo `<scratchpad>/toy-f5-t1`.
2. **Aislá los datos del usuario** antes de correr `exo` o el agente: `EXO_DATA_DIR` y `EXO_MEMORY_DB` a una carpeta temporal propia de la corrida.
3. En la carpeta:
   ```bash
   git init -q -b main && git add -A && git commit -qm "chore: toy base"
   exo init --agents claude-code --yes --ticket-pattern '[A-Z][A-Z0-9]*-\d+' --ticket-example PROJ-123
   git add -A && git commit -qm "chore: adopt exo"
   git config core.hooksPath    # .exo/githooks
   exo p0                       # P0 GATE: PASSED (3/3)
   ```
   El commit "adopt exo" ya pasa por los hooks: el `pre-commit` escanea todo lo que `exo init` instaló.
4. Con `claude -p` en una carpeta nueva, el workspace no es confiable y `permissions.allow` no aplica (hallazgo de F2). Pasá las herramientas a mano:
   ```bash
   claude -p "<pedido>" --allowedTools "Bash(exo:*) Bash(git:*) Bash(python:*) Bash(mkdir:*) Bash(ls:*) Bash(cat:*) PowerShell(exo:*) PowerShell(git:*) PowerShell(python:*) Read Edit Write Grep Glob TodoWrite Task Agent" --max-turns 250
   ```
5. El pedido aprueba las fases por adelantado (modo automático), da el ticket, prohíbe saltear los hooks, el push y el PR, y pide `exo gate publish --change <change> --dry-run` en lugar de publicar.
6. Al terminar, en la carpeta:
   ```bash
   git status --short
   git log --format='%h %s%n%b' main..HEAD
   exo check --base main
   exo speclint specs/archive/<fecha>-<change>
   exo gate publish --change <change> --dry-run
   exo p0
   ```

## Corrida 1 — Tier 1 (Claude Code 2.1.325, 2026-11-15)

**Pedido:** `/sdd-new` para sumar `--version` al CLI, con el ticket PROJ-7.

| Verificación | Esperado | Resultado |
|---|---|---|
| Instalación | `exo init` instala `core`, `sdd`, `quality` y `security`, activa los hooks y el commit de adopción pasa el `pre-commit` | OK, después de un arreglo. La primera vez el `pre-commit` bloqueó `.exo/lock.json`: un hash sha256 tenía una tira de dígitos que pasaba Luhn y el detector de tarjetas la tomó. Se corrigió el detector (`fd1cbad`), con su test |
| P0 en el proyecto | `exo p0` da `PASSED (3/3)` | OK |
| Ticket | Rama y commits con el ticket confirmado, como footer `Refs:` | OK: rama `feat/PROJ-7-add-version-option`, y los 4 commits llevan `Refs: PROJ-7` |
| Hooks | Cada commit pasa por `commit-msg` y `pre-commit`, sin `--no-verify` | OK: los 4 commits pasaron. El agente además corrió `review` antes de cada commit |
| Ciclo | Las fases del Tier 1: risk → new → apply → verify (liviano) → archive | OK: Tier 1 (FM-30) con evidencia por dimensión. Apply en `sdd-implementer` con el test primero; verify en `sdd-verifier`, con veredicto `ready` |
| Skills | Sin degradaciones: los packs `quality` y `security` están instalados | OK: `harness-review`, `secure-coding-baseline`, `review` y `prompt-hygiene` cargadas, "Degraded: none" |
| Gates | Tier 1 no exige gates; el texto del PR tiene el `contract_check` del verify | OK: `exo gate publish --dry-run` imprime un texto, `contract_check`, con su marcador y "Requires tech_lead approval: no" |
| PR y AI Usage Record | `pr.md` pasa speclint; el registro tiene `capabilities_used`, `phases_done` completo y el gate | OK: `pr.md` en la carpeta archivada; 25 capacidades registradas y `gates: [contract_check pass]` |
| Paso de CI | `exo check --base main` en verde | OK: `PASS PROJ-7-add-version-option (Tier 1)`, `OK: 0 errors`. Árbol limpio y 6 tests del juguete pasan. Verificado aparte: `python -m toy_todo --version` imprime `toy-todo 0.1.0` |

## Corrida 2 — Tier 2 (Claude Code 2.1.325, 2026-11-15)

**Pedido:** `/sdd-new` para que `add` rechace un título vacío o de solo espacios con exit code 2, con el ticket PROJ-8. Es la corrida que ejercita los gates.

| Verificación | Esperado | Resultado |
|---|---|---|
| Ciclo | risk → new → spec (+ test-spec) → apply → verify → archive | OK: Tier 2 (FM-20). `component_criticality` = 2 y `test_maturity_gap` = 2, con evidencia `path:line` |
| Tests primero | Los tests nuevos fallan antes del arreglo | OK: tres fallaron con `assert 0 == 2` y después pasaron. Quedaron 9 passed, contra 5 de base |
| Gates del tier | `contract_check` en el Gate summary y `gates/code_review.md` escrito por `harness-review` | OK: el verificador devolvió los dos textos y el orquestador escribió el gate. `code_review` APPROVED, `Source: skill harness-review` |
| `exo check` exige el gate | Sin `gates/code_review.md` el check falla | OK: se movió el archivo a mano y `exo check --base main` dio `FAILED: 1 errors`; restaurado, da `OK: 0 errors` |
| Publicación | `exo gate publish --dry-run`: un texto por gate, con su marcador | OK: `code_review` y `contract_check` |
| Hooks y ticket | 4 commits con `Refs: PROJ-8`, todos por los hooks | OK |

**Incidente del harness:** la primera respuesta del verificador se cortó por un error de stream, y Claude Code lo reportó como "Request interrupted by user". No fue un permiso ni un problema del motor. Se retomó la misma sesión con `claude -p --resume <session-id>`; el verify se repitió en contexto fresco y el ciclo terminó.

## Observaciones

- Las dos corridas notaron que falta `.exo/context.md` y sugirieron `project-onboarding`. Es lo esperado en un proyecto recién adoptado.
- Las dos escribieron el `Purpose` de la capacidad nueva y lo dejaron registrado como decisión del agente, para que la persona lo confirme.
- El juguete no tiene CI. Los ejemplos de `.exo/shared/ci-and-review.md` quedan `[No verificado]` porque no hay un remoto donde probarlos. El paso que proponen está cubierto por `pytest -k criterio_5`.

## Copilot (opcional)

No se corrió en esta fase. Para hacerlo: misma preparación con `--agents copilot`, abrir la carpeta en VS Code con Copilot en modo agente y pedir el mismo cambio de Tier 1. Anotá el resultado con las mismas verificaciones.
