from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from . import storage
from .models import DEFAULT_PRIORITY, DEFAULT_STATUS, validate_priority, validate_status


def init() -> dict[str, str]:
    """Initialize task storage."""
    return storage.init()


def create_task(
    title: str,
    description: str = "",
    priority: int | str = DEFAULT_PRIORITY,
    tags: list[str] | None = None,
    domain: str = "",
) -> dict:
    """Create and return a task."""
    _require_text(title, "Task title")

    data = _load_or_init()
    now = _now()
    task = {
        "id": str(uuid4()),
        "title": title.strip(),
        "description": description.strip(),
        "status": DEFAULT_STATUS,
        "priority": validate_priority(priority),
        "tags": tags or [],
        "domain": domain.strip(),
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "cancelled_at": None,
    }

    data["tasks"].append(task)
    storage.save_tasks_data(data)
    return task


def list_tasks(status: str | None = "active", include_all: bool = False) -> list[dict]:
    """Return tasks filtered by status unless include_all is true."""
    data = _load_or_init()
    tasks = data["tasks"]

    if include_all:
        return tasks

    if status is None:
        return tasks

    normalized = validate_status(status)
    return [task for task in tasks if task.get("status") == normalized]


def get_task(task_ref: str) -> dict:
    """Return one task by id prefix or exact id."""
    return _find_task(_load_or_init()["tasks"], task_ref)


def update_task(
    task_ref: str,
    title: str | None = None,
    description: str | None = None,
    priority: int | str | None = None,
    domain: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
) -> dict:
    """Edit one task and return the updated task."""
    data = _load_or_init()
    task = _find_task(data["tasks"], task_ref)

    if title is not None:
        _require_text(title, "Task title")
        task["title"] = title.strip()

    if description is not None:
        task["description"] = description.strip()

    if priority is not None:
        task["priority"] = validate_priority(priority)

    if domain is not None:
        task["domain"] = domain.strip()

    if tags is not None:
        task["tags"] = tags

    if status is not None:
        _set_status(task, status)

    task["updated_at"] = _now()
    storage.save_tasks_data(data)
    return task


def mark_done(task_ref: str) -> dict:
    """Mark a task done."""
    return update_task(task_ref, status="done")


def cancel_task(task_ref: str) -> dict:
    """Mark a task cancelled."""
    return update_task(task_ref, status="cancelled")


def reopen_task(task_ref: str) -> dict:
    """Mark a task active again."""
    return update_task(task_ref, status="active")


def _load_or_init() -> dict:
    try:
        return storage.load_tasks_data()
    except FileNotFoundError:
        storage.init()
        return storage.load_tasks_data()


def _find_task(tasks: list[dict], task_ref: str) -> dict:
    _require_text(task_ref, "Task id")
    matches = [
        task
        for task in tasks
        if task.get("id") == task_ref or task.get("id", "").startswith(task_ref)
    ]

    if not matches:
        raise ValueError(f"Unknown task: {task_ref}")

    if len(matches) > 1:
        raise ValueError(f"Task id is ambiguous: {task_ref}")

    return matches[0]


def _set_status(task: dict, status: str) -> None:
    normalized = validate_status(status)
    task["status"] = normalized

    now = _now()
    if normalized == "done":
        task["completed_at"] = task.get("completed_at") or now
        task["cancelled_at"] = None
    elif normalized == "cancelled":
        task["cancelled_at"] = task.get("cancelled_at") or now
        task["completed_at"] = None
    else:
        task["completed_at"] = None
        task["cancelled_at"] = None


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
