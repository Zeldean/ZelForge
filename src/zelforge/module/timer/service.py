from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from . import storage


def start_timer(timer_ref: str, title: str | None = None) -> dict:
    """Start a timer by appending a start event to the live log."""
    timer = find_timer(timer_ref)
    active = get_active_session_for_timer(timer["id"])
    if active:
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


def stop_timer(timer_ref: str) -> dict:
    """Stop one timer by appending a stop event to the live log."""
    timer = find_timer(timer_ref)
    active = get_active_session_for_timer(timer["id"])
    if not active:
        raise ValueError(f"No active session for timer: {timer_ref}")

    stopped_at = _now()
    event = {
        "event": "stop",
        "session_id": active["session_id"],
        "created_at": stopped_at,
    }
    storage.append_log_event(event)

    return {
        **active,
        "timer": timer,
        "stopped_at": stopped_at,
        "duration_seconds": _duration_seconds(active["started_at"], stopped_at),
    }


def save_closed_sessions() -> dict:
    """Promote old closed log sessions into permanent session storage."""
    events = storage.read_log_events()
    closed_sessions = _closed_sessions_from_events(events)
    cutoff_date = datetime.now(timezone.utc).date()
    invalid_sessions = [
        session
        for session in closed_sessions
        if session["duration_seconds"] < 0
    ]
    promotable = [
        session
        for session in closed_sessions
        if (
            session["duration_seconds"] >= 0
            and _parse_timestamp(session["started_at"]).date() < cutoff_date
        )
    ]

    if not promotable:
        return {
            "saved": 0,
            "skipped_invalid": len(invalid_sessions),
            "remaining_events": len(events),
            "active": len(get_active_sessions()),
        }

    sessions_data = storage.get_sessions_data()
    existing_ids = {session.get("id") for session in sessions_data["sessions"]}
    promoted_session_ids = set()
    saved = 0

    for session in promotable:
        promoted_session_ids.add(session["id"])
        if session["id"] in existing_ids:
            continue

        sessions_data["sessions"].append(session)
        existing_ids.add(session["id"])
        saved += 1

    storage.save_sessions_data(sessions_data)

    remaining_events = [
        event
        for event in events
        if event.get("session_id") not in promoted_session_ids
    ]
    storage.write_log_events(remaining_events)

    return {
        "saved": saved,
        "promoted": len(promotable),
        "skipped_invalid": len(invalid_sessions),
        "removed_events": len(events) - len(remaining_events),
        "remaining_events": len(remaining_events),
        "active": len(_active_sessions_from_events(remaining_events)),
    }


def get_today_active_sessions(timer_ref: str | None = None) -> list[dict]:
    """Return active sessions that started during the current UTC day."""
    timer_filter = find_timer(timer_ref)["id"] if timer_ref else None
    timers_by_id = {timer["id"]: timer for timer in storage.get_timers()}
    today = datetime.now(timezone.utc).date()
    sessions = []

    for session in get_active_sessions():
        started_at = session.get("started_at")
        if not started_at:
            continue

        if _parse_timestamp(started_at).date() != today:
            continue

        if timer_filter and session.get("timer_id") != timer_filter:
            continue

        timer = timers_by_id.get(session.get("timer_id"), {})
        sessions.append(
            {
                **session,
                "timer": timer,
                "elapsed_seconds": _duration_seconds(started_at, _now()),
            }
        )

    return sorted(sessions, key=lambda session: session["started_at"])


def get_active_sessions() -> list[dict]:
    """Return active sessions reconstructed from the event log."""
    return _active_sessions_from_events(storage.read_log_events())


def _active_sessions_from_events(events: list[dict]) -> list[dict]:
    active_by_id: dict[str, dict] = {}

    for event in events:
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


def _closed_sessions_from_events(events: list[dict]) -> list[dict]:
    starts_by_id: dict[str, dict] = {}
    closed_sessions = []

    for event in events:
        event_name = event.get("event")
        session_id = event.get("session_id")
        if not session_id:
            continue

        if event_name == "start":
            starts_by_id[session_id] = event
        elif event_name == "stop":
            start_event = starts_by_id.pop(session_id, None)
            if not start_event:
                continue

            started_at = start_event["created_at"]
            stopped_at = event["created_at"]
            closed_sessions.append(
                {
                    "id": session_id,
                    "timer_id": start_event["timer_id"],
                    "title": start_event.get("title") or "",
                    "started_at": started_at,
                    "stopped_at": stopped_at,
                    "duration_seconds": _duration_seconds(started_at, stopped_at),
                }
            )

    return closed_sessions


def get_active_session_for_timer(timer_id: str) -> dict | None:
    """Return the active session for one timer, if it has one."""
    matches = [
        session
        for session in get_active_sessions()
        if session.get("timer_id") == timer_id
    ]

    if not matches:
        return None

    if len(matches) > 1:
        active_ids = ", ".join(session["session_id"][:8] for session in matches)
        raise ValueError(f"Multiple active sessions for timer: {active_ids}")

    return matches[0]


def find_timer(timer_ref: str) -> dict:
    """Find a timer by UUID id or short code."""
    _require_text(timer_ref, "Timer")
    normalized_ref = _normalize_timer_ref(timer_ref)

    for timer in storage.get_timers():
        if (
            timer.get("id") == timer_ref
            or timer.get("code") == timer_ref
            or timer.get("code") == normalized_ref
        ):
            return timer

    raise ValueError(f"Unknown timer: {timer_ref}")


def _normalize_timer_ref(timer_ref: str) -> str:
    if timer_ref.isdigit():
        return timer_ref.zfill(2)

    return timer_ref


def _duration_seconds(started_at: str, stopped_at: str) -> int:
    started = _parse_timestamp(started_at)
    stopped = _parse_timestamp(stopped_at)
    return int((stopped - started).total_seconds())


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
