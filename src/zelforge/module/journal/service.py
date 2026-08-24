from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from zelforge.core.domains import get_default_domain, resolve_domain_code

from . import storage
from .models import extract_inline_tags, normalize_tags


def init() -> dict[str, str]:
    """Initialize journal storage."""
    return storage.init()


def create_note(body: str, tags: list[str] | None = None, domain: str = "") -> dict:
    """Create and return a journal note."""
    _require_text(body, "Note body")

    data = _load_or_init()
    now = _now()
    note = {
        "id": str(uuid4()),
        "body": body.strip(),
        "tags": normalize_tags(tags),
        "domain": _resolve_domain(domain),
        "created_at": now,
        "updated_at": now,
    }

    data["notes"].append(note)
    storage.save_notes_data(data)
    return note


def list_notes() -> list[dict]:
    """Return all journal notes, oldest first."""
    return _load_or_init()["notes"]


def get_note(note_ref: str) -> dict:
    """Return one note by id prefix or exact id."""
    return _find_note(_load_or_init()["notes"], note_ref)


def list_known_tags() -> list[str]:
    """Return known tags (inline `#tags` and explicit tags), most used first."""
    counts: Counter[str] = Counter()
    for note in _load_or_init()["notes"]:
        counts.update(extract_inline_tags(note.get("body", "")))
        counts.update(note.get("tags", []))

    return [tag for tag, _ in counts.most_common()]


def _load_or_init() -> dict:
    try:
        return storage.load_notes_data()
    except FileNotFoundError:
        storage.init()
        return storage.load_notes_data()


def _find_note(notes: list[dict], note_ref: str) -> dict:
    _require_text(note_ref, "Note id")
    matches = [
        note
        for note in notes
        if note.get("id") == note_ref or note.get("id", "").startswith(note_ref)
    ]

    if not matches:
        raise ValueError(f"Unknown note: {note_ref}")

    if len(matches) > 1:
        raise ValueError(f"Note id is ambiguous: {note_ref}")

    return matches[0]


def _resolve_domain(domain: str) -> str:
    if domain.strip():
        return resolve_domain_code(domain)

    return get_default_domain() or ""


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
