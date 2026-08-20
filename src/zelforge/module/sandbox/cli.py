from __future__ import annotations

import typer


app = typer.Typer(
    help="Standalone TUI mockups for testing frontend interactions.",
    no_args_is_help=True,
)
cli = app


@app.callback()
def main() -> None:
    """Throwaway TUIs with no real backend, used to test frontend ideas."""


@app.command()
def hub() -> None:
    """Open the Hub TUI: tasks, trackers, levels, notes, timers, and more."""
    from .hub.app import run

    run()


if __name__ == "__main__":
    cli()
