from __future__ import annotations


TASK_STATUSES = {"active", "done", "cancelled"}
DEFAULT_STATUS = "active"
TASK_PRIORITIES = {
    0: "none",
    1: "low",
    2: "medium",
    3: "high",
    4: "urgent",
}
PRIORITY_LABELS = {label: value for value, label in TASK_PRIORITIES.items()}
DEFAULT_PRIORITY = 2


def validate_status(status: str) -> str:
    """Return a normalized task status or raise a clear error."""
    normalized = status.strip().lower()
    if normalized not in TASK_STATUSES:
        allowed = ", ".join(sorted(TASK_STATUSES))
        raise ValueError(f"Unknown task status '{status}'. Use one of: {allowed}")

    return normalized


def validate_priority(priority: int | str | None) -> int:
    """Return a normalized priority number or raise a clear error."""
    if priority is None:
        return DEFAULT_PRIORITY

    if isinstance(priority, int):
        return _validate_priority_number(priority)

    normalized = priority.strip().lower()
    if not normalized:
        return DEFAULT_PRIORITY

    if normalized.isdigit():
        return _validate_priority_number(int(normalized))

    if normalized not in PRIORITY_LABELS:
        allowed = ", ".join(
            [str(value) for value in TASK_PRIORITIES]
            + list(TASK_PRIORITIES.values())
        )
        raise ValueError(f"Unknown task priority '{priority}'. Use one of: {allowed}")

    return PRIORITY_LABELS[normalized]


def get_priority_label(priority: int | str | None) -> str:
    """Return a display label for a stored task priority."""
    try:
        return TASK_PRIORITIES[validate_priority(priority)]
    except ValueError:
        return str(priority or TASK_PRIORITIES[DEFAULT_PRIORITY])


def _validate_priority_number(priority: int) -> int:
    if priority not in TASK_PRIORITIES:
        allowed = ", ".join(str(value) for value in TASK_PRIORITIES)
        raise ValueError(f"Unknown task priority '{priority}'. Use one of: {allowed}")

    return priority
