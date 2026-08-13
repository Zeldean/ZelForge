from __future__ import annotations

import typer

from zelforge.core.domains import get_domain_name

from . import service
from .models import get_priority_label


cli = typer.Typer(help="Task commands.")
subtasks_app = typer.Typer(help="Subtask commands.")
cli.add_typer(subtasks_app, name="sub")


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
    priority: str = typer.Option(
        "2",
        "--priority",
        "-p",
        help="Task priority: 0 none, 1 low, 2 medium, 3 high, 4 urgent.",
    ),
    tag: list[str] = typer.Option([], "--tag", "-t", help="Task tag."),
    domain: str = typer.Option("", "--domain", help="Task domain code."),
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
    typer.echo(f"domain      {_domain_label(task.get('domain'))}")
    typer.echo(f"tags        {', '.join(task.get('tags', [])) or '-'}")
    typer.echo(f"created_at  {task['created_at']}")
    typer.echo(f"updated_at  {task['updated_at']}")
    typer.echo(f"description {task.get('description') or '-'}")
    _echo_subtasks(task.get("subtasks", []))


@cli.command()
def edit(
    task_ref: str,
    title: str | None = typer.Option(None, "--title", help="New task title."),
    description: str | None = typer.Option(None, "--description", "-d", help="New description."),
    priority: str | None = typer.Option(
        None,
        "--priority",
        "-p",
        help="New priority: 0 none, 1 low, 2 medium, 3 high, 4 urgent.",
    ),
    domain: str | None = typer.Option(None, "--domain", help="New domain code."),
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


@subtasks_app.command("add")
def add_subtask(task_ref: str, title: str) -> None:
    """Add a subtask to a task."""
    try:
        subtask = service.add_subtask(task_ref, title)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"created subtask {subtask['id'][:8]}: {subtask['title']}")


@subtasks_app.command("list")
def list_subtasks(
    task_ref: str,
    all_subtasks: bool = typer.Option(False, "--all", "-a", help="Show every status."),
) -> None:
    """List subtasks for a task."""
    try:
        subtasks = service.list_subtasks(task_ref, include_all=all_subtasks)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    if not subtasks:
        typer.echo("no subtasks")
        return

    for subtask in subtasks:
        typer.echo(_format_subtask_line(subtask))


@subtasks_app.command("edit")
def edit_subtask(
    task_ref: str,
    subtask_ref: str,
    title: str | None = typer.Option(None, "--title", help="New subtask title."),
    status: str | None = typer.Option(None, "--status", "-s", help="New subtask status."),
) -> None:
    """Edit an existing subtask."""
    try:
        subtask = service.update_subtask(
            task_ref=task_ref,
            subtask_ref=subtask_ref,
            title=title,
            status=status,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"updated subtask {subtask['id'][:8]}: {subtask['title']}")


@subtasks_app.command("done")
def done_subtask(task_ref: str, subtask_ref: str) -> None:
    """Mark a subtask done."""
    try:
        subtask = service.update_subtask(task_ref, subtask_ref, status="done")
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"done subtask {subtask['id'][:8]}: {subtask['title']}")


@subtasks_app.command("cancel")
def cancel_subtask(task_ref: str, subtask_ref: str) -> None:
    """Mark a subtask cancelled."""
    try:
        subtask = service.update_subtask(task_ref, subtask_ref, status="cancelled")
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"cancelled subtask {subtask['id'][:8]}: {subtask['title']}")


@subtasks_app.command("reopen")
def reopen_subtask(task_ref: str, subtask_ref: str) -> None:
    """Mark a subtask active again."""
    try:
        subtask = service.update_subtask(task_ref, subtask_ref, status="active")
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"reopened subtask {subtask['id'][:8]}: {subtask['title']}")


@subtasks_app.command("remove")
def remove_subtask(task_ref: str, subtask_ref: str) -> None:
    """Remove a subtask."""
    try:
        subtask = service.remove_subtask(task_ref, subtask_ref)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"removed subtask {subtask['id'][:8]}: {subtask['title']}")


@cli.command()
def tui() -> None:
    """Open the interactive task TUI."""
    from .tui import run

    run()


def _format_task_line(task: dict) -> str:
    tags = ",".join(task.get("tags", []))
    tag_text = f" [{tags}]" if tags else ""
    domain = _domain_label(task.get("domain"), empty="")
    domain_text = f" ({domain})" if domain else ""
    subtask_text = _subtask_summary(task.get("subtasks", []))
    return (
        f"{task['id'][:8]}  {task['status']:<9} "
        f"{get_priority_label(task.get('priority')):<7} "
        f"{task['title']}{domain_text}{tag_text}{subtask_text}"
    )


def _echo_subtasks(subtasks: list[dict]) -> None:
    typer.echo("subtasks")
    if not subtasks:
        typer.echo("  -")
        return

    for subtask in subtasks:
        typer.echo(f"  {_format_subtask_line(subtask)}")


def _format_subtask_line(subtask: dict) -> str:
    return f"{subtask['id'][:8]}  {subtask['status']:<9} {subtask['title']}"


def _domain_label(code: str | None, empty: str = "-") -> str:
    if not code:
        return empty

    return get_domain_name(code)


def _subtask_summary(subtasks: list[dict]) -> str:
    if not subtasks:
        return ""

    done = sum(1 for subtask in subtasks if subtask.get("status") == "done")
    total = len(subtasks)
    return f" [{done}/{total}]"


if __name__ == "__main__":
    cli()
