@AGENTS.md

## Solo para Claude Code

- Al empezar una fase, entrá en plan mode, leé el archivo de la fase y proponé la secuencia de commits antes de escribir código. Esperá aprobación.
- Usá subagentes para explorar o revisar cuando haya que leer 4 o más archivos, y para la revisión final de la fase con contexto fresco.
- Antes de dar una fase por terminada, corré los criterios de aceptación uno por uno con el comando exacto y mostrá la salida resumida.
- Si una verificación de documentación externa es necesaria (por ejemplo convenciones de otros agentes en F0), buscá la fuente oficial y anotá URL y fecha.
