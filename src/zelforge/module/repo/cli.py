from __future__ import annotations

import typer


cli = typer.Typer(help="Repository commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Manage local repository indexes."""
    if ctx.invoked_subcommand is None:
        typer.echo("zelrepo is planned, but repo commands are not implemented yet")


if __name__ == "__main__":
    cli()
