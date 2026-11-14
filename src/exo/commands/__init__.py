"""Subcomandos del CLI. Cada módulo expone `register(subparsers)`."""

from exo.commands import (
    backups,
    check,
    doctor,
    fitness,
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
    validate.register,
    tools.register,
    doctor.register,
    project.register,
    memory.register,
]
