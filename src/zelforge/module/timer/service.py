from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import NAMESPACE_URL, uuid5

from . import storage


def start_timer(timer_ref: str, title: str | None = None) -> dict:
    """Start a timer by appending a start event to the live log."""
    timer = find_timer(timer_ref)
    active = get_active_session_for_timer(timer["id"])
    if active:
        stop_timer(timer["id"])

    event = {
        "event": "start",
        "timer_id": timer["id"],
        "title": title or timer["name"],
        "created_at": _now(),
    }
    storage.append_log_event(event)

    return {
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
        "timer_id": timer["id"],
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
        storage.write_log_events(events)
        return {
            "saved": 0,
            "skipped_invalid": len(invalid_sessions),
            "remaining_events": len(events),
            "active": len(get_active_sessions()),
        }

    sessions_data = storage.get_sessions_data()
    existing_ids = {session.get("id") for session in sessions_data["sessions"]}
    promoted_event_indexes = set()
    saved = 0

    for session in promotable:
        promoted_event_indexes.update(session.get("_log_indexes", []))
        persisted_session = {
            key: value
            for key, value in session.items()
            if not key.startswith("_")
        }
        if session["id"] in existing_ids:
            continue

        sessions_data["sessions"].append(persisted_session)
        existing_ids.add(session["id"])
        saved += 1

    storage.save_sessions_data(sessions_data)

    remaining_events = [
        event
        for index, event in enumerate(events)
        if index not in promoted_event_indexes
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


def get_today_status(timer_refs: list[str] | None = None) -> list[dict]:
    """Return today's sessions grouped by timer."""
    return get_status(timer_refs=timer_refs)


def get_status(
    timer_refs: list[str] | None = None,
    date_filter: str | date | None = None,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
) -> list[dict]:
    """Return sessions for a local date or date range, grouped by timer."""
    timers = storage.get_timers()
    timer_filters = _find_timer_ids(timer_refs or [], timers)
    timers_by_id = {timer["id"]: timer for timer in timers}
    selected_timers = [
        timer
        for timer in timers
        if (
            timer["id"] in timer_filters
            if timer_filters
            else _timer_is_visible_by_default(timer)
        )
    ]
    selected_timer_ids = {timer["id"] for timer in selected_timers}
    range_start, range_end = _status_range(date_filter, start_date, end_date)
    sessions_by_id: dict[str, dict] = {}

    for session in storage.get_sessions():
        normalized = _status_session_from_saved(session, timers_by_id)
        if normalized:
            sessions_by_id[normalized["id"]] = normalized

    events = storage.read_log_events()
    for session in _closed_sessions_from_events(events):
        normalized = _status_session_from_saved(session, timers_by_id)
        if normalized:
            sessions_by_id[normalized["id"]] = normalized

    for session in _active_sessions_from_events(events):
        normalized = _status_session_from_active(session, timers_by_id)
        if normalized:
            sessions_by_id[normalized["id"]] = normalized

    sessions = []
    for session in sessions_by_id.values():
        clipped = _clip_session_to_range(session, range_start, range_end)
        if clipped:
            sessions.append(clipped)

    grouped_by_timer: dict[str, dict] = {
        timer["id"]: {
            "timer": timer,
            "sessions": [],
            "total_seconds": 0,
        }
        for timer in selected_timers
    }

    for session in sorted(sessions, key=lambda item: item["started_at"]):
        timer_id = session.get("timer_id")
        if timer_id not in selected_timer_ids:
            continue

        group = grouped_by_timer[timer_id]
        group["sessions"].append(session)
        group["total_seconds"] += session["duration_seconds"]

    return sorted(
        grouped_by_timer.values(),
        key=lambda group: (
            group["timer"].get("code") or "",
            group["timer"].get("name") or "",
        ),
    )


def get_today_active_sessions(timer_ref: str | None = None) -> list[dict]:
    """Return active sessions that started during the current local day."""
    timer_filter = find_timer(timer_ref)["id"] if timer_ref else None
    timers_by_id = {timer["id"]: timer for timer in storage.get_timers()}
    today = datetime.now().astimezone().date()
    sessions = []

    for session in get_active_sessions():
        started_at = session.get("started_at")
        if not started_at:
            continue

        if _parse_timestamp(started_at).astimezone().date() != today:
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


def _status_session_from_saved(
    session: dict,
    timers_by_id: dict[str, dict],
) -> dict | None:
    started_at = session.get("started_at")
    stopped_at = session.get("stopped_at")
    timer_id = session.get("timer_id")
    if not started_at or not timer_id:
        return None

    duration = session.get("duration_seconds")
    if duration is None and stopped_at:
        duration = _duration_seconds(started_at, stopped_at)
    elif duration is None:
        duration = 0

    return {
        "id": session.get("id") or session.get("session_id"),
        "timer_id": timer_id,
        "timer": timers_by_id.get(timer_id, {}),
        "title": session.get("title") or "",
        "started_at": started_at,
        "stopped_at": stopped_at,
        "duration_seconds": max(int(duration), 0),
        "active": stopped_at is None,
    }


def _status_session_from_active(
    session: dict,
    timers_by_id: dict[str, dict],
) -> dict | None:
    started_at = session.get("started_at")
    timer_id = session.get("timer_id")
    if not started_at or not timer_id:
        return None

    return {
        "id": session["id"],
        "timer_id": timer_id,
        "timer": timers_by_id.get(timer_id, {}),
        "title": session.get("title") or "",
        "started_at": started_at,
        "stopped_at": None,
        "duration_seconds": _duration_seconds(started_at, _now()),
        "active": True,
    }


def get_active_sessions() -> list[dict]:
    """Return active sessions reconstructed from the event log."""
    return _active_sessions_from_events(storage.read_log_events())


def _active_sessions_from_events(events: list[dict]) -> list[dict]:
    active_by_session_id: dict[str, dict] = {}
    active_by_timer_id: dict[str, dict] = {}

    for event in events:
        event_name = event.get("event")
        session_id = event.get("session_id")
        timer_id = event.get("timer_id")

        if event_name == "start":
            active = _active_session_from_start_event(event)
            if not active:
                continue

            if session_id:
                if session_id in active_by_session_id:
                    continue

                active_by_session_id[session_id] = active
            elif timer_id and timer_id not in active_by_timer_id:
                active_by_timer_id[timer_id] = active
        elif event_name == "stop":
            if session_id:
                active_by_session_id.pop(session_id, None)
            elif timer_id:
                active_by_timer_id.pop(timer_id, None)

    return [
        *active_by_session_id.values(),
        *active_by_timer_id.values(),
    ]


def _closed_sessions_from_events(events: list[dict]) -> list[dict]:
    starts_by_session_id: dict[str, dict] = {}
    starts_by_timer_id: dict[str, dict] = {}
    closed_sessions = []

    for index, event in enumerate(events):
        event_name = event.get("event")
        session_id = event.get("session_id")
        timer_id = event.get("timer_id")

        if event_name == "start":
            if session_id:
                if session_id in starts_by_session_id:
                    continue

                starts_by_session_id[session_id] = {**event, "_log_index": index}
            elif timer_id and timer_id not in starts_by_timer_id:
                starts_by_timer_id[timer_id] = {**event, "_log_index": index}
        elif event_name == "stop":
            if session_id:
                start_event = starts_by_session_id.pop(session_id, None)
            elif timer_id:
                start_event = starts_by_timer_id.pop(timer_id, None)
            else:
                start_event = None

            if not start_event:
                continue

            started_at = start_event["created_at"]
            stopped_at = event["created_at"]
            session_id = start_event.get("session_id") or _make_session_id(
                start_event["timer_id"],
                started_at,
            )
            closed_sessions.append(
                {
                    "id": session_id,
                    "timer_id": start_event["timer_id"],
                    "title": start_event.get("title") or "",
                    "started_at": started_at,
                    "stopped_at": stopped_at,
                    "duration_seconds": _duration_seconds(started_at, stopped_at),
                    "_log_indexes": [start_event["_log_index"], index],
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
        titles = ", ".join(session["title"] for session in matches)
        raise ValueError(f"Multiple active sessions for timer: {titles}")

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


def _find_timer_ids(timer_refs: list[str], timers: list[dict]) -> set[str]:
    timer_ids = set()

    for timer_ref in timer_refs:
        _require_text(timer_ref, "Timer")
        normalized_ref = _normalize_timer_ref(timer_ref)
        for timer in timers:
            if (
                timer.get("id") == timer_ref
                or timer.get("code") == timer_ref
                or timer.get("code") == normalized_ref
            ):
                timer_ids.add(timer["id"])
                break
        else:
            raise ValueError(f"Unknown timer: {timer_ref}")

    return timer_ids


def _timer_is_visible_by_default(timer: dict) -> bool:
    return timer.get("active") is not False and timer.get("archived") is not True


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


def _status_range(
    date_filter: str | date | None,
    start_date: str | date | None,
    end_date: str | date | None,
) -> tuple[datetime, datetime]:
    if date_filter and (start_date or end_date):
        raise ValueError("Use --date or --start-date/--end-date, not both")

    local_tz = datetime.now().astimezone().tzinfo
    if date_filter:
        selected = _parse_local_date(date_filter)
        return _local_day_bounds(selected, local_tz)

    if start_date or end_date:
        start = _parse_local_date(start_date or end_date)
        end = _parse_local_date(end_date or start_date)
        if start > end:
            raise ValueError("start date cannot be after end date")

        range_start = datetime.combine(start, time.min, tzinfo=local_tz)
        range_end = datetime.combine(end, time.max, tzinfo=local_tz)
        return range_start, range_end

    return _local_day_bounds(datetime.now().astimezone().date(), local_tz)


def _parse_local_date(value: str | date | None) -> date:
    if value is None:
        raise ValueError("date is required")

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.") from error


def _local_day_bounds(selected: date, local_tz) -> tuple[datetime, datetime]:
    return (
        datetime.combine(selected, time.min, tzinfo=local_tz),
        datetime.combine(selected, time.max, tzinfo=local_tz),
    )


def _active_session_from_start_event(event: dict) -> dict | None:
    timer_id = event.get("timer_id")
    started_at = event.get("created_at")
    if not timer_id or not started_at:
        return None

    return {
        "id": event.get("session_id") or _make_session_id(timer_id, started_at),
        "timer_id": timer_id,
        "title": event.get("title") or "",
        "started_at": started_at,
    }


def _make_session_id(timer_id: str, started_at: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"zelforge:timer:{timer_id}:{started_at}"))


def _clip_session_to_range(
    session: dict,
    range_start: datetime,
    range_end: datetime,
) -> dict | None:
    started_at = _parse_timestamp(session["started_at"]).astimezone()
    stopped_at = session.get("stopped_at")
    ended_at = (
        _parse_timestamp(stopped_at).astimezone()
        if stopped_at
        else datetime.now().astimezone()
    )

    if started_at > range_end or ended_at < range_start:
        return None

    clipped_start = max(started_at, range_start)
    clipped_end = min(ended_at, range_end)

    return {
        **session,
        "started_at": clipped_start.isoformat(),
        "stopped_at": None if session.get("active") else clipped_end.isoformat(),
        "duration_seconds": int((clipped_end - clipped_start).total_seconds()),
    }


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} cannot be blank")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
