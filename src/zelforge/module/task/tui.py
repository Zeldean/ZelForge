from __future__ import annotations

import curses
import textwrap

from . import service
from .models import get_priority_label


HELP_TEXT = (
    "q quit  tab active/all  left/right focus  up/down select  "
    "a task  s subtask  e edit  d done  c cancel  o reopen  x remove subtask"
)
DEFAULT_ATTR = curses.A_NORMAL
FOCUS_TASKS = "tasks"
FOCUS_SUBTASKS = "subtasks"


def run() -> None:
    """Run the task TUI."""
    curses.wrapper(_run)


def _run(screen) -> None:
    _init_colors(screen)
    _set_cursor(False)
    screen.keypad(True)
    state = {
        "focus": FOCUS_TASKS,
        "selected": 0,
        "subtask_selected": 0,
        "offset": 0,
        "subtask_offset": 0,
        "include_all": False,
        "message": "",
    }

    while True:
        tasks = _load_tasks(state)
        selected = min(state["selected"], max(len(tasks) - 1, 0))
        state["selected"] = selected
        if tasks:
            subtasks = _focused_subtasks(tasks[selected])
            state["subtask_selected"] = min(
                state["subtask_selected"],
                max(len(subtasks) - 1, 0),
            )
        else:
            state["subtask_selected"] = 0

        _draw(screen, tasks, state)

        key = screen.getch()
        if key in (ord("q"), ord("Q")):
            return
        if key in (curses.KEY_LEFT, ord("h"), ord("H")):
            state["focus"] = FOCUS_TASKS
        elif key in (curses.KEY_RIGHT, ord("l"), ord("L"), ord("\n"), curses.KEY_ENTER):
            if tasks:
                state["focus"] = FOCUS_SUBTASKS
        elif key in (curses.KEY_UP, ord("k"), ord("K")):
            _move_selection(tasks, state, -1)
        elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
            _move_selection(tasks, state, 1)
        elif key in (ord("\t"),):
            state["include_all"] = not state["include_all"]
            state["selected"] = 0
            state["subtask_selected"] = 0
            state["offset"] = 0
            state["subtask_offset"] = 0
            state["focus"] = FOCUS_TASKS
            state["message"] = _mode_message(state)
        elif key in (ord("r"), ord("R")):
            state["message"] = "refreshed"
        elif key in (ord("a"), ord("A")):
            _add_task(screen, state)
        elif key in (ord("s"), ord("S")):
            _add_subtask(screen, tasks, selected, state)
        elif key in (ord("e"), ord("E")):
            _edit_focused(screen, tasks, selected, state)
        elif key in (ord("d"), ord("D")):
            _update_focused(tasks, selected, state, "done")
        elif key in (ord("c"), ord("C")):
            _update_focused(tasks, selected, state, "cancelled")
        elif key in (ord("o"), ord("O")):
            _update_focused(tasks, selected, state, "active")
        elif key in (ord("x"), ord("X")):
            _remove_focused_subtask(screen, tasks, selected, state)


def _load_tasks(state: dict) -> list[dict]:
    return service.list_tasks(include_all=state["include_all"])


def _draw(screen, tasks: list[dict], state: dict) -> None:
    screen.erase()
    height, width = screen.getmaxyx()
    mode = "all" if state["include_all"] else "active"
    _add_line(screen, 0, 1, f"ZelTask ({mode})", _attr(curses.A_BOLD))
    _add_line(screen, 1, 1, _truncate(HELP_TEXT, width - 3), _attr(curses.A_DIM))

    if state.get("message"):
        _add_line(screen, 2, 1, _truncate(state["message"], width - 3), _attr(curses.A_DIM))

    if width < 72 or height < 14:
        _draw_small(screen, tasks, state, height, width)
        screen.refresh()
        return

    list_width = max(min(width // 2, 74), 38)
    detail_width = width - list_width - 4
    panel_top = 4
    panel_height = height - panel_top - 1

    _draw_box(
        screen,
        panel_top,
        1,
        panel_height,
        list_width,
        "Tasks",
        focused=state["focus"] == FOCUS_TASKS,
    )
    _draw_box(
        screen,
        panel_top,
        list_width + 2,
        panel_height,
        detail_width,
        "Details",
        focused=state["focus"] == FOCUS_SUBTASKS,
    )

    if not tasks:
        _add_line(screen, panel_top + 2, 3, "No tasks")
        screen.refresh()
        return

    _draw_task_tickets(screen, tasks, state, panel_top + 1, 2, panel_height - 2, list_width - 2)
    _draw_detail_panel(
        screen,
        tasks[state["selected"]],
        state,
        panel_top + 1,
        list_width + 3,
        panel_height - 2,
        detail_width - 2,
    )
    screen.refresh()


def _draw_small(screen, tasks: list[dict], state: dict, height: int, width: int) -> None:
    if not tasks:
        _add_line(screen, 4, 1, "No tasks")
        return

    row = 4
    offset = _visible_offset(tasks, state, height - 4, "offset", "selected")
    for index, task in enumerate(tasks[offset:], offset):
        if row >= height - 1:
            break

        marker = ">" if index == state["selected"] else " "
        line = f"{marker} {_task_summary_line(task)}"
        _add_line(screen, row, 1, _truncate(line, width - 2))
        row += 1


def _draw_task_tickets(
    screen,
    tasks: list[dict],
    state: dict,
    top: int,
    left: int,
    height: int,
    width: int,
) -> None:
    ticket_height = 4
    visible_count = max(height // ticket_height, 1)
    offset = _visible_offset(tasks, state, visible_count, "offset", "selected")
    row = top

    for index, task in enumerate(tasks[offset : offset + visible_count], offset):
        selected = index == state["selected"]
        attr = _attr(curses.A_BOLD if selected else curses.A_NORMAL)
        _draw_box(screen, row, left, 3, width, "", focused=selected)
        _add_line(screen, row + 1, left + 2, _truncate(_task_summary_line(task), width - 4), attr)
        meta = (
            f"{task['id'][:8]}  {task['status']}  "
            f"{get_priority_label(task.get('priority'))}"
        )
        _add_line(screen, row + 2, left + 2, _truncate(meta, width - 4), _attr(curses.A_DIM))
        row += ticket_height


def _draw_detail_panel(
    screen,
    task: dict,
    state: dict,
    top: int,
    left: int,
    height: int,
    width: int,
) -> None:
    row = top + 1
    _add_line(screen, row, left, _truncate(task["title"], width), _attr(curses.A_BOLD))
    row += 2

    meta_lines = [
        f"id        {task['id'][:8]}",
        f"status    {task['status']}",
        f"priority  {get_priority_label(task.get('priority'))}",
        f"domain    {task.get('domain') or '-'}",
        f"tags      {', '.join(task.get('tags', [])) or '-'}",
    ]
    for line in meta_lines:
        if row >= top + height:
            return
        _add_line(screen, row, left, _truncate(line, width))
        row += 1

    row += 1
    _add_line(screen, row, left, "Description", _attr(curses.A_BOLD))
    row += 1
    for line in _wrap(task.get("description") or "-", width):
        if row >= top + height:
            return
        _add_line(screen, row, left, line)
        row += 1

    row += 1
    if row >= top + height:
        return
    _add_line(
        screen,
        row,
        left,
        f"Subtasks {_subtask_summary(task.get('subtasks', []))}",
        _attr(curses.A_BOLD),
    )
    row += 1
    _draw_subtasks(screen, task, state, row, left, top + height - row, width)


def _draw_subtasks(
    screen,
    task: dict,
    state: dict,
    top: int,
    left: int,
    height: int,
    width: int,
) -> None:
    subtasks = task.get("subtasks", [])
    if not subtasks:
        _add_line(screen, top, left, "-")
        return

    offset = _visible_offset(
        subtasks,
        state,
        height,
        "subtask_offset",
        "subtask_selected",
    )
    for index, subtask in enumerate(subtasks[offset:], offset):
        row = top + index - offset
        if row >= top + height:
            break

        selected = state["focus"] == FOCUS_SUBTASKS and index == state["subtask_selected"]
        marker = ">" if selected else " "
        line = f"{marker} {_status_icon(subtask)} {subtask['title']}"
        attr = _attr(curses.A_BOLD if selected else curses.A_NORMAL)
        _add_line(screen, row, left, _truncate(line, width), attr)


def _move_selection(tasks: list[dict], state: dict, direction: int) -> None:
    if state["focus"] == FOCUS_SUBTASKS and tasks:
        subtasks = _focused_subtasks(tasks[state["selected"]])
        state["subtask_selected"] = min(
            max(state["subtask_selected"] + direction, 0),
            max(len(subtasks) - 1, 0),
        )
        return

    state["selected"] = min(
        max(state["selected"] + direction, 0),
        max(len(tasks) - 1, 0),
    )
    state["subtask_selected"] = 0
    state["subtask_offset"] = 0


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
        state["focus"] = FOCUS_TASKS
        state["message"] = f"created task {task['id'][:8]}: {task['title']}"
    except ValueError as error:
        state["message"] = str(error)


def _add_subtask(screen, tasks: list[dict], selected: int, state: dict) -> None:
    task = _selected_task(tasks, selected)
    if not task:
        state["message"] = "no task selected"
        return

    title = _prompt(screen, "Subtask title")
    if not title:
        state["message"] = "cancelled"
        return

    try:
        subtask = service.add_subtask(task["id"], title)
        state["focus"] = FOCUS_SUBTASKS
        state["subtask_selected"] = len(task.get("subtasks", []))
        state["message"] = f"created subtask {subtask['id'][:8]}: {subtask['title']}"
    except ValueError as error:
        state["message"] = str(error)


def _edit_focused(screen, tasks: list[dict], selected: int, state: dict) -> None:
    task = _selected_task(tasks, selected)
    if not task:
        state["message"] = "no task selected"
        return

    if state["focus"] == FOCUS_SUBTASKS:
        subtask = _selected_subtask(task, state)
        if not subtask:
            state["message"] = "no subtask selected"
            return

        title = _prompt(screen, "Subtask title", default=subtask["title"])
        if title is None:
            state["message"] = "cancelled"
            return

        try:
            updated = service.update_subtask(task["id"], subtask["id"], title=title)
            state["message"] = f"updated subtask {updated['id'][:8]}: {updated['title']}"
        except ValueError as error:
            state["message"] = str(error)
        return

    title = _prompt(screen, "Task title", default=task["title"])
    if title is None:
        state["message"] = "cancelled"
        return

    try:
        updated = service.update_task(task["id"], title=title)
        state["message"] = f"updated task {updated['id'][:8]}: {updated['title']}"
    except ValueError as error:
        state["message"] = str(error)


def _update_focused(
    tasks: list[dict],
    selected: int,
    state: dict,
    status: str,
) -> None:
    task = _selected_task(tasks, selected)
    if not task:
        state["message"] = "no task selected"
        return

    try:
        if state["focus"] == FOCUS_SUBTASKS:
            subtask = _selected_subtask(task, state)
            if not subtask:
                state["message"] = "no subtask selected"
                return

            updated = service.update_subtask(task["id"], subtask["id"], status=status)
            state["message"] = f"{updated['status']} subtask {updated['id'][:8]}"
            return

        updated = service.update_task(task["id"], status=status)
        state["message"] = f"{updated['status']} task {updated['id'][:8]}"
    except ValueError as error:
        state["message"] = str(error)


def _remove_focused_subtask(screen, tasks: list[dict], selected: int, state: dict) -> None:
    task = _selected_task(tasks, selected)
    if not task or state["focus"] != FOCUS_SUBTASKS:
        state["message"] = "focus a subtask first"
        return

    subtask = _selected_subtask(task, state)
    if not subtask:
        state["message"] = "no subtask selected"
        return

    answer = _prompt(screen, f"Remove '{subtask['title']}'? type yes")
    if answer != "yes":
        state["message"] = "cancelled"
        return

    try:
        removed = service.remove_subtask(task["id"], subtask["id"])
        state["subtask_selected"] = max(state["subtask_selected"] - 1, 0)
        state["message"] = f"removed subtask {removed['id'][:8]}: {removed['title']}"
    except ValueError as error:
        state["message"] = str(error)


def _selected_task(tasks: list[dict], selected: int) -> dict | None:
    if not tasks:
        return None

    return tasks[min(selected, len(tasks) - 1)]


def _selected_subtask(task: dict, state: dict) -> dict | None:
    subtasks = task.get("subtasks", [])
    if not subtasks:
        return None

    return subtasks[min(state["subtask_selected"], len(subtasks) - 1)]


def _focused_subtasks(task: dict) -> list[dict]:
    return task.get("subtasks", [])


def _mode_message(state: dict) -> str:
    return "showing all tasks" if state["include_all"] else "showing active tasks"


def _task_summary_line(task: dict) -> str:
    domain = task.get("domain")
    domain_text = f" ({domain})" if domain else ""
    return (
        f"{_status_icon(task)} {task['title']}{domain_text} "
        f"{_subtask_summary(task.get('subtasks', []))}"
    )


def _status_icon(task: dict) -> str:
    status = task.get("status")
    if status == "done":
        return "✓"
    if status == "cancelled":
        return "×"
    return "•"


def _subtask_summary(subtasks: list[dict]) -> str:
    if not subtasks:
        return ""

    done = sum(1 for subtask in subtasks if subtask.get("status") == "done")
    return f"[{done}/{len(subtasks)}]"


def _visible_offset(
    items: list[dict],
    state: dict,
    visible_count: int,
    offset_key: str,
    selected_key: str,
) -> int:
    selected = state[selected_key]
    offset = min(state.get(offset_key, 0), selected)
    visible_count = max(visible_count, 1)

    if selected >= offset + visible_count:
        offset = selected - visible_count + 1

    state[offset_key] = max(offset, 0)
    return state[offset_key]


def _prompt(screen, label: str, default: str | None = None) -> str | None:
    height, width = screen.getmaxyx()
    suffix = f" [{default}]" if default is not None else ""
    prompt = f"{label}{suffix}: "
    row = height - 1
    _add_line(screen, row, 0, " " * max(width - 1, 0))
    _add_line(screen, row, 0, _truncate(prompt, width - 1))
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

    attr = _attr(curses.A_BOLD if focused else curses.A_NORMAL)
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


def _wrap(value: str, width: int) -> list[str]:
    return textwrap.wrap(value, width=max(width, 1)) or [""]


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
