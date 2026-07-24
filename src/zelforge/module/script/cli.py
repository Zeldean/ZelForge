from __future__ import annotations

import typer


cli = typer.Typer(help="Script utility commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Run small utility scripts."""
    if ctx.invoked_subcommand is None:
        typer.echo("zelscript is planned, but script commands are not implemented yet")


if __name__ == "__main__":
    cli()
