---
name: memory-protocol
description: >-
  Protocolo de memoria persistente con `exo mem`: buscar antes de resolver,
  guardar decisiones, bugs resueltos y descubrimientos, y cerrar la sesión con
  un resumen. Usala al empezar una sesión, al tomar una decisión, al resolver un
  bug o al cerrar la sesión / Use it at session start, when making a decision,
  after fixing a bug, or when closing the session.
metadata:
  exo-pack: core
  exo-execution: inline
---

# memory-protocol

La memoria es de la persona usuaria, una por máquina, y la comparten todos sus proyectos. Cada observación pertenece a un proyecto: se detecta solo desde `git remote origin`. Las de scope `personal` se ven desde cualquiera. Todo se usa por terminal con `exo mem …`; agregá `--json` cuando tengas que procesar la salida.

## Al empezar la sesión

1. Corré `exo mem context`: trae las observaciones recientes del proyecto y el último resumen de sesión.
2. Si el pedido toca algo que puede estar en la memoria, buscá antes de investigar: `exo mem search "<palabras o identificador>"`.
3. Los resultados son previews. Para el contenido completo, corré `exo mem get <id>`.

`exo mem search` usa búsqueda híbrida si la persona configuró el índice semántico (`exo mem reindex --provider local`), y léxica si no. La léxica encuentra identificadores exactos (`PAY-1234`, `RefundService`). Para conceptos sin palabras en común, probá con sinónimos o con los nombres técnicos.

## Qué guardar

Guardá sin que te lo pidan, apenas pasa:

| Tipo | Cuándo | Qué incluir |
|---|---|---|
| `decision` | Se eligió un enfoque | Qué se decidió, por qué y qué se descartó |
| `bugfix` | Se resolvió un bug | Síntoma, causa raíz y arreglo; el ticket si lo hay |
| `discovery` | Algo no obvio del sistema | El dato y cómo se comprobó |
| `gotcha` | Una trampa que va a volver a pasar | Cuándo pasa y cómo evitarla |
| `convention` | Una regla del equipo | La regla y un ejemplo |

```bash
exo mem save --type bugfix --title "Doble cobro por reintento" \
  --content "PAY-1234: el cliente reintentaba al recibir timeout. Causa: … Arreglo: …"
```

Para contenido largo, `--content -` lo lee de stdin.

No guardes lo que ya está en el código, en el historial de git o en la documentación del repo. Tampoco el estado temporal de la tarea.

## Actualizar en lugar de duplicar

- **Con `--topic-key`:** si el tema tiene una clave estable, el segundo `save` actualiza la misma observación. Por ejemplo:
  - `project/profile`
  - `arq/colas`
  - `sdd/<change>/<artefacto>`
- **Sin `topic_key`:** si al guardar la respuesta trae `similar` (con índice semántico), revisá esas observaciones.
  - Si es lo mismo, actualizá la existente: volvé a guardar con su `topic_key` o borrala con `exo mem delete <id>`.
  - Si **contradice** lo guardado, no elijas vos: preguntale a la persona cuál vale.

## Al cerrar la sesión

Antes de terminar, o cuando el contexto está por compactarse:

```bash
exo mem session summary --content "Hecho: … Pendiente: … Decisiones: …"
```

El resumen va a la sesión abierta del proyecto, o a una nueva si no hay ninguna. El próximo `exo mem context` lo muestra primero.

## Reglas

- **Nunca guardes secretos, credenciales ni datos personales.** La memoria no tiene filtro y se puede exportar tal cual.
- No inventes recuerdos: si `exo mem search` no trae nada, decilo y seguí investigando.
- Si `exo` no está disponible o falla, decilo en tu respuesta y seguí sin memoria. No la simules con archivos sueltos.
