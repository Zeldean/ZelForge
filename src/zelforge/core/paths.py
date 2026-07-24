import os
from pathlib import Path


APP_DIR_NAME = "zelforge"


def _path_from_env(name: str) -> Path | None:
    """Return an optional path override from an environment variable."""
    value = os.getenv(name)
    if not value:
        return None

    # Allows users to write paths like "~/zel-state" in their shell config.
    return Path(value).expanduser()


def get_state_dir() -> Path:
    """Return the directory for user state that changes while the app runs."""
    override = _path_from_env("ZEL_STATE_DIR")
    if override:
        return override

    return Path.home() / ".local" / "state" / APP_DIR_NAME


def get_config_dir() -> Path:
    """Return the directory for user-editable configuration files."""
    override = _path_from_env("ZEL_CONFIG_DIR")
    if override:
        return override

    return Path.home() / ".config" / APP_DIR_NAME


def get_cache_dir() -> Path:
    """Return the directory for disposable cached files."""
    override = _path_from_env("ZEL_CACHE_DIR")
    if override:
        return override

    return Path.home() / ".cache" / APP_DIR_NAME
