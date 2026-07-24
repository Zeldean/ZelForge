from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .paths import get_cache_dir, get_config_dir, get_state_dir


def ensure_dir(path: Path) -> Path:
    """Create a directory if needed and return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent_dir(path: Path) -> Path:
    """Create the parent directory for a file path and return the file path."""
    ensure_dir(path.parent)
    return path


def ensure_base_dirs() -> None:
    """Create the main directories ZelForge uses for runtime files."""
    ensure_dir(get_state_dir())
    ensure_dir(get_config_dir())
    ensure_dir(get_cache_dir())


def read_text(path: Path, default: str = "") -> str:
    """Read a text file, returning the default when it does not exist."""
    if not path.exists():
        return default

    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> Path:
    """Write a text file, creating parent directories first."""
    ensure_parent_dir(path)
    path.write_text(text, encoding="utf-8")
    return path


def read_json(path: Path, default: Any = None) -> Any:
    """Read a JSON file, returning the default when it does not exist."""
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> Path:
    """Write a JSON file, creating parent directories first."""
    ensure_parent_dir(path)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")

    return path


def _now() -> str:
    """Return the current UTC timestamp for storage metadata."""
    return datetime.now(timezone.utc).isoformat()


def get_meta(schema_version: int, description: str) -> dict:
    """Return standard metadata for a JSON storage file."""
    now = _now()

    return {
        "id": str(uuid4()),
        "schema_version": schema_version,
        "description": description,
        "created_at": now,
        "updated_at": now,
    }
