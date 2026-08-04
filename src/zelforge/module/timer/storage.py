"""Storage setup helpers for the timer module."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from zelforge.core.paths import get_state_dir
from zelforge.core.storage import (
    ensure_dir,
    ensure_parent_dir,
    read_json,
    write_json,
    get_meta,
)


STATE_NAME = "timer"
LOG_FILE_NAME = "log.txt"

# Each storage object maps to one JSON file with the same top-level array name.
_OBJECTS = {
    "timers": {
        "schema_version": 1,
        "description": "This is the list of all timers that can be used.",
    },
    "sessions": {
        "schema_version": 1,
        "description": "This is the list of all the sessions of the various timers.",
    },
}


def get_timer_dir() -> Path:
    """Return the timer module state directory."""
    return get_state_dir() / STATE_NAME


def get_log_path() -> Path:
    """Return the timer event log path."""
    return get_timer_dir() / LOG_FILE_NAME


def init() -> dict:
    """Create the basic timer storage files if they do not already exist."""
    ensure_dir(get_timer_dir())

    for name in _OBJECTS:
        _create_object(name)

    ensure_parent_dir(get_log_path())
    if not get_log_path().exists():
        get_log_path().write_text("", encoding="utf-8")

    return {"status": "success"}


def get_timers() -> list[dict]:
    """Return all timer definitions."""
    data = _load_object("timers")
    return data["timers"]


def get_sessions() -> list[dict]:
    """Return all timer sessions."""
    data = _load_object("sessions")
    return data["sessions"]


def get_sessions_data() -> dict:
    """Return the full sessions storage object."""
    return _load_object("sessions")


def save_sessions_data(data: dict) -> Path:
    """Save the full sessions storage object."""
    return _save_object("sessions", data)


def add_timer(
    name: str,
    description: str = "",
    code: str | None = None,
    domain: str = "",
    tags: list[str] | None = None,
    archived: bool = False,
) -> dict:
    """Add one timer definition and return the new timer."""
    _require_text(name, "Timer name")
    data = _load_object("timers")

    timer = {
        "id": str(uuid4()),
        "code": code,
        "name": name,
        "description": description,
        "archived": archived,
        "tags": tags or [],
        "domain": domain,
    }

    data["timers"].append(timer)
    _save_object("timers", data)

    return timer


def add_session(
    timer_id: str,
    title: str,
    started_at: str | None = None,
    stopped_at: str | None = None,
    duration_seconds: int | None = None,
) -> dict:
    """Add one timer session and return the new session."""
    _require_text(timer_id, "Timer id")
    _require_text(title, "Session title")

    if duration_seconds is not None and duration_seconds < 0:
        raise ValueError("Session duration cannot be negative")

    if not _timer_exists(timer_id):
        raise ValueError(f"Timer does not exist: {timer_id}")

    data = _load_object("sessions")

    session = {
        "id": str(uuid4()),
        "timer_id": timer_id,
        "title": title,
        "started_at": started_at or _now(),
        "stopped_at": stopped_at,
        "duration_seconds": duration_seconds,
    }

    data["sessions"].append(session)
    _save_object("sessions", data)

    return session


def append_log_event(event: dict) -> dict:
    """Append one JSON event to the timer text log."""
    ensure_parent_dir(get_log_path())

    with get_log_path().open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, sort_keys=True))
        file.write("\n")

    return event


def read_log_events() -> list[dict]:
    """Read timer log events from the text log."""
    log_path = get_log_path()
    if not log_path.exists():
        return []

    events = []
    for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue

        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid timer log line {line_number}: {error.msg}") from error

    return events


def write_log_events(events: list[dict]) -> Path:
    """Rewrite the timer text log with JSON events."""
    ensure_parent_dir(get_log_path())

    with get_log_path().open("w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event, sort_keys=True))
            file.write("\n")

    return get_log_path()


def _get_object_config(name: str) -> dict:
    """Return the config for a known timer storage object."""
    if name not in _OBJECTS:
        allowed = ", ".join(_OBJECTS)
        raise ValueError(f"Unknown timer storage object '{name}'. Use one of: {allowed}")

    return _OBJECTS[name]


def _get_object_path(name: str) -> Path:
    """Return the JSON file path for a known timer storage object."""
    _get_object_config(name)
    return get_timer_dir() / f"{name}.json"


def _load_object(name: str) -> dict:
    """Load a timer storage object, failing if the file is missing."""
    object_path = _get_object_path(name)

    if not object_path.exists():
        raise FileNotFoundError(f"Timer storage object does not exist: {object_path}")

    return read_json(object_path)


def _save_object(name: str, data: dict) -> Path:
    """Save a timer storage object and refresh its update timestamp."""
    data["updated_at"] = _now()
    return write_json(_get_object_path(name), data)


def _timer_exists(timer_id: str) -> bool:
    """Return whether a timer definition exists for the given id."""
    return any(timer.get("id") == timer_id for timer in get_timers())


def _require_text(value: str, label: str) -> None:
    """Raise a clear error when a required text value is blank."""
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _now() -> str:
    """Return the current UTC timestamp for storage."""
    return datetime.now(timezone.utc).isoformat()





def make_data(name: str, schema_version: int, description: str) -> dict:
    """Build the initial JSON structure for one timer storage file."""
    data = get_meta(schema_version, description)
    data[name] = []

    return data


def _create_object(name: str) -> dict:
    """Create one timer JSON file, unless it already exists."""
    config = _get_object_config(name)
    object_path = _get_object_path(name)

    if not object_path.exists():
        data = make_data(name, config["schema_version"], config["description"])
        write_json(path=object_path, data=data)
        return data

    return {"message": f"Object named {name} already exists"}
