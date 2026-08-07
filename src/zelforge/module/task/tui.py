from __future__ import annotations

import curses
import textwrap

from . import service
from .models import get_priority_label


HELP_TEXT = "q quit  r refresh  a add  d done  c cancel  o reopen  tab active/all"
DEFAULT_ATTR = curses.A_NORMAL


def run() -> None:
    """Run the task TUI."""
    curses.wrapper(_run)


def _run(screen) -> None:
    _init_colors(screen)
    _set_cursor(False)
    screen.keypad(True)
    state = {
        "selected": 0,
        "offset": 0,
        "include_all": False,
        "message": "",
    }

    while True:
        tasks = _load_tasks(state)
        selected = min(state["selected"], max(len(tasks) - 1, 0))
        state["selected"] = selected
        _draw(screen, tasks, state)

        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (curses.KEY_UP, ord("k"), ord("K")):
            state["selected"] = max(selected - 1, 0)
        elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
            state["selected"] = min(selected + 1, max(len(tasks) - 1, 0))
        elif key in (ord("\t"),):
            state["include_all"] = not state["include_all"]
            state["selected"] = 0
            state["offset"] = 0
            state["message"] = _mode_message(state)
        elif key in (ord("r"), ord("R")):
            state["message"] = "refreshed"
        elif key in (ord("a"), ord("A")):
            _add_task(screen, state)
        elif key in (ord("d"), ord("D")):
            _update_selected_task(tasks, selected, state, "done")
        elif key in (ord("c"), ord("C")):
            _update_selected_task(tasks, selected, state, "cancelled")
        elif key in (ord("o"), ord("O")):
            _update_selected_task(tasks, selected, state, "active")


def _load_tasks(state: dict) -> list[dict]:
    return service.list_tasks(include_all=state["include_all"])


def _draw(screen, tasks: list[dict], state: dict) -> None:
    screen.erase()
    height, width = screen.getmaxyx()
    mode = "all" if state["include_all"] else "active"
    _add_line(screen, 0, 0, f"ZelTask ({mode})", _attr(curses.A_BOLD))
    _add_line(screen, 1, 0, HELP_TEXT)

    if state.get("message"):
        _add_line(screen, 2, 0, state["message"], _attr(curses.A_DIM))

    if not tasks:
        _add_line(screen, 4, 0, "No tasks")
        screen.refresh()
        return

    list_width = max(min(width // 2, 72), 32)
    detail_column = list_width + 2
    _draw_task_list(screen, tasks, state, list_width, height)
    _draw_task_detail(screen, tasks[state["selected"]], detail_column, width, height)
    screen.refresh()


def _draw_task_list(
    screen,
    tasks: list[dict],
    state: dict,
    list_width: int,
    height: int,
) -> None:
    row = 4
    offset = _visible_offset(tasks, state, height)
    for index, task in enumerate(tasks[offset:], offset):
        if row >= height - 1:
            break

        selected = index == state["selected"]
        marker = ">" if selected else " "
        priority = get_priority_label(task.get("priority"))
        line = f"{marker} {_status_icon(task)} {priority:<7} {task['title']}"
        attr = _attr(curses.A_BOLD if selected else curses.A_NORMAL)
        _add_line(screen, row, 0, _truncate(line, list_width - 1), attr)
        row += 1


def _draw_task_detail(
    screen,
    task: dict,
    column: int,
    width: int,
    height: int,
) -> None:
    if column >= width - 8:
        return

    detail_width = width - column - 1
    row = 4
    lines = [
        task["title"],
        "",
        f"id        {task['id'][:8]}",
        f"status    {task['status']}",
        f"priority  {get_priority_label(task.get('priority'))}",
        f"domain    {task.get('domain') or '-'}",
        f"tags      {', '.join(task.get('tags', [])) or '-'}",
        "",
        "description",
        task.get("description") or "-",
    ]

    for line in lines:
        if row >= height - 1:
            break

        wrapped = textwrap.wrap(line, width=max(detail_width, 1)) or [""]
        for wrapped_line in wrapped:
            if row >= height - 1:
                break

            attr = _attr(curses.A_BOLD) if row == 4 else None
            _add_line(screen, row, column, wrapped_line, attr)
            row += 1


def _visible_offset(tasks: list[dict], state: dict, height: int) -> int:
    selected = state["selected"]
    offset = min(state.get("offset", 0), selected)
    available_rows = max(height - 5, 1)

    if selected >= offset + available_rows:
        offset = selected - available_rows + 1

    state["offset"] = max(offset, 0)
    return state["offset"]


def _add_task(screen, state: dict) -> None:
    title = _prompt(screen, "Task title")
    if not title:
        state["message"] = "cancelled"
        return

    priority = _prompt(screen, "Priority", default="medium")
    if priority is None:
        state["message"] = "cancelled"
        return

    domain = _prompt(screen, "Domain", default="")
    if domain is None:
        state["message"] = "cancelled"
        return

    try:
        task = service.create_task(title=title, priority=priority, domain=domain)
        state["include_all"] = False
        state["message"] = f"created {task['id'][:8]}: {task['title']}"
    except ValueError as error:
        state["message"] = str(error)


def _update_selected_task(
    tasks: list[dict],
    selected: int,
    state: dict,
    status: str,
) -> None:
    if not tasks:
        state["message"] = "no task selected"
        return

    task = tasks[selected]
    try:
        updated = service.update_task(task["id"], status=status)
        state["message"] = f"{updated['status']} {updated['id'][:8]}: {updated['title']}"
    except ValueError as error:
        state["message"] = str(error)


def _mode_message(state: dict) -> str:
    return "showing all tasks" if state["include_all"] else "showing active tasks"


def _status_icon(task: dict) -> str:
    status = task.get("status")
    if status == "done":
        return "✓"
    if status == "cancelled":
        return "×"
    return "•"


def _prompt(screen, label: str, default: str | None = None) -> str | None:
    height, width = screen.getmaxyx()
    suffix = f" [{default}]" if default is not None else ""
    prompt = f"{label}{suffix}: "
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
    if text:
        return text

    return default


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
    global DEFAULT_ATTR

    if not curses.has_colors():
        return

    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, -1, -1)
        DEFAULT_ATTR = curses.color_pair(1)
        screen.bkgdset(" ", DEFAULT_ATTR)
    except curses.error:
        DEFAULT_ATTR = curses.A_NORMAL


def _attr(attr: int) -> int:
    return DEFAULT_ATTR | attr


def _set_cursor(visible: bool) -> None:
    try:
        curses.curs_set(1 if visible else 0)
    except curses.error:
        pass


def _truncate(value: str, width: int) -> str:
    if width <= 0 or len(value) <= width:
        return value

    return f"{value[: max(width - 1, 0)]}…"
