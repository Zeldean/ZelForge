from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zelforge.core.paths import get_state_dir
from zelforge.core.storage import ensure_dir, get_meta, read_json, write_json


STATE_NAME = "journal"
NOTES_FILE_NAME = "notes.json"
SCHEMA_VERSION = 1
DESCRIPTION = "ZelForge journal note storage."


def get_journal_dir() -> Path:
    """Return the journal module state directory."""
    return get_state_dir() / STATE_NAME


def get_notes_path() -> Path:
    """Return the note storage file path."""
    return get_journal_dir() / NOTES_FILE_NAME


def init() -> dict[str, str]:
    """Create journal storage if it does not already exist."""
    ensure_dir(get_journal_dir())

    if not get_notes_path().exists():
        write_json(get_notes_path(), _make_data())

    return {"status": "success"}


def load_notes_data() -> dict[str, Any]:
    """Load note storage, failing clearly if it has not been initialized."""
    notes_path = get_notes_path()
    if not notes_path.exists():
        raise FileNotFoundError(f"Journal storage does not exist: {notes_path}")

    data = read_json(notes_path)
    data.setdefault("notes", [])
    return data


def save_notes_data(data: dict[str, Any]) -> dict[str, Any]:
    """Save note storage and return the saved data."""
    data.setdefault("notes", [])
    data["updated_at"] = _now()
    write_json(get_notes_path(), data)
    return data


def _make_data() -> dict[str, Any]:
    data = get_meta(SCHEMA_VERSION, DESCRIPTION)
    data["notes"] = []
    return data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
