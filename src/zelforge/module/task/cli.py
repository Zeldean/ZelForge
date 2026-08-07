from __future__ import annotations

import typer

from . import service
from .models import get_priority_label


cli = typer.Typer(help="Task commands.")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Manage tasks."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@cli.command()
def init() -> None:
    """Create task storage files."""
    result = service.init()
    typer.echo(result["status"])


@cli.command()
def add(
    title: str,
    description: str = typer.Option("", "--description", "-d", help="Task description."),
    priority: str = typer.Option("medium", "--priority", "-p", help="Task priority."),
    tag: list[str] = typer.Option([], "--tag", "-t", help="Task tag."),
    domain: str = typer.Option("", "--domain", help="Task domain or project."),
) -> None:
    """Create a new task."""
    try:
        task = service.create_task(
            title=title,
            description=description,
            priority=priority,
            tags=tag,
            domain=domain,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"created task {task['id'][:8]}: {task['title']}")


@cli.command("list")
def list_tasks(
    status: str = typer.Option("active", "--status", "-s", help="Status to show."),
    all_tasks: bool = typer.Option(False, "--all", "-a", help="Show every status."),
) -> None:
    """List tasks."""
    try:
        tasks = service.list_tasks(status=status, include_all=all_tasks)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    if not tasks:
        typer.echo("no tasks")
        return

    for task in tasks:
        typer.echo(_format_task_line(task))


@cli.command()
def show(task_ref: str) -> None:
    """Show one task."""
    try:
        task = service.get_task(task_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"id          {task['id']}")
    typer.echo(f"title       {task['title']}")
    typer.echo(f"status      {task['status']}")
    typer.echo(f"priority    {get_priority_label(task.get('priority'))}")
    typer.echo(f"domain      {task.get('domain') or '-'}")
    typer.echo(f"tags        {', '.join(task.get('tags', [])) or '-'}")
    typer.echo(f"created_at  {task['created_at']}")
    typer.echo(f"updated_at  {task['updated_at']}")
    typer.echo(f"description {task.get('description') or '-'}")


@cli.command()
def edit(
    task_ref: str,
    title: str | None = typer.Option(None, "--title", help="New task title."),
    description: str | None = typer.Option(None, "--description", "-d", help="New description."),
    priority: str | None = typer.Option(None, "--priority", "-p", help="New priority."),
    domain: str | None = typer.Option(None, "--domain", help="New domain or project."),
    tag: list[str] | None = typer.Option(None, "--tag", "-t", help="Replace task tags."),
    status: str | None = typer.Option(None, "--status", "-s", help="New task status."),
) -> None:
    """Edit an existing task."""
    try:
        task = service.update_task(
            task_ref=task_ref,
            title=title,
            description=description,
            priority=priority,
            domain=domain,
            tags=tag,
            status=status,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"updated task {task['id'][:8]}: {task['title']}")


@cli.command()
def done(task_ref: str) -> None:
    """Mark a task done."""
    try:
        task = service.mark_done(task_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"done task {task['id'][:8]}: {task['title']}")


@cli.command()
def cancel(task_ref: str) -> None:
    """Mark a task cancelled."""
    try:
        task = service.cancel_task(task_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"cancelled task {task['id'][:8]}: {task['title']}")


@cli.command()
def reopen(task_ref: str) -> None:
    """Mark a task active again."""
    try:
        task = service.reopen_task(task_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"reopened task {task['id'][:8]}: {task['title']}")


@cli.command()
def tui() -> None:
    """Open the interactive task TUI."""
    from .tui import run

    run()


def _format_task_line(task: dict) -> str:
    tags = ",".join(task.get("tags", []))
    tag_text = f" [{tags}]" if tags else ""
    domain = task.get("domain")
    domain_text = f" ({domain})" if domain else ""
    return (
        f"{task['id'][:8]}  {task['status']:<9} "
        f"{get_priority_label(task.get('priority')):<7} "
        f"{task['title']}{domain_text}{tag_text}"
    )


if __name__ == "__main__":
    cli()
