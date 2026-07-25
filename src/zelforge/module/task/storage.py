from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zelforge.core.paths import get_state_dir
from zelforge.core.storage import ensure_dir, get_meta, read_json, write_json


STATE_NAME = "task"
TASKS_FILE_NAME = "tasks.json"
SCHEMA_VERSION = 1
DESCRIPTION = "ZelForge task storage."


def get_task_dir() -> Path:
    """Return the task module state directory."""
    return get_state_dir() / STATE_NAME


def get_tasks_path() -> Path:
    """Return the task storage file path."""
    return get_task_dir() / TASKS_FILE_NAME


def init() -> dict[str, str]:
    """Create task storage if it does not already exist."""
    ensure_dir(get_task_dir())

    if not get_tasks_path().exists():
        write_json(get_tasks_path(), _make_data())

    return {"status": "success"}


def load_tasks_data() -> dict[str, Any]:
    """Load task storage, failing clearly if it has not been initialized."""
    task_path = get_tasks_path()
    if not task_path.exists():
        raise FileNotFoundError(f"Task storage does not exist: {task_path}")

    data = read_json(task_path)
    data.setdefault("tasks", [])
    return data


def save_tasks_data(data: dict[str, Any]) -> dict[str, Any]:
    """Save task storage and return the saved data."""
    data.setdefault("tasks", [])
    data["updated_at"] = _now()
    write_json(get_tasks_path(), data)
    return data


def _make_data() -> dict[str, Any]:
    data = get_meta(SCHEMA_VERSION, DESCRIPTION)
    data["tasks"] = []
    return data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
