from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from . import storage


def start_timer(timer_ref: str, title: str | None = None) -> dict:
    """Start a timer by appending a start event to the live log."""
    timer = find_timer(timer_ref)
    active_sessions = get_active_sessions()
    if active_sessions:
        active = active_sessions[0]
        raise ValueError(
            f"Timer already active: {active['title']} ({active['session_id'][:8]})"
        )

    event = {
        "event": "start",
        "session_id": str(uuid4()),
        "timer_id": timer["id"],
        "timer_code": timer.get("code"),
        "title": title or timer["name"],
        "created_at": _now(),
    }
    storage.append_log_event(event)

    return {
        "session_id": event["session_id"],
        "timer": timer,
        "title": event["title"],
        "started_at": event["created_at"],
    }


def stop_timer() -> dict:
    """Stop the active timer by appending a stop event to the live log."""
    active_sessions = get_active_sessions()
    if not active_sessions:
        raise ValueError("No active timer session")

    if len(active_sessions) > 1:
        active_ids = ", ".join(session["session_id"][:8] for session in active_sessions)
        raise ValueError(f"Multiple active timer sessions found: {active_ids}")

    active = active_sessions[0]
    stopped_at = _now()
    event = {
        "event": "stop",
        "session_id": active["session_id"],
        "created_at": stopped_at,
    }
    storage.append_log_event(event)

    return {
        **active,
        "stopped_at": stopped_at,
        "duration_seconds": _duration_seconds(active["started_at"], stopped_at),
    }


def get_active_sessions() -> list[dict]:
    """Return active sessions reconstructed from the event log."""
    active_by_id: dict[str, dict] = {}

    for event in storage.read_log_events():
        event_name = event.get("event")
        session_id = event.get("session_id")
        if not session_id:
            continue

        if event_name == "start":
            active_by_id[session_id] = {
                "session_id": session_id,
                "timer_id": event.get("timer_id"),
                "timer_code": event.get("timer_code"),
                "title": event.get("title") or "",
                "started_at": event.get("created_at"),
            }
        elif event_name == "stop":
            active_by_id.pop(session_id, None)

    return list(active_by_id.values())


def find_timer(timer_ref: str) -> dict:
    """Find a timer by UUID id or short code."""
    _require_text(timer_ref, "Timer")

    for timer in storage.get_timers():
        if timer.get("id") == timer_ref or timer.get("code") == timer_ref:
            return timer

    raise ValueError(f"Unknown timer: {timer_ref}")


def _duration_seconds(started_at: str, stopped_at: str) -> int:
    started = datetime.fromisoformat(started_at)
    stopped = datetime.fromisoformat(stopped_at)
    return int((stopped - started).total_seconds())


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
