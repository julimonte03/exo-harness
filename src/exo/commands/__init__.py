"""Subcomandos del CLI. Cada módulo expone `register(subparsers)`."""

from exo.commands import (
    backups,
    fitness,
    inject,
    registry,
    speclint,
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
    validate.register,
    tools.register,
]
