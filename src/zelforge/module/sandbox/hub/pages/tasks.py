"""Tasks page: a DataTable of tasks. Completing one grants XP to its domain."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import DataTable, Static

from ...screens import PromptScreen
from .base import Page

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class TasksPage(Page):
    TAB_ID = "tasks"
    TAB_TITLE = "Tasks"

    BINDINGS = [
        ("a", "add_task", "Add"),
        ("d", "delete_task", "Delete"),
    ]

    def __init__(self) -> None:
        super().__init__(id="tasks-page")
        self._row_task_ids: list[int] = []

    def compose(self) -> ComposeResult:
        yield Static("a add   enter complete   d delete", classes="page-hint")
        yield DataTable(id="tasks-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Title", "Domain", "Priority", "XP", "Status")

    def initial_focus_target(self):
        return self.query_one(DataTable)

    def commands(self) -> list[tuple[str, str, object]]:
        return [
            ("Tasks: Add", "Add a new task", self.action_add_task),
            ("Tasks: Delete Selected", "Delete the selected task", self.action_delete_task),
        ]

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._complete_selected()

    def action_add_task(self) -> None:
        domain_hint = "/".join(self.store.domains)

        def handle_xp(title: str, domain_id: str, value: str | None) -> None:
            if value is None:
                return

            try:
                xp = int(value)
            except ValueError:
                self.app.notify(f"invalid xp: {value}", severity="error")
                return

            self.store.add_task(title, domain_id, "medium", xp)
            self.refresh_from_store()
            self.app.notify(f"added task '{title}'", timeout=2)

        def handle_domain(title: str, domain_id: str | None) -> None:
            if domain_id is None:
                return

            if domain_id not in self.store.domains:
                self.app.notify(f"unknown domain '{domain_id}' — use one of: {domain_hint}", severity="error")
                return

            self.app.push_screen(PromptScreen("XP reward", default="25"), lambda v: handle_xp(title, domain_id, v))

        def handle_title(title: str | None) -> None:
            if not title:
                return

            self.app.push_screen(PromptScreen(f"Domain ({domain_hint})"), lambda d: handle_domain(title, d))

        self.app.push_screen(PromptScreen("Task title"), handle_title)

    def action_delete_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            self.app.notify("no task selected", severity="warning")
            return

        self.store.delete_task(task_id)
        self.refresh_from_store()

    def _complete_selected(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            return

        event = self.store.complete_task(task_id)
        if event is None:
            self.app.notify("already done", severity="warning")
            return

        self.refresh_from_store()
        if event.domain_leveled_up:
            self.app.notify(f"LEVEL UP! {event.domain.title} is now level {event.domain.level}", timeout=4)
        else:
            self.app.notify(f"+{event.amount} xp — {event.label}", timeout=2)

        if event.character_leveled_up:
            self.app.notify(f"CHARACTER LEVEL UP! You are now level {event.character_level}", timeout=5)

    def _selected_task_id(self) -> int | None:
        table = self.query_one(DataTable)
        row = table.cursor_row
        if row is None or row < 0 or row >= len(self._row_task_ids):
            return None

        return self._row_task_ids[row]

    def refresh_from_store(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self._row_task_ids = []

        tasks = sorted(self.store.tasks, key=lambda t: (t.status == "done", PRIORITY_ORDER.get(t.priority, 1)))
        for task in tasks:
            domain = self.store.domains[task.domain_id]
            table.add_row(task.title, domain.title, task.priority, str(task.xp), task.status)
            self._row_task_ids.append(task.id)
