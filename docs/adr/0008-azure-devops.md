# ADR-0008 — Azure DevOps para repos y CI

- **Estado:** Aceptada; reemplazada en parte por ADR-0017 (2026-11-19). El repo y la CI del motor pasaron a GitHub y GitHub Actions, y `azure-pipelines.yml` queda como ejemplo. Lo de los proyectos ya lo había generalizado ADR-0014 (D-30).
- **Fecha:** 2026-10-30
- **Decisión:** D-16 (`docs/plan/04-DECISIONES.md`)

## Contexto

El plan asumía GitHub para el repo del motor y plantillas de GitHub Actions y GitLab CI para los proyectos. El dueño confirmó que los repos van a estar en **Azure DevOps** (Azure Repos), con un pipeline propio. Todavía no están creados.

Datos de Azure DevOps que importan, verificados el 2026-10-30:

- La plantilla de PR por defecto es `pull_request_template.md`, y se busca en `.azuredevops/`, `.vsts/`, `docs/` o la raíz, en ese orden: https://learn.microsoft.com/en-us/azure/devops/repos/git/pull-request-templates
- En Azure Repos, la validación de PRs se configura con una política de rama (*Build validation*), no con `pr:` en el YAML: https://learn.microsoft.com/en-us/azure/devops/pipelines/repos/azure-repos-git
- Los revisores obligatorios también son una política de rama. Que Azure Repos no use `CODEOWNERS` como GitHub es `[No verificado]`: hay que revisarlo en F5.

## Decisión

- El repo del motor va a Azure Repos. La CI del motor pasa a **`azure-pipelines.yml`**, con matriz Linux, macOS y Windows × Python 3.10 y 3.13 en agentes hospedados por Microsoft; se adapta a un pool propio si el equipo lo usa. Se elimina `.github/workflows/ci.yml`.
- La plantilla de PR pasa a `.azuredevops/pull_request_template.md`.
- Para los proyectos, el motor no impone un pipeline: `exo check` (F4/F5) se invoca desde el pipeline del equipo, y se entrega una plantilla de Azure Pipelines de ejemplo. GitHub Actions y GitLab CI salen de la v1.

## Alternativas

- **Mantener GitHub Actions.** No correría nunca, porque el código no va a estar en GitHub.
- **Que el motor genere el pipeline completo de cada proyecto.** Choca con el pipeline propio que ya tiene el equipo.

## Consecuencias

- **F0/F1:** el criterio de "CI verde en los tres sistemas" se verifica con Azure Pipelines cuando exista el repo. Mientras tanto sigue la regla de cierre local de `docs/plan/PROGRESO.md`.
- **F2:** el adaptador de Copilot no necesita `.github/agents/` (era para el cloud agent de GitHub.com). VS Code y Copilot CLI leen `.claude/agents/`, `.claude/skills/`, `AGENTS.md` y `.mcp.json`.
- **F4:** el tracker de tickets probablemente sea **Azure Boards**, que referencia work items como `AB#123`. Hay que sumarlo como tipo de tracker al decidir D-09.
- **F5:** `exo gate publish` publica un comentario por gate usando la API REST de Azure DevOps o `az repos`, en lugar de `gh`/`glab`. Los roles se garantizan con políticas de rama. La plantilla de pipeline de proyecto es de Azure Pipelines.
