from __future__ import annotations

import curses
from datetime import datetime

from . import service


HELP_TEXT = "q quit  r refresh  up/down select  enter/s start or stop"


def run() -> None:
    """Run the timer TUI."""
    curses.wrapper(_run)


def _run(screen) -> None:
    _set_cursor(False)
    screen.keypad(True)
    state = {
        "selected": 0,
        "offset": 0,
        "message": "",
    }

    while True:
        groups = service.get_today_status()
        selected = min(state["selected"], max(len(groups) - 1, 0))
        state["selected"] = selected
        _draw(screen, groups, state)

        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (curses.KEY_UP, ord("k"), ord("K")):
            state["selected"] = max(selected - 1, 0)
        elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
            state["selected"] = min(selected + 1, max(len(groups) - 1, 0))
        elif key in (ord("r"), ord("R")):
            state["message"] = "refreshed"
        elif key in (curses.KEY_ENTER, 10, 13, ord("s"), ord("S")):
            _toggle_selected_timer(screen, groups, selected, state)


def _draw(screen, groups: list[dict], state: dict) -> None:
    screen.erase()
    height, width = screen.getmaxyx()
    _add_line(screen, 0, 0, "ZelTimer", curses.A_BOLD)
    _add_line(screen, 1, 0, HELP_TEXT)

    if state.get("message"):
        _add_line(screen, 2, 0, state["message"], curses.A_DIM)

    row = 4
    if not groups:
        _add_line(screen, row, 0, "No timers to display")
        screen.refresh()
        return

    offset = _visible_offset(groups, state, height)
    for index, group in enumerate(groups[offset:], offset):
        if row >= height - 1:
            break

        timer = group.get("timer", {})
        selected = index == state["selected"]
        row = _draw_timer_group(screen, row, timer, group, selected)
        row += 1

    screen.refresh()


def _visible_offset(groups: list[dict], state: dict, height: int) -> int:
    selected = state["selected"]
    offset = min(state.get("offset", 0), selected)
    available_rows = max(height - 5, 1)

    while selected >= offset and not _selection_fits(
        groups,
        offset,
        selected,
        available_rows,
    ):
        offset += 1

    state["offset"] = offset
    return offset


def _selection_fits(
    groups: list[dict],
    offset: int,
    selected: int,
    available_rows: int,
) -> bool:
    used_rows = 0
    for group in groups[offset : selected + 1]:
        used_rows += _group_height(group)

    return used_rows <= available_rows


def _group_height(group: dict) -> int:
    return len(group.get("sessions", [])) + 3


def _draw_timer_group(
    screen,
    row: int,
    timer: dict,
    group: dict,
    selected: bool,
) -> int:
    code = timer.get("code") or "-"
    name = timer.get("name") or "-"
    active = _timer_has_active_session(timer)
    marker = ">" if selected else " "
    status = "running" if active else "idle"
    title = f"{marker} {name} ({code}) [{status}]"
    _add_line(screen, row, 0, title, curses.A_REVERSE if selected else curses.A_NORMAL)
    row += 1

    title_width = max([len(session["title"]) for session in group["sessions"]] + [5])
    for session in group["sessions"]:
        started = _format_time(session["started_at"])
        stopped = "active" if session["active"] else _format_time(session["stopped_at"])
        duration = _format_duration(session["duration_seconds"])
        line = (
            f"  ├── {session['title']:<{title_width}}  "
            f"{started} -> {stopped:<6}  {duration}"
        )
        _add_line(screen, row, 0, line)
        row += 1

    total = _format_duration(group["total_seconds"])
    line = f"  └── {'TOTAL':<{title_width}}  {'':>5}    {'':<6}  {total}"
    _add_line(screen, row, 0, line, curses.A_BOLD)
    return row + 1


def _toggle_selected_timer(
    screen,
    groups: list[dict],
    selected: int,
    state: dict,
) -> None:
    if not groups:
        state["message"] = "no timers to select"
        return

    timer = groups[selected].get("timer", {})
    timer_ref = timer.get("id")
    if not timer_ref:
        state["message"] = "selected timer is missing an id"
        return

    try:
        if _timer_has_active_session(timer):
            session = service.stop_timer(timer_ref)
            state["message"] = (
                f"stopped {timer.get('name')}: "
                f"{session['title']} ({_format_duration(session['duration_seconds'])})"
            )
        else:
            title = _prompt(screen, "Session title", default=timer.get("name") or "")
            if title is None:
                state["message"] = "cancelled"
                return

            session = service.start_timer(timer_ref, title=title)
            state["message"] = f"started {timer.get('name')}: {session['title']}"
    except ValueError as error:
        state["message"] = str(error)


def _timer_has_active_session(timer: dict) -> bool:
    timer_id = timer.get("id")
    if not timer_id:
        return False

    try:
        return service.get_active_session_for_timer(timer_id) is not None
    except ValueError:
        return True


def _prompt(screen, label: str, default: str = "") -> str | None:
    height, width = screen.getmaxyx()
    prompt = f"{label} [{default}]: "
    row = height - 1
    _add_line(screen, row, 0, " " * max(width - 1, 0))
    _add_line(screen, row, 0, prompt)
    _set_cursor(True)
    curses.echo()

    try:
        value = screen.getstr(row, min(len(prompt), max(width - 1, 0)), 200)
    except KeyboardInterrupt:
        return None
    finally:
        curses.noecho()
        _set_cursor(False)

    text = value.decode("utf-8").strip()
    return text or default


def _add_line(screen, row: int, column: int, text: str, attr: int = curses.A_NORMAL) -> None:
    height, width = screen.getmaxyx()
    if row < 0 or row >= height or column >= width:
        return

    available_width = max(width - column - 1, 0)
    if available_width:
        screen.addnstr(row, column, text, available_width, attr)


def _set_cursor(visible: bool) -> None:
    try:
        curses.curs_set(1 if visible else 0)
    except curses.error:
        pass


def _format_duration(total_seconds: int) -> str:
    hours, remainder = divmod(max(total_seconds, 0), 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02}m {seconds:02}s"

    return f"{minutes}m {seconds:02}s"


def _format_time(value: str) -> str:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp.astimezone().strftime("%H:%M")
