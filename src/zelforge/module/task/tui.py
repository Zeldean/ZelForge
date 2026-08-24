"""Task TUI, built on Textual.

Feature parity with the previous curses version: a task list on the left,
details (meta, description, subtasks) on the right, add/edit/done/cancel/
reopen for both tasks and subtasks, and the same interactive fuzzy domain
picker for assigning a task's domain.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from zelforge.core import domains as domain_store
from zelforge.core.tui.components import ConfirmScreen, DomainPickerScreen, PromptScreen

from . import service
from .models import DEFAULT_PRIORITY, TASK_PRIORITIES, get_priority_label


def run() -> None:
    """Run the task TUI."""
    TaskApp().run()


def _domain_label(code: str | None, empty: str = "-") -> str:
    if not code:
        return empty

    return domain_store.get_domain_name(code)


def _subtask_summary(subtasks: list[dict]) -> str:
    if not subtasks:
        return ""

    done = sum(1 for subtask in subtasks if subtask.get("status") == "done")
    return f"[{done}/{len(subtasks)}]"


def _status_icon(item: dict) -> str:
    status = item.get("status")
    if status == "done":
        return "✓"
    if status == "cancelled":
        return "×"
    return "•"


def _task_summary_line(task: dict) -> str:
    domain = _domain_label(task.get("domain"), empty="")
    domain_text = f" ({domain})" if domain else ""
    return f"{_status_icon(task)} {task['title']}{domain_text} {_subtask_summary(task.get('subtasks', []))}"


def _subtask_summary_line(subtask: dict) -> str:
    return f"{_status_icon(subtask)} {subtask['title']}"


class TaskApp(App):
    """Browse tasks and subtasks, edit them, and change their status."""

    CSS_PATH = Path(__file__).parent / "tui.tcss"
    TITLE = "ZelTask"

    BINDINGS = [
        ("v", "toggle_mode", "Active/All"),
        ("a", "add_task", "Add Task"),
        ("s", "add_subtask", "Add Subtask"),
        ("e", "edit_focused", "Edit"),
        ("d", "mark_status('done')", "Done"),
        ("c", "mark_status('cancelled')", "Cancel"),
        ("o", "mark_status('active')", "Reopen"),
        ("x", "remove_subtask", "Remove Subtask"),
        ("r", "refresh", "Refresh"),
        ("colon", "command_palette", "Commands"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.include_all = False
        self.tasks: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="mode-label")
        with Horizontal(id="panes"):
            with Vertical(id="task-pane"):
                yield ListView(id="task-list")
            with Vertical(id="detail-pane"):
                yield Static("", id="task-meta")
                yield Static("", id="task-description")
                yield Static("Subtasks", id="subtasks-label")
                yield ListView(id="subtask-list")
        yield Footer()

    def on_mount(self) -> None:
        # ansi-dark maps colors to the terminal's own ANSI palette and
        # leaves the background untouched (transparent here), instead of
        # painting Textual's truecolor theme over the terminal.
        self.theme = "ansi-dark"
        self.refresh_data(preserve_selection=False)

    def refresh_data(self, preserve_selection: bool = True) -> None:
        self.tasks = service.list_tasks(include_all=self.include_all)
        self.query_one("#mode-label", Static).update(f"showing {'all' if self.include_all else 'active'} tasks")
        self._render_task_list(preserve_selection)
        self._render_detail()

    def _render_task_list(self, preserve_selection: bool) -> None:
        list_view = self.query_one("#task-list", ListView)
        previous_index = list_view.index or 0
        list_view.clear()
        for task in self.tasks:
            list_view.append(ListItem(Label(_task_summary_line(task))))

        if self.tasks:
            list_view.index = min(previous_index, len(self.tasks) - 1) if preserve_selection else 0

    def _render_detail(self) -> None:
        meta = self.query_one("#task-meta", Static)
        description = self.query_one("#task-description", Static)
        subtask_list = self.query_one("#subtask-list", ListView)

        task = self._selected_task()
        if task is None:
            meta.update("No tasks")
            description.update("")
            subtask_list.clear()
            return

        meta.update(
            f"{task['title']}\n"
            f"id        {task['id'][:8]}\n"
            f"status    {task['status']}\n"
            f"priority  {get_priority_label(task.get('priority'))}\n"
            f"domain    {_domain_label(task.get('domain'))}\n"
            f"tags      {', '.join(task.get('tags', [])) or '-'}"
        )
        description.update("\n".join(textwrap.wrap(task.get("description") or "-", width=70)) or "-")

        previous_index = subtask_list.index or 0
        subtask_list.clear()
        for subtask in task.get("subtasks", []):
            subtask_list.append(ListItem(Label(_subtask_summary_line(subtask))))

        subtasks = task.get("subtasks", [])
        if subtasks:
            subtask_list.index = min(previous_index, len(subtasks) - 1)

    def _selected_task(self) -> dict | None:
        if not self.tasks:
            return None

        list_view = self.query_one("#task-list", ListView)
        index = min(list_view.index or 0, len(self.tasks) - 1)
        return self.tasks[index]

    def _selected_subtask(self) -> dict | None:
        task = self._selected_task()
        if task is None:
            return None

        subtasks = task.get("subtasks", [])
        if not subtasks:
            return None

        subtask_list = self.query_one("#subtask-list", ListView)
        index = min(subtask_list.index or 0, len(subtasks) - 1)
        return subtasks[index]

    def _subtasks_focused(self) -> bool:
        return self.focused is self.query_one("#subtask-list", ListView)

    # --- actions -------------------------------------------------------

    def action_toggle_mode(self) -> None:
        self.include_all = not self.include_all
        self.refresh_data(preserve_selection=False)

    def action_refresh(self) -> None:
        self.refresh_data(preserve_selection=True)
        self.notify("refreshed", timeout=1)

    def action_add_task(self) -> None:
        def handle_domain(title: str, priority: int, domain: str | None) -> None:
            if domain is None:
                self.notify("cancelled", timeout=1)
                return

            try:
                task = service.create_task(title=title, priority=priority, domain=domain)
            except ValueError as error:
                self.notify(str(error), severity="error")
                return

            self.include_all = False
            self.refresh_data(preserve_selection=False)
            self.notify(f"created task {task['id'][:8]}: {task['title']}", timeout=2)

        def handle_priority(title: str, value: str | None) -> None:
            if value is None:
                self.notify("cancelled", timeout=1)
                return

            try:
                priority = int(value)
            except ValueError:
                priority = DEFAULT_PRIORITY

            self.push_screen(DomainPickerScreen(), lambda domain: handle_domain(title, priority, domain))

        def handle_title(title: str | None) -> None:
            if not title:
                self.notify("cancelled", timeout=1)
                return

            options = "  ".join(f"{value} {label}" for value, label in TASK_PRIORITIES.items())
            self.push_screen(PromptScreen(f"Priority ({options})", default=str(DEFAULT_PRIORITY)), lambda v: handle_priority(title, v))

        self.push_screen(PromptScreen("Task title"), handle_title)

    def action_add_subtask(self) -> None:
        task = self._selected_task()
        if task is None:
            self.notify("no task selected", severity="warning")
            return

        def handle(title: str | None) -> None:
            if not title:
                self.notify("cancelled", timeout=1)
                return

            try:
                subtask = service.add_subtask(task["id"], title)
            except ValueError as error:
                self.notify(str(error), severity="error")
                return

            self.refresh_data(preserve_selection=True)
            self.query_one("#subtask-list", ListView).focus()
            self.notify(f"created subtask {subtask['id'][:8]}: {subtask['title']}", timeout=2)

        self.push_screen(PromptScreen("Subtask title"), handle)

    def action_edit_focused(self) -> None:
        task = self._selected_task()
        if task is None:
            self.notify("no task selected", severity="warning")
            return

        if self._subtasks_focused():
            subtask = self._selected_subtask()
            if subtask is None:
                self.notify("no subtask selected", severity="warning")
                return

            def handle_subtask(title: str | None) -> None:
                if title is None:
                    return

                try:
                    updated = service.update_subtask(task["id"], subtask["id"], title=title)
                except ValueError as error:
                    self.notify(str(error), severity="error")
                    return

                self.refresh_data(preserve_selection=True)
                self.notify(f"updated subtask {updated['id'][:8]}: {updated['title']}", timeout=2)

            self.push_screen(PromptScreen("Subtask title", default=subtask["title"]), handle_subtask)
            return

        def handle_task(title: str | None) -> None:
            if title is None:
                return

            try:
                updated = service.update_task(task["id"], title=title)
            except ValueError as error:
                self.notify(str(error), severity="error")
                return

            self.refresh_data(preserve_selection=True)
            self.notify(f"updated task {updated['id'][:8]}: {updated['title']}", timeout=2)

        self.push_screen(PromptScreen("Task title", default=task["title"]), handle_task)

    def action_mark_status(self, status: str) -> None:
        task = self._selected_task()
        if task is None:
            self.notify("no task selected", severity="warning")
            return

        try:
            if self._subtasks_focused():
                subtask = self._selected_subtask()
                if subtask is None:
                    self.notify("no subtask selected", severity="warning")
                    return

                updated = service.update_subtask(task["id"], subtask["id"], status=status)
                self.refresh_data(preserve_selection=True)
                self.notify(f"{updated['status']} subtask {updated['id'][:8]}", timeout=2)
                return

            updated = service.update_task(task["id"], status=status)
            self.refresh_data(preserve_selection=True)
            self.notify(f"{updated['status']} task {updated['id'][:8]}", timeout=2)
        except ValueError as error:
            self.notify(str(error), severity="error")

    def action_remove_subtask(self) -> None:
        task = self._selected_task()
        if task is None or not self._subtasks_focused():
            self.notify("focus a subtask first", severity="warning")
            return

        subtask = self._selected_subtask()
        if subtask is None:
            self.notify("no subtask selected", severity="warning")
            return

        def handle(confirmed: bool) -> None:
            if not confirmed:
                self.notify("cancelled", timeout=1)
                return

            try:
                removed = service.remove_subtask(task["id"], subtask["id"])
            except ValueError as error:
                self.notify(str(error), severity="error")
                return

            self.refresh_data(preserve_selection=True)
            self.notify(f"removed subtask {removed['id'][:8]}: {removed['title']}", timeout=2)

        self.push_screen(ConfirmScreen(f"Remove '{subtask['title']}'?"), handle)


if __name__ == "__main__":
    run()
