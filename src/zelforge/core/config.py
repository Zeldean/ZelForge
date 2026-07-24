from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import get_config_dir
from .storage import get_meta, read_json, write_json


CONFIG_FILE_NAME = "config.json"
SCHEMA_VERSION = 1
DESCRIPTION = "ZelForge user configuration."


def get_config_path() -> Path:
    """Return the main user config file path."""
    return get_config_dir() / CONFIG_FILE_NAME


def default_config() -> dict[str, Any]:
    """Return a fresh default config document."""
    data = get_meta(SCHEMA_VERSION, DESCRIPTION)
    data["paths"] = {}
    data["settings"] = {}
    return data


def init_config() -> dict[str, Any]:
    """Create the config file if missing and return its current content."""
    config_path = get_config_path()
    if config_path.exists():
        return load_config()

    data = default_config()
    write_json(config_path, data)
    return data


def load_config() -> dict[str, Any]:
    """Load config, returning a default document when no config exists."""
    data = read_json(get_config_path(), default_config())
    data.setdefault("paths", {})
    data.setdefault("settings", {})
    return data


def save_config(data: dict[str, Any]) -> dict[str, Any]:
    """Save config and return the saved document."""
    data.setdefault("paths", {})
    data.setdefault("settings", {})
    data["updated_at"] = _now()
    write_json(get_config_path(), data)
    return data


def get_path(key: str) -> str | None:
    """Return a module path value."""
    return load_config()["paths"].get(key)


def set_path(key: str, value: str) -> dict[str, Any]:
    """Set a module path value."""
    _require_key(key)
    _require_value(value, "Path")

    data = load_config()
    data["paths"][key] = str(Path(value).expanduser())
    return save_config(data)


def unset_path(key: str) -> bool:
    """Remove a module path value and return whether it existed."""
    _require_key(key)

    data = load_config()
    existed = key in data["paths"]
    data["paths"].pop(key, None)
    save_config(data)
    return existed


def get_setting(key: str) -> Any:
    """Return a general setting value."""
    return load_config()["settings"].get(key)


def set_setting(key: str, value: str) -> dict[str, Any]:
    """Set a general setting value."""
    _require_key(key)
    _require_value(value, "Setting")

    data = load_config()
    data["settings"][key] = value
    return save_config(data)


def unset_setting(key: str) -> bool:
    """Remove a general setting value and return whether it existed."""
    _require_key(key)

    data = load_config()
    existed = key in data["settings"]
    data["settings"].pop(key, None)
    save_config(data)
    return existed


def _require_key(key: str) -> None:
    if not key.strip():
        raise ValueError("Key cannot be blank")


def _require_value(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} value cannot be blank")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
