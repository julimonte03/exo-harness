---
name: sdd-status
description: >-
  Muestra el estado de los changes SDD del proyecto (fase, artefactos,
  followups y ticket) sin adivinar. Usala cuando pregunten en qué está un
  cambio o qué falta / Use it when asked about the status of a change or what
  is missing.
metadata:
  exo-pack: sdd
  exo-execution: inline
---

# sdd-status

Respondé solo con lo que devuelve el motor. No infieras el estado leyendo archivos a mano.

## Pasos

1. Para ver todos los changes, corré `exo change list --json`.
2. Para uno en particular, corré `exo change status <change-name> --json`.
3. Para los followups abiertos, corré `exo change followups <change-name> --json`.
4. Resumí: fase, artefactos presentes, ticket, followups abiertos y qué sigue.

Si el comando no está disponible, decilo y no inventes el estado.
