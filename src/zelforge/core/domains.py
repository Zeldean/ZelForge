from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import get_state_dir
from .storage import ensure_dir, get_meta, read_json, write_json


SCHEMA_VERSION = 1
DESCRIPTION = "ZelForge shared user domains."
DOMAINS_FILE_NAME = "domains.json"


def get_domains_path() -> Path:
    """Return the shared domains storage path."""
    return get_state_dir() / DOMAINS_FILE_NAME


def init_domains() -> dict[str, Any]:
    """Create shared domain storage if it does not already exist."""
    ensure_dir(get_state_dir())
    if not get_domains_path().exists():
        write_json(get_domains_path(), _make_data())

    return load_domains_data()


def load_domains_data() -> dict[str, Any]:
    """Load shared domain storage, creating it on first use."""
    data = read_json(get_domains_path())
    if data is None:
        return init_domains()

    data.setdefault("default_domain", None)
    data.setdefault("domains", [])
    return data


def list_domains(include_inactive: bool = False) -> list[dict]:
    """Return configured domains."""
    domains = load_domains_data()["domains"]
    if include_inactive:
        return domains

    return [domain for domain in domains if domain.get("active") is not False]


def get_default_domain() -> str | None:
    """Return the default domain key, if one is configured."""
    return load_domains_data().get("default_domain")


def add_domain(
    key: str,
    name: str | None = None,
    description: str = "",
) -> dict:
    """Add a user domain and return it."""
    normalized_key = _normalize_key(key)
    data = load_domains_data()
    if _find_domain(data["domains"], normalized_key):
        raise ValueError(f"Domain already exists: {normalized_key}")

    now = _now()
    domain = {
        "key": normalized_key,
        "name": (name or normalized_key).strip(),
        "description": description.strip(),
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    data["domains"].append(domain)
    _save_domains_data(data)
    return domain


def rename_domain(key: str, new_key: str, name: str | None = None) -> dict:
    """Rename a domain key and optionally update its display name."""
    normalized_key = _normalize_key(key)
    normalized_new_key = _normalize_key(new_key)
    data = load_domains_data()
    domain = _require_domain(data["domains"], normalized_key)
    existing = _find_domain(data["domains"], normalized_new_key)
    if existing and existing is not domain:
        raise ValueError(f"Domain already exists: {normalized_new_key}")

    domain["key"] = normalized_new_key
    if name is not None:
        domain["name"] = name.strip() or normalized_new_key
    elif domain.get("name") == normalized_key:
        domain["name"] = normalized_new_key
    domain["updated_at"] = _now()

    if data.get("default_domain") == normalized_key:
        data["default_domain"] = normalized_new_key

    _save_domains_data(data)
    return domain


def set_domain_active(key: str, active: bool) -> dict:
    """Set whether a domain is active."""
    normalized_key = _normalize_key(key)
    data = load_domains_data()
    domain = _require_domain(data["domains"], normalized_key)
    domain["active"] = active
    domain["updated_at"] = _now()

    if not active and data.get("default_domain") == normalized_key:
        data["default_domain"] = None

    _save_domains_data(data)
    return domain


def remove_domain(key: str) -> bool:
    """Remove a domain. Returns whether it existed."""
    normalized_key = _normalize_key(key)
    data = load_domains_data()
    original_count = len(data["domains"])
    data["domains"] = [
        domain for domain in data["domains"] if domain.get("key") != normalized_key
    ]
    removed = len(data["domains"]) != original_count

    if data.get("default_domain") == normalized_key:
        data["default_domain"] = None

    if removed:
        _save_domains_data(data)

    return removed


def set_default_domain(key: str | None) -> str | None:
    """Set or clear the default domain."""
    data = load_domains_data()
    if key is None:
        data["default_domain"] = None
        _save_domains_data(data)
        return None

    normalized_key = _normalize_key(key)
    domain = _require_domain(data["domains"], normalized_key)
    if domain.get("active") is False:
        raise ValueError(f"Cannot set inactive domain as default: {normalized_key}")

    data["default_domain"] = normalized_key
    _save_domains_data(data)
    return normalized_key


def _save_domains_data(data: dict[str, Any]) -> dict[str, Any]:
    data["updated_at"] = _now()
    write_json(get_domains_path(), data)
    return data


def _make_data() -> dict[str, Any]:
    data = get_meta(SCHEMA_VERSION, DESCRIPTION)
    data["default_domain"] = None
    data["domains"] = []
    return data


def _find_domain(domains: list[dict], key: str) -> dict | None:
    for domain in domains:
        if domain.get("key") == key:
            return domain

    return None


def _require_domain(domains: list[dict], key: str) -> dict:
    domain = _find_domain(domains, key)
    if not domain:
        raise ValueError(f"Unknown domain: {key}")

    return domain


def _normalize_key(key: str) -> str:
    normalized = key.strip().lower()
    if not normalized:
        raise ValueError("Domain key cannot be blank")

    if any(character.isspace() for character in normalized):
        raise ValueError("Domain key cannot contain whitespace")

    return normalized


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
