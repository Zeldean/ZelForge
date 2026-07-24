from __future__ import annotations

import typer

from zelforge.module.timer import storage


app = typer.Typer(help="Timer commands.")


@app.command()
def init() -> None:
    """Create timer storage files."""
    result = storage.init()
    typer.echo(result["status"])


@app.command()
def add(
    name: str,
    code: str | None = typer.Option(None, help="Short user-facing timer code."),
    description: str = typer.Option("", help="Timer description."),
    domain: str = typer.Option("", help="Timer domain."),
    archived: bool = typer.Option(False, help="Create the timer as archived."),
) -> None:
    """Create a new timer."""
    timer = storage.add_timer(
        name=name,
        code=code,
        description=description,
        domain=domain,
        archived=archived,
    )

    typer.echo(f"created timer {timer['code'] or timer['id']}: {timer['name']}")


@app.command("list")
def list_timers(show_archived: bool = typer.Option(False, "--archived")) -> None:
    """List timers."""
    timers = storage.get_timers()

    for timer in timers:
        if timer.get("archived") and not show_archived:
            continue

        code = timer.get("code") or "-"
        archived = " archived" if timer.get("archived") else ""
        typer.echo(f"{code}  {timer['name']}  {timer['id']}{archived}")


@app.command()
def start(
    timer_ref: str,
    title: str | None = typer.Option(None, help="Session title."),
) -> None:
    """Start a new timer session."""
    timer = _find_timer(timer_ref)
    session_title = title or timer["name"]

    session = storage.add_session(
        timer_id=timer["id"],
        title=session_title,
    )

    typer.echo(f"started session {session['id']} for {timer['name']}")


@app.command()
def pause() -> None:
    """Pause the active session."""
    typer.echo("pause is planned, but service logic is not implemented yet")


@app.command()
def resume() -> None:
    """Resume the last timer as a new session."""
    typer.echo("resume is planned, but service logic is not implemented yet")


@app.command()
def stop() -> None:
    """Stop the active session."""
    typer.echo("stop is planned, but service logic is not implemented yet")


@app.command()
def status() -> None:
    """Show active timer status."""
    typer.echo("status is planned, but service logic is not implemented yet")


@app.command()
def sessions(timer_ref: str | None = typer.Argument(None)) -> None:
    """List timer sessions."""
    timer_id = _find_timer(timer_ref)["id"] if timer_ref else None

    for session in storage.get_sessions():
        if timer_id and session.get("timer_id") != timer_id:
            continue

        stopped_at = session.get("stopped_at") or "active"
        typer.echo(
            f"{session['started_at']} -> {stopped_at}  "
            f"{session['title']}  {session['timer_id']}"
        )


def _find_timer(timer_ref: str) -> dict:
    """Find a timer by UUID id or short code."""
    for timer in storage.get_timers():
        if timer.get("id") == timer_ref or timer.get("code") == timer_ref:
            return timer

    raise typer.BadParameter(f"Unknown timer: {timer_ref}")
