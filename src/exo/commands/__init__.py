"""Subcomandos del CLI. Cada módulo expone `register(subparsers)`."""

from exo.commands import (
    backups,
    check,
    doctor,
    fitness,
    gate,
    governance,
    hook,
    inject,
    memory,
    project,
    registry,
    speclint,
    specs,
    tools,
    validate,
    version,
)

COMMANDS = [
    version.register,
    inject.register,
    backups.register,
    registry.register,
    fitness.register,
    speclint.register,
    specs.register,
    check.register,
    hook.register,
    gate.register,
    governance.register,
    validate.register,
    tools.register,
    doctor.register,
    project.register,
    memory.register,
]
