# Verdad conocida de los fixtures de ingeniería inversa

Un archivo `<fixture>.md` por cada repo de `tests/fixtures/repos/<fixture>/`, **afuera del fixture** para que la adopción no lea la respuesta (ADR-0015). Cada uno tiene prosa (qué es el proyecto y por qué tiene cada caso difícil) y un único bloque `json` con el esquema de `tests/_ground_truth.py`.

Reglas para los fixtures:
- **Código sintético:** sin secretos, sin datos personales reales; solo tarjetas de prueba publicadas y dominios `example.com`.
- **Contenido:** en inglés, como un proyecto real; entre 1 y 1,5 mil líneas.
- **Sin carpetas `build/` ni `dist/`:** el `.gitignore` del repo las ignora.
- **Sin dependencias instaladas** (`node_modules/`, `target/`, venvs): solo los manifiestos.
- **Python:** el código parsea con Python 3.10.
