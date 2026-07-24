from __future__ import annotations

import typer


cli = typer.Typer(help="Time block commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Plan time blocks."""
    if ctx.invoked_subcommand is None:
        typer.echo("zelblock is planned, but block commands are not implemented yet")


if __name__ == "__main__":
    cli()
