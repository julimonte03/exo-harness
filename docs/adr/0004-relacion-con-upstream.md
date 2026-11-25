# ADR-0004 — Relación con gentle-ai y Engram (upstream)

- **Estado:** Aceptada
- **Fecha:** 2026-10-29
- **Decisión:** D-03

## Contexto

`gentle-ai` es un proyecto parecido, escrito en Go. Hoy gentle-ai es agnóstico de agente: configura más de quince agentes existentes sin instalarlos, instala skills, configura MCP, hace backups de config, tiene `doctor` y usa Engram como memoria. Engram es un binario Go con SQLite + FTS5 (búsqueda léxica), accesible por CLI, HTTP, MCP y TUI, que guarda su base en `~/.engram/engram.db`. La tarea 0.5 de F0 pide verificar las licencias antes de reusar nada.

Licencias verificadas el 2026-10-29:

| Proyecto | Repo | Licencia (SPDX) | Copyright | LICENSE |
|---|---|---|---|---|
| gentle-ai | https://github.com/Gentleman-Programming/gentle-ai | MIT | `Copyright (c) 2025 Gentleman Programming` | https://github.com/Gentleman-Programming/gentle-ai/blob/main/LICENSE |
| Engram | https://github.com/Gentleman-Programming/engram | MIT | `Copyright (c) 2026 Alan Buscaglia` | https://github.com/Gentleman-Programming/engram/blob/main/LICENSE |

**Marcas:** según el README de gentle-ai, "Gentle AI™" y "Engram™" son marcas de Alan Buscaglia. La licencia MIT cubre el código, pero no habilita a sugerir aval ni afiliación: https://github.com/Gentleman-Programming/gentle-ai/blob/main/TRADEMARKS.md. Son marcas ™, no registradas.

## Decisión

Opción **(a)**: construir el motor propio en Python siguiendo el plan, y usar gentle-ai y Engram **solo como referencia**: matriz de agentes, rutas y comportamiento observable.

- No se copia código ni texto de upstream por defecto. Si alguna vez se reusa un fragmento, se conserva el aviso MIT y se lo registra en `THIRD_PARTY_NOTICES.md`, que se crea ese día.
- No se usan los nombres "Gentle AI" ni "Engram" como nombre de componentes, comandos ni documentación propia. La memoria del motor se llama `memory` (tools `mem_*`); "engram" aparece solo al citar el upstream.

## Alternativas

- **(b) Fork o extensión de gentle-ai en Go.** El upstream es muy activo, así que habría divergencia constante. Además cambia el lenguaje decidido en ADR-0002.
- **(c) Usar el binario de Engram como memoria.** Su búsqueda es solo léxica, y la memoria híbrida es una de las mejoras centrales del plan (F3).

## Consecuencias

- El valor diferencial (gobierno, gates, AI Usage Record, DPA, jueces, ingeniería inversa, memoria híbrida) se construye y se mantiene acá.
- La matriz de agentes de gentle-ai sirve para contrastar, pero la fuente final siempre es la documentación oficial de cada agente (`docs/agent-matrix.md`).
- Compatibilidad de API con Engram (15 tools `mem_*`): se replica por contrato, sin código upstream.
