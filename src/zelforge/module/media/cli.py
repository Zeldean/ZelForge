from __future__ import annotations

import typer


cli = typer.Typer(help="Media commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Manage media libraries."""
    if ctx.invoked_subcommand is None:
        typer.echo("zelmedia is planned, but media commands are not implemented yet")


if __name__ == "__main__":
    cli()
