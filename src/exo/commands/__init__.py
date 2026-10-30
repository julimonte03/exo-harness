"""Subcomandos del CLI. Cada módulo expone `register(subparsers)`."""

from exo.commands import inject, version

COMMANDS = [version.register, inject.register]
