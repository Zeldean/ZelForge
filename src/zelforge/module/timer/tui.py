from __future__ import annotations

import curses
from datetime import date, datetime, timedelta

from . import service


HELP_TEXT = (
    "q quit  p/n date  t today  d set date  g range  r refresh  "
    "up/down select  enter/s start or stop"
)
DEFAULT_ATTR = curses.A_NORMAL
REFRESH_TIMEOUT_MS = 1000
COLORS_ENABLED = False
C_HEADER = 2
C_MUTED = 3
C_BORDER = 4
C_FOCUS = 5
C_ACTIVE = 6
C_MESSAGE = 7
C_ACCENT = 8


def run() -> None:
    """Run the timer TUI."""
    curses.wrapper(_run)


def _run(screen) -> None:
    _init_colors(screen)
    _set_cursor(False)
    screen.keypad(True)
    screen.timeout(REFRESH_TIMEOUT_MS)
    state = {
        "selected": 0,
        "offset": 0,
        "message": "",
        "start_date": date.today(),
        "end_date": date.today(),
    }

    while True:
        groups = _load_groups(state)
        selected = min(state["selected"], max(len(groups) - 1, 0))
        state["selected"] = selected
        _draw(screen, groups, state)

        key = screen.getch()
        if key == -1:
            continue

        if key in (ord("q"), ord("Q")):
            return
        if key in (curses.KEY_UP, ord("k"), ord("K")):
            state["selected"] = max(selected - 1, 0)
        elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
            state["selected"] = min(selected + 1, max(len(groups) - 1, 0))
        elif key in (ord("p"), ord("P")):
            _shift_range(state, -1)
        elif key in (ord("n"), ord("N")):
            _shift_range(state, 1)
        elif key in (ord("t"), ord("T")):
            today = date.today()
            state["start_date"] = today
            state["end_date"] = today
            state["message"] = "showing today"
        elif key in (ord("d"), ord("D")):
            _set_date(screen, state)
        elif key in (ord("g"), ord("G")):
            _set_range(screen, state)
        elif key in (ord("r"), ord("R")):
            state["message"] = "refreshed"
        elif key in (curses.KEY_ENTER, 10, 13, ord("s"), ord("S")):
            _toggle_selected_timer(screen, groups, selected, state)


def _load_groups(state: dict) -> list[dict]:
    return service.get_status(
        date_filter=state["start_date"] if _is_single_day(state) else None,
        start_date=None if _is_single_day(state) else state["start_date"],
        end_date=None if _is_single_day(state) else state["end_date"],
    )


def _draw(screen, groups: list[dict], state: dict) -> None:
    screen.erase()
    height, width = screen.getmaxyx()
    _add_line(screen, 0, 1, f"ZelTimer  {_range_label(state)}", _color(C_HEADER, curses.A_BOLD))
    _add_line(screen, 1, 1, _truncate(HELP_TEXT, width - 3), _color(C_MUTED, curses.A_DIM))

    if state.get("message"):
        _add_line(screen, 2, 1, _truncate(state["message"], width - 3), _color(C_MESSAGE))

    if width < 72 or height < 14:
        _draw_small(screen, groups, state, height, width)
        screen.refresh()
        return

    list_width = _timer_panel_width(groups, width)
    detail_width = width - list_width - 4
    panel_top = 4
    panel_height = height - panel_top - 1

    _draw_box(screen, panel_top, 1, panel_height, list_width, "Timers", focused=True)
    _draw_box(screen, panel_top, list_width + 2, panel_height, detail_width, "Sessions")

    if not groups:
        _add_line(screen, panel_top + 2, 3, "No timers to display")
        screen.refresh()
        return

    _draw_timer_tickets(screen, groups, state, panel_top + 1, 2, panel_height - 2, list_width - 2)
    _draw_detail_panel(
        screen,
        groups[state["selected"]],
        state,
        panel_top + 1,
        list_width + 3,
        panel_height - 2,
        detail_width - 2,
    )
    screen.refresh()


def _draw_small(screen, groups: list[dict], state: dict, height: int, width: int) -> None:
    if not groups:
        _add_line(screen, 4, 1, "No timers to display")
        return

    row = 4
    offset = _visible_offset(groups, state, height - 4)
    for index, group in enumerate(groups[offset:], offset):
        if row >= height - 1:
            break

        marker = ">" if index == state["selected"] else " "
        _add_line(screen, row, 1, _truncate(f"{marker} {_timer_summary(group)}", width - 2))
        row += 1


def _draw_timer_tickets(
    screen,
    groups: list[dict],
    state: dict,
    top: int,
    left: int,
    height: int,
    width: int,
) -> None:
    ticket_height = 4
    visible_count = max(height // ticket_height, 1)
    offset = _visible_offset(groups, state, visible_count)
    row = top

    for index, group in enumerate(groups[offset : offset + visible_count], offset):
        selected = index == state["selected"]
        attr = _color(C_FOCUS, curses.A_BOLD) if selected else _attr(curses.A_NORMAL)
        timer = group.get("timer", {})
        _draw_box(screen, row, left, 3, width, "", focused=selected)
        _add_line(screen, row + 1, left + 2, _truncate(_timer_summary(group), width - 4), attr)
        meta = (
            f"{timer.get('code') or '-'}  {len(group.get('sessions', []))} sessions  "
            f"{_format_duration(group['total_seconds'])}"
        )
        _add_line(screen, row + 2, left + 2, _truncate(meta, width - 4), _color(C_MUTED, curses.A_DIM))
        row += ticket_height


def _timer_panel_width(groups: list[dict], screen_width: int) -> int:
    if not groups:
        return min(34, max(screen_width - 42, 24))

    content_width = max(
        [
            len(_timer_summary(group))
            for group in groups
        ]
        + [len("Timers")]
    )
    desired = content_width + 6
    max_width = max(min(screen_width - 44, 52), 28)
    return max(min(desired, max_width), 28)


def _draw_detail_panel(
    screen,
    group: dict,
    state: dict,
    top: int,
    left: int,
    height: int,
    width: int,
) -> None:
    timer = group.get("timer", {})
    row = top + 1
    _add_line(screen, row, left, _truncate(timer.get("name") or "-", width), _color(C_HEADER, curses.A_BOLD))
    row += 1
    _add_line(
        screen,
        row,
        left,
        _truncate(
            f"code {timer.get('code') or '-'}  total {_format_duration(group['total_seconds'])}",
            width,
        ),
        _color(C_MUTED, curses.A_DIM),
    )
    row += 2

    sessions = group.get("sessions", [])
    if not sessions:
        _add_line(screen, row, left, "No sessions in this range")
        return

    include_date = not _is_single_day(state)
    for session in sessions:
        if row + 3 >= top + height - 2:
            break

        _draw_session_block(screen, session, row, left, width, include_date)
        row += 5

    if row < top + height:
        _add_line(
            screen,
            row + 1,
            left,
            _truncate(f"TOTAL {_format_duration(group['total_seconds'])}", width),
            _color(C_ACCENT, curses.A_BOLD),
        )


def _draw_session_block(
    screen,
    session: dict,
    top: int,
    left: int,
    width: int,
    include_date: bool,
) -> None:
    block_width = max(width, 12)
    _draw_box(screen, top, left, 4, block_width, "", focused=session.get("active", False))

    title = f"{_status_icon(session)} {session['title']}"
    _add_centered_line(
        screen,
        top + 1,
        left + 1,
        block_width - 2,
        title,
        _color(C_ACTIVE, curses.A_BOLD) if session.get("active") else _attr(curses.A_BOLD),
    )

    started = _format_time(session["started_at"], include_date=include_date)
    stopped = (
        "active"
        if session["active"]
        else _format_time(session["stopped_at"], include_date=include_date)
    )
    duration = _format_duration(session["duration_seconds"])
    timing = f"{started} -> {stopped}    {duration}"
    _add_centered_line(screen, top + 2, left + 1, block_width - 2, timing, _color(C_MUTED, curses.A_DIM))


def _visible_offset(groups: list[dict], state: dict, visible_count: int) -> int:
    selected = state["selected"]
    offset = min(state.get("offset", 0), selected)
    visible_count = max(visible_count, 1)

    if selected >= offset + visible_count:
        offset = selected - visible_count + 1

    state["offset"] = max(offset, 0)
    return state["offset"]


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
            today = date.today()
            state["start_date"] = today
            state["end_date"] = today
    except ValueError as error:
        state["message"] = str(error)


def _set_date(screen, state: dict) -> None:
    value = _prompt(screen, "Date", default=state["start_date"].isoformat())
    if value is None:
        state["message"] = "cancelled"
        return

    try:
        selected = date.fromisoformat(value)
    except ValueError:
        state["message"] = f"invalid date: {value}"
        return

    state["start_date"] = selected
    state["end_date"] = selected
    state["selected"] = 0
    state["offset"] = 0
    state["message"] = f"showing {selected.isoformat()}"


def _set_range(screen, state: dict) -> None:
    start_value = _prompt(screen, "Start date", default=state["start_date"].isoformat())
    if start_value is None:
        state["message"] = "cancelled"
        return

    end_value = _prompt(screen, "End date", default=state["end_date"].isoformat())
    if end_value is None:
        state["message"] = "cancelled"
        return

    try:
        start = date.fromisoformat(start_value)
        end = date.fromisoformat(end_value)
    except ValueError:
        state["message"] = "invalid range date"
        return

    if start > end:
        state["message"] = "start date cannot be after end date"
        return

    state["start_date"] = start
    state["end_date"] = end
    state["selected"] = 0
    state["offset"] = 0
    state["message"] = f"showing {_range_label(state)}"


def _shift_range(state: dict, days: int) -> None:
    delta = timedelta(days=days)
    state["start_date"] = state["start_date"] + delta
    state["end_date"] = state["end_date"] + delta
    state["message"] = f"showing {_range_label(state)}"


def _timer_has_active_session(timer: dict) -> bool:
    timer_id = timer.get("id")
    if not timer_id:
        return False

    try:
        return service.get_active_session_for_timer(timer_id) is not None
    except ValueError:
        return True


def _timer_summary(group: dict) -> str:
    timer = group.get("timer", {})
    running = " running" if _timer_has_active_session(timer) else ""
    return (
        f"{timer.get('name') or '-'} ({timer.get('code') or '-'})"
        f"{running}  {_format_duration(group['total_seconds'])}"
    )


def _is_single_day(state: dict) -> bool:
    return state["start_date"] == state["end_date"]


def _range_label(state: dict) -> str:
    if _is_single_day(state):
        return state["start_date"].isoformat()

    return f"{state['start_date'].isoformat()} -> {state['end_date'].isoformat()}"


def _status_icon(session: dict) -> str:
    return "●" if session.get("active") else "•"


def _prompt(screen, label: str, default: str = "") -> str | None:
    height, width = screen.getmaxyx()
    prompt = f"{label} [{default}]: "
    row = height - 1
    _add_line(screen, row, 0, " " * max(width - 1, 0))
    _add_line(screen, row, 0, _truncate(prompt, width - 1))
    screen.timeout(-1)
    _set_cursor(True)
    curses.echo()

    try:
        value = screen.getstr(row, min(len(prompt), max(width - 1, 0)), 200)
    except KeyboardInterrupt:
        return None
    finally:
        curses.noecho()
        _set_cursor(False)
        screen.timeout(REFRESH_TIMEOUT_MS)

    text = value.decode("utf-8").strip()
    return text or default


def _draw_box(
    screen,
    top: int,
    left: int,
    height: int,
    width: int,
    title: str,
    focused: bool = False,
) -> None:
    if height < 2 or width < 4:
        return

    attr = _color(C_FOCUS if focused else C_BORDER, curses.A_BOLD if focused else curses.A_NORMAL)
    horizontal = "═" if focused else "─"
    vertical = "║" if focused else "│"
    top_left = "╔" if focused else "┌"
    top_right = "╗" if focused else "┐"
    bottom_left = "╚" if focused else "└"
    bottom_right = "╝" if focused else "┘"

    _add_line(screen, top, left, top_left + horizontal * (width - 2) + top_right, attr)
    for row in range(top + 1, top + height - 1):
        _add_line(screen, row, left, vertical, attr)
        _add_line(screen, row, left + width - 1, vertical, attr)
    _add_line(
        screen,
        top + height - 1,
        left,
        bottom_left + horizontal * (width - 2) + bottom_right,
        attr,
    )

    if title:
        _add_line(screen, top, left + 2, f" {title} ", attr)


def _add_centered_line(
    screen,
    row: int,
    column: int,
    width: int,
    text: str,
    attr: int | None = None,
) -> None:
    clipped = _truncate(text, width)
    padding = max((width - len(clipped)) // 2, 0)
    _add_line(screen, row, column + padding, clipped, attr)


def _add_line(screen, row: int, column: int, text: str, attr: int | None = None) -> None:
    height, width = screen.getmaxyx()
    if row < 0 or row >= height or column >= width:
        return

    available_width = max(width - column - 1, 0)
    if available_width:
        screen.addnstr(
            row,
            column,
            text,
            available_width,
            DEFAULT_ATTR if attr is None else attr,
        )


def _init_colors(screen) -> None:
    global COLORS_ENABLED, DEFAULT_ATTR

    if not curses.has_colors():
        return

    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, -1, -1)
        curses.init_pair(C_HEADER, curses.COLOR_CYAN, -1)
        curses.init_pair(C_MUTED, curses.COLOR_WHITE, -1)
        curses.init_pair(C_BORDER, curses.COLOR_BLUE, -1)
        curses.init_pair(C_FOCUS, curses.COLOR_CYAN, -1)
        curses.init_pair(C_ACTIVE, curses.COLOR_GREEN, -1)
        curses.init_pair(C_MESSAGE, curses.COLOR_YELLOW, -1)
        curses.init_pair(C_ACCENT, curses.COLOR_MAGENTA, -1)
        DEFAULT_ATTR = curses.color_pair(1)
        COLORS_ENABLED = True
        screen.bkgdset(" ", DEFAULT_ATTR)
    except curses.error:
        DEFAULT_ATTR = curses.A_NORMAL
        COLORS_ENABLED = False


def _attr(attr: int) -> int:
    return DEFAULT_ATTR | attr


def _color(pair: int, attr: int = curses.A_NORMAL) -> int:
    if COLORS_ENABLED:
        return DEFAULT_ATTR | curses.color_pair(pair) | attr

    return _attr(attr)


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


def _format_time(value: str, include_date: bool = False) -> str:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    format_text = "%Y-%m-%d %H:%M" if include_date else "%H:%M"
    return timestamp.astimezone().strftime(format_text)


def _truncate(value: str, width: int) -> str:
    if width <= 0 or len(value) <= width:
        return value

    return f"{value[: max(width - 1, 0)]}…"
