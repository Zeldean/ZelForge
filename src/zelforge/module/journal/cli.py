from __future__ import annotations

import typer

from . import service


cli = typer.Typer(help="Journal commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Capture journal notes. Bare command opens the TUI."""
    if ctx.invoked_subcommand is None:
        from .tui import run

        run()


@cli.command()
def init() -> None:
    """Create journal storage files."""
    result = service.init()
    typer.echo(result["status"])


@cli.command()
def note(
    body: str,
    tag: list[str] = typer.Option([], "--tag", "-t", help="Note tag."),
    domain: str = typer.Option("", "--domain", help="Note domain code."),
) -> None:
    """Capture a quick note from the command line."""
    try:
        created = service.create_note(body=body, tags=tag, domain=domain)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"saved note {created['id'][:8]}")


@cli.command("list")
def list_notes() -> None:
    """List captured notes."""
    notes = service.list_notes()
    if not notes:
        typer.echo("no notes")
        return

    for saved in notes:
        preview = saved["body"].splitlines()[0][:60]
        typer.echo(f"{saved['id'][:8]}  {saved['created_at']}  {preview}")


if __name__ == "__main__":
    cli()
