from __future__ import annotations

import typer

from zelforge.module.timer import service
from zelforge.module.timer import storage


app = typer.Typer(help="Timer commands.", no_args_is_help=True)
cli = app


@app.callback()
def main() -> None:
    """Track named timers and work sessions."""


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
    """Start a new timer session in the live log."""
    try:
        session = service.start_timer(timer_ref, title=title)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(
        f"started session {session['session_id'][:8]} "
        f"for {session['timer']['name']}: {session['title']}"
    )


@app.command()
def pause() -> None:
    """Pause the active session."""
    typer.echo("pause is planned, but service logic is not implemented yet")


@app.command()
def resume() -> None:
    """Resume the last timer as a new session."""
    typer.echo("resume is planned, but service logic is not implemented yet")


@app.command()
def stop(timer_ref: str) -> None:
    """Stop a timer's active session in the live log."""
    try:
        session = service.stop_timer(timer_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(
        f"stopped session {session['session_id'][:8]}: "
        f"{session['timer']['name']} - {session['title']} "
        f"({session['duration_seconds']}s)"
    )


@app.command()
def save() -> None:
    """Save old closed log sessions into permanent storage."""
    try:
        result = service.save_closed_sessions()
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(
        f"saved {result['saved']} sessions; "
        f"skipped {result.get('skipped_invalid', 0)} invalid sessions; "
        f"removed {result.get('removed_events', 0)} log events; "
        f"{result['remaining_events']} log events remain"
    )


@app.command()
def status(timer_ref: str | None = typer.Argument(None)) -> None:
    """Show today's timer sessions and totals."""
    try:
        groups = service.get_today_status(timer_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    if not groups:
        typer.echo("no timer sessions for today")
        return

    typer.echo("timer sessions today")
    for group in groups:
        timer = group.get("timer", {})
        code = timer.get("code") or "-"
        name = timer.get("name") or "-"
        typer.echo(f"{code}  {name}")

        for session in group["sessions"]:
            started = _format_time(session["started_at"])
            stopped = "active" if session["active"] else _format_time(session["stopped_at"])
            duration = _format_duration(session["duration_seconds"])
            typer.echo(f"  {started} -> {stopped:<6} {duration:<8} {session['title']}")

        typer.echo(f"  total        {_format_duration(group['total_seconds'])}")


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
    try:
        return service.find_timer(timer_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


def _format_duration(total_seconds: int) -> str:
    hours, remainder = divmod(max(total_seconds, 0), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m"

    if minutes:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


def _format_time(value: str) -> str:
    return value[11:16]


if __name__ == "__main__":
    cli()
