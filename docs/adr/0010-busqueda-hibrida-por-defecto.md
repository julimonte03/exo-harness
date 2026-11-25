# ADR-0010 — Búsqueda híbrida con embeddings ONNX como default de la memoria

- **Estado:** Aceptada
- **Fecha:** 2026-11-13
- **Decisiones:** D-07 y D-08 (`docs/plan/04-DECISIONES.md`)

## Contexto

El plan de F3 deja que el default del backend (D-07) y de los embeddings (D-08) lo decida un experimento, con una regla fijada antes de correrlo. La regla quedó congelada en el commit `b8dc9b7`, antes de la corrida.

Por ADR-0009 se comparó `lexical` contra `hybrid-sqlite` con dos modelos multilingües, sin Qdrant y sin Ollama (no está instalado en la máquina del experimento):
- `static`: model2vec `minishlab/potion-multilingual-128M`;
- `onnx`: FastEmbed `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.

**Entorno:** Windows 11, Python 3.14.5, sqlite-vec 0.1.9, model2vec 0.10.0 y FastEmbed 0.9.1 con onnxruntime 1.32.0, en CPU.

**Dataset sintético** (`tests/memory_eval/`):
- 80 memorias de una plataforma de pagos ficticia, en español e inglés.
- 50 consultas: 15 exactas, 20 paráfrasis, 10 de idioma cruzado y 5 sin respuesta.

**Reporte completo:** `docs/evals/memory-2026-11-13.md`. Se regenera con `exo mem eval --output docs/evals/memory-<fecha>.md`.

## Resultados

| Configuración | Recall@5 | exactas | paráfrasis | cruzadas | FP sin respuesta | p95 ms (5 000 memorias) | Instalado | Arranque en frío |
|---|---|---|---|---|---|---|---|---|
| `lexical` | 62,2 | 100 | 55 | 20 | 80 % | 4,7 | 0 MB | 0,1 s |
| `hybrid-static` | 77,8 | 100 | 80 | 40 | 40 % | 31,2 | 635 MB | 5,7 s |
| `hybrid-onnx` | **80,0** | 100 | 85 | 40 | 0 % | 67,1 | 424 MB | 2,4 s |
| `semantic-onnx` (referencia) | 80,0 | 93,3 | 70 | 80 | 0 % | 59,2 | 424 MB | 2,3 s |

La regla congelada:
- **Recall@5:** la híbrida pasa a default si sube el Recall@5 global al menos 10 puntos.
- **Exactas:** no puede bajar las consultas exactas más de 2 puntos.
- **Latencia:** su p95 tiene que quedar por debajo de 150 ms.
- **Desempate:** entre varias, gana la de mejor Recall@5; si empatan, la más liviana.

Las dos híbridas pasan: +15,6 y +17,8 puntos, sin pérdida en las exactas. Gana **`hybrid-onnx`**, que además pesa menos y arranca más rápido que `hybrid-static`.

## Decisión

- **D-07:** el default es `hybrid-sqlite`. El modo `auto` usa la búsqueda híbrida cuando la base tiene un índice semántico y, si no, la léxica, que sigue siempre disponible sin extras (criterio 2).
- **D-08:** el proveedor `local` resuelve primero `onnx` y después `static`. Los modelos se bajan solo a pedido (ADR-0009). La configuración recomendada:

  ```bash
  pip install exo-harness[vector]      # sqlite-vec + FastEmbed
  exo mem model pull                   # onnx: paraphrase-multilingual-MiniLM-L12-v2
  exo mem reindex --provider local
  ```

- **Extras:**
  - `[vector]` pasa a ser sqlite-vec + FastEmbed.
  - model2vec queda como alternativa en `[static]`.
  - Se quita el extra `[onnx]`.

## Alcance de la evidencia

- **Dataset propio:** lo escribió quien implementó el motor, aunque las paráfrasis evitan a propósito las palabras de cada memoria. Es chico: una consulta equivale a 2,2 puntos de Recall@5. Entre `onnx` y `static` hay justo una consulta de diferencia, así que esa preferencia es débil. La diferencia contra la léxica es clara.
- **Idioma cruzado:** la fusión RRF con pesos iguales diluye lo semántico. La híbrida acierta el 40 % y la semántica sola, el 80 %. Ajustar los pesos (`weights` en `MemoryStore.query`) podría mejorarlo; queda como trabajo futuro, con su propio experimento.
- **Falsos positivos de la léxica:** son altos porque cada palabra suma (OR) y las comunes coinciden siempre. Un filtro de palabras vacías podría bajarlos. También queda para más adelante.
- **Cobertura:** solo se midió en Windows y en CPU. Con Python 3.10, pip resuelve un onnxruntime anterior, porque el último exige 3.11 o más.
- **La latencia es con el modelo cargado** (agregado en la revisión de F3):
  - El p95 de 67 ms, 85 ms al repetir la corrida, se mide con la base abierta y el modelo en memoria.
  - Es la latencia del servidor MCP, que desde la revisión reutiliza el proveedor dentro del proceso.
  - Cada llamada del CLI es un proceso nuevo y carga el modelo. Con onnx, `exo mem search` y `exo mem save` tardan entre 1,3 y 2,1 s; es la columna de arranque en frío.
  - El criterio 6 de F3 («p95 de búsqueda < 150 ms con 5 000 memorias») se cumple para la búsqueda en sí. Para un agente que usa el CLI, el costo real por llamada es el del arranque.
- **Los falsos positivos de la tabla no son un filtro** (agregado en la revisión):
  - El umbral se calibra con las mismas consultas y no se aplica al buscar, así que la híbrida igual devuelve resultados para las consultas sin respuesta.
  - El 0 % significa que ninguna tuvo un primer resultado con una confianza tan alta como la de un acierto.

## Consecuencias

- La CI instala `[dev,vector,static]` en el job de memoria. Los tests con modelos reales se saltean si no están bajados.
- `exo doctor` informa si falta el extra, el modelo o vectores, y si se usa el backend lento de Python porque no carga sqlite-vec.
