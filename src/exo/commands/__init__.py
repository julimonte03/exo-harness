"""Subcomandos del CLI. Cada módulo expone `register(subparsers)`."""

from exo.commands import backups, inject, registry, version

COMMANDS = [version.register, inject.register, backups.register, registry.register]
