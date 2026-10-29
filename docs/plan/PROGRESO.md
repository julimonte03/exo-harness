# Progreso de construcción

**Fase activa:** F0

Una fase está **terminada** cuando: todos sus criterios de aceptación pasaron con el comando exacto, la CI está verde en los tres sistemas operativos y el PR de la fase está mergeado.

## Estado por fase

| Fase | Estado | Rama / PR | Inicio | Cierre | Notas |
|---|---|---|---|---|---|
| F0 Fundaciones | Pendiente | | | | |
| F1 Núcleo | Pendiente | | | | |
| F2 Adaptadores + instalador | Pendiente | | | | |
| F3 Memoria v2 | Pendiente | | | | |
| F4 Ciclo SDD | Pendiente | | | | |
| F5 Gobierno y gates | Pendiente | | | | |
| F6 Ingeniería inversa | Pendiente | | | | |
| F7 Packs | Pendiente | | | | |
| F8 Endurecimiento + v1.0 | Pendiente | | | | |

Estados: `Pendiente` · `En curso` · `Bloqueada (D-xx)` · `Terminada`.

## Registro de criterios de aceptación

Copiar este bloque por cada fase al cerrarla.

```markdown
### F<n> — <nombre> — <fecha>

| # | Criterio | Comando ejecutado | Resultado |
|---|---|---|---|
| 1 | ... | `...` | OK / NOK + detalle |

Checklist manual (si aplica): docs/checklists/F<n>-*.md — resultado y observaciones.
Decisiones tomadas durante la fase: D-xx → ADR-xxxx.
Desvíos respecto del plan y por qué:
```
