from __future__ import annotations

from datetime import datetime

import typer

from zelforge.module.timer import service
from zelforge.module.timer import storage


app = typer.Typer(help="Timer commands.", no_args_is_help=True)
cli = app


@app.callback()
def main() -> None:
    """Track named timers and work sessions."""

@app.command()
def tui() -> None:
    """Open the interactive timer TUI."""
    from .tui import run

    run()

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

    typer.echo(f"started {session['timer']['name']}: {session['title']}")


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
        f"stopped {session['timer']['name']}: "
        f"{session['title']} ({session['duration_seconds']}s)"
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
def status(
    timer_refs: list[str] = typer.Argument(None),
    date: str | None = typer.Option(
        None,
        "--date",
        help="Show one local date, formatted YYYY-MM-DD.",
    ),
    start_date: str | None = typer.Option(
        None,
        "--start-date",
        help="Start local date for an inclusive range.",
    ),
    end_date: str | None = typer.Option(
        None,
        "--end-date",
        help="End local date for an inclusive range.",
    ),
) -> None:
    """Show timer sessions and totals for a local date or range."""
    try:
        groups = service.get_status(
            timer_refs=timer_refs,
            date_filter=date,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    if not groups:
        typer.echo("no timers to display")
        return

    include_date = _should_include_date(date, start_date, end_date)
    stop_width = 16 if include_date else 6
    for group in groups:
        timer = group.get("timer", {})
        code = timer.get("code") or "-"
        name = timer.get("name") or "-"
        typer.echo(f"{name} ({code})")

        title_width = max([len(session["title"]) for session in group["sessions"]] + [5])
        for session in group["sessions"]:
            started = _format_time(session["started_at"], include_date=include_date)
            stopped = (
                "active"
                if session["active"]
                else _format_time(session["stopped_at"], include_date=include_date)
            )
            duration = _format_duration(session["duration_seconds"])
            typer.echo(
                f"├── {session['title']:<{title_width}}  "
                f"{started} -> {stopped:<{stop_width}}  {duration}"
            )

        typer.echo(
            f"└── {'TOTAL':<{title_width}}  "
            f"{'':>{len(started) if group['sessions'] else 5}}    "
            f"{'':<{stop_width}}  {_format_duration(group['total_seconds'])}"
        )


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
        return f"{hours}h {minutes:02}m {seconds:02}s"

    return f"{minutes}m {seconds:02}s"


def _format_time(value: str, include_date: bool = False) -> str:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    format_text = "%Y-%m-%d %H:%M" if include_date else "%H:%M"
    return timestamp.astimezone().strftime(format_text)


def _should_include_date(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
) -> bool:
    if date:
        return False

    if not start_date and not end_date:
        return False

    return (start_date or end_date) != (end_date or start_date)


if __name__ == "__main__":
    cli()
