from __future__ import annotations

import typer


cli = typer.Typer(help="Habit commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Track daily habits."""
    if ctx.invoked_subcommand is None:
        typer.echo("zelhabit is planned, but habit commands are not implemented yet")


if __name__ == "__main__":
    cli()
