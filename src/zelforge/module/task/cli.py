from __future__ import annotations

import typer


cli = typer.Typer(help="Task commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Manage tasks."""
    if ctx.invoked_subcommand is None:
        typer.echo("zeltask is planned, but task commands are not implemented yet")


if __name__ == "__main__":
    cli()
