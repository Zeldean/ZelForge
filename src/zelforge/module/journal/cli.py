from __future__ import annotations

import typer


cli = typer.Typer(help="Journal commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Manage journal notes and vault indexes."""
    if ctx.invoked_subcommand is None:
        typer.echo("zeljournal is planned, but journal commands are not implemented yet")


if __name__ == "__main__":
    cli()
