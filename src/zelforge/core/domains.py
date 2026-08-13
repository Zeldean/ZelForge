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
    for domain in data["domains"]:
        domain.setdefault("code", domain.get("key"))
        domain.setdefault("key", domain.get("code"))
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


def get_domain_name(code: str | None) -> str:
    """Return the display name for a domain code."""
    if not code:
        return ""

    normalized_code = _normalize_code(code)
    domain = _find_domain(load_domains_data()["domains"], normalized_code)
    if not domain:
        return normalized_code

    return domain.get("name") or normalized_code


def resolve_domain_code(code: str) -> str:
    """Return a normalized active domain code or raise a clear error."""
    normalized_code = _normalize_code(code)
    domain = _require_domain(load_domains_data()["domains"], normalized_code)
    if domain.get("active") is False:
        raise ValueError(f"Domain is inactive: {normalized_code}")

    return domain["code"]


def add_domain(
    code: str,
    name: str | None = None,
    description: str = "",
) -> dict:
    """Add a user domain and return it."""
    normalized_code = _normalize_code(code)
    data = load_domains_data()
    if _find_domain(data["domains"], normalized_code):
        raise ValueError(f"Domain already exists: {normalized_code}")

    now = _now()
    domain = {
        "key": normalized_code,
        "code": normalized_code,
        "name": (name or normalized_code).strip(),
        "description": description.strip(),
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    data["domains"].append(domain)
    _save_domains_data(data)
    return domain


def rename_domain(code: str, new_code: str, name: str | None = None) -> dict:
    """Rename a domain code and optionally update its display name."""
    normalized_code = _normalize_code(code)
    normalized_new_code = _normalize_code(new_code)
    data = load_domains_data()
    domain = _require_domain(data["domains"], normalized_code)
    existing = _find_domain(data["domains"], normalized_new_code)
    if existing and existing is not domain:
        raise ValueError(f"Domain already exists: {normalized_new_code}")

    domain["key"] = normalized_new_code
    domain["code"] = normalized_new_code
    if name is not None:
        domain["name"] = name.strip() or normalized_new_code
    elif domain.get("name") == normalized_code:
        domain["name"] = normalized_new_code
    domain["updated_at"] = _now()

    if data.get("default_domain") == normalized_code:
        data["default_domain"] = normalized_new_code

    _save_domains_data(data)
    return domain


def set_domain_active(code: str, active: bool) -> dict:
    """Set whether a domain is active."""
    normalized_code = _normalize_code(code)
    data = load_domains_data()
    domain = _require_domain(data["domains"], normalized_code)
    domain["active"] = active
    domain["updated_at"] = _now()

    if not active and data.get("default_domain") == normalized_code:
        data["default_domain"] = None

    _save_domains_data(data)
    return domain


def remove_domain(code: str) -> bool:
    """Remove a domain. Returns whether it existed."""
    normalized_code = _normalize_code(code)
    data = load_domains_data()
    original_count = len(data["domains"])
    data["domains"] = [
        domain for domain in data["domains"] if domain.get("code") != normalized_code
    ]
    removed = len(data["domains"]) != original_count

    if data.get("default_domain") == normalized_code:
        data["default_domain"] = None

    if removed:
        _save_domains_data(data)

    return removed


def set_default_domain(code: str | None) -> str | None:
    """Set or clear the default domain."""
    data = load_domains_data()
    if code is None:
        data["default_domain"] = None
        _save_domains_data(data)
        return None

    normalized_code = _normalize_code(code)
    domain = _require_domain(data["domains"], normalized_code)
    if domain.get("active") is False:
        raise ValueError(f"Cannot set inactive domain as default: {normalized_code}")

    data["default_domain"] = normalized_code
    _save_domains_data(data)
    return normalized_code


def _save_domains_data(data: dict[str, Any]) -> dict[str, Any]:
    data["updated_at"] = _now()
    write_json(get_domains_path(), data)
    return data


def _make_data() -> dict[str, Any]:
    data = get_meta(SCHEMA_VERSION, DESCRIPTION)
    data["default_domain"] = None
    data["domains"] = []
    return data


def _find_domain(domains: list[dict], code: str) -> dict | None:
    for domain in domains:
        if domain.get("code") == code or domain.get("key") == code:
            return domain

    return None


def _require_domain(domains: list[dict], code: str) -> dict:
    domain = _find_domain(domains, code)
    if not domain:
        raise ValueError(f"Unknown domain: {code}")

    return domain


def _normalize_code(code: str) -> str:
    normalized = code.strip().lower()
    if not normalized:
        raise ValueError("Domain code cannot be blank")

    if any(character.isspace() for character in normalized):
        raise ValueError("Domain code cannot contain whitespace")

    return normalized


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
