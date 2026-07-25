from __future__ import annotations


TASK_STATUSES = {"active", "done", "cancelled"}
DEFAULT_STATUS = "active"


def validate_status(status: str) -> str:
    """Return a normalized task status or raise a clear error."""
    normalized = status.strip().lower()
    if normalized not in TASK_STATUSES:
        allowed = ", ".join(sorted(TASK_STATUSES))
        raise ValueError(f"Unknown task status '{status}'. Use one of: {allowed}")

    return normalized
