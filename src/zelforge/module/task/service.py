from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from zelforge.core.domains import get_default_domain, resolve_domain_code

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
        "domain": _resolve_domain(domain),
        "subtasks": [],
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
    tasks = [_normalize_task(task) for task in data["tasks"]]

    if include_all:
        return tasks

    if status is None:
        return tasks

    normalized = validate_status(status)
    return [task for task in tasks if task.get("status") == normalized]


def get_task(task_ref: str) -> dict:
    """Return one task by id prefix or exact id."""
    return _normalize_task(_find_task(_load_or_init()["tasks"], task_ref))


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
    _normalize_task(task)

    if title is not None:
        _require_text(title, "Task title")
        task["title"] = title.strip()

    if description is not None:
        task["description"] = description.strip()

    if priority is not None:
        task["priority"] = validate_priority(priority)

    if domain is not None:
        task["domain"] = _resolve_domain(domain)

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


def add_subtask(task_ref: str, title: str) -> dict:
    """Create a subtask under a parent task."""
    _require_text(title, "Subtask title")
    data = _load_or_init()
    task = _normalize_task(_find_task(data["tasks"], task_ref))
    now = _now()
    subtask = {
        "id": str(uuid4()),
        "title": title.strip(),
        "status": DEFAULT_STATUS,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "cancelled_at": None,
    }
    task["subtasks"].append(subtask)
    task["updated_at"] = now
    storage.save_tasks_data(data)
    return subtask


def update_subtask(
    task_ref: str,
    subtask_ref: str,
    title: str | None = None,
    status: str | None = None,
) -> dict:
    """Edit one subtask and return it."""
    data = _load_or_init()
    task = _normalize_task(_find_task(data["tasks"], task_ref))
    subtask = _find_subtask(task, subtask_ref)

    if title is not None:
        _require_text(title, "Subtask title")
        subtask["title"] = title.strip()

    if status is not None:
        _set_status(subtask, status)

    now = _now()
    subtask["updated_at"] = now
    task["updated_at"] = now
    storage.save_tasks_data(data)
    return subtask


def remove_subtask(task_ref: str, subtask_ref: str) -> dict:
    """Remove one subtask and return it."""
    data = _load_or_init()
    task = _normalize_task(_find_task(data["tasks"], task_ref))
    subtask = _find_subtask(task, subtask_ref)
    task["subtasks"] = [
        item for item in task["subtasks"] if item.get("id") != subtask.get("id")
    ]
    task["updated_at"] = _now()
    storage.save_tasks_data(data)
    return subtask


def list_subtasks(task_ref: str, include_all: bool = False) -> list[dict]:
    """Return subtasks for a parent task."""
    task = get_task(task_ref)
    subtasks = task["subtasks"]
    if include_all:
        return subtasks

    return [subtask for subtask in subtasks if subtask.get("status") == DEFAULT_STATUS]


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


def _find_subtask(task: dict, subtask_ref: str) -> dict:
    _require_text(subtask_ref, "Subtask id")
    matches = [
        subtask
        for subtask in task.get("subtasks", [])
        if subtask.get("id") == subtask_ref
        or subtask.get("id", "").startswith(subtask_ref)
    ]

    if not matches:
        raise ValueError(f"Unknown subtask: {subtask_ref}")

    if len(matches) > 1:
        raise ValueError(f"Subtask id is ambiguous: {subtask_ref}")

    return matches[0]


def _normalize_task(task: dict) -> dict:
    task.setdefault("subtasks", [])
    for subtask in task["subtasks"]:
        subtask.setdefault("status", DEFAULT_STATUS)
        subtask.setdefault("created_at", task.get("created_at"))
        subtask.setdefault("updated_at", subtask.get("created_at"))
        subtask.setdefault("completed_at", None)
        subtask.setdefault("cancelled_at", None)

    return task


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


def _resolve_domain(domain: str) -> str:
    if domain.strip():
        return resolve_domain_code(domain)

    return get_default_domain() or ""


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
