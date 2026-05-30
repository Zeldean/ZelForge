from __future__ import annotations

import click

from . import __version__


@click.group()
def cli() -> None:
    """ZelForge CLI."""


@cli.command()
def version() -> None:
    """Show the installed ZelForge version."""
    click.echo(f"zelforge {__version__}")


if __name__ == "__main__":
    cli()
