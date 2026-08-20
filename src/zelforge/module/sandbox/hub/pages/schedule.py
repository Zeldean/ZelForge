"""Schedule page: a day timeline of time blocks (mirrors the zelblock idea)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ...graphics import TimelineRow
from ...screens import PromptScreen
from .base import Page


class SchedulePage(Page):
    TAB_ID = "schedule"
    TAB_TITLE = "Schedule"

    BINDINGS = [
        ("a", "add_block", "Add"),
        ("d", "delete_block", "Delete"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("a add   d delete (by title)", classes="page-hint")
        yield Static(self._ruler(), id="schedule-ruler")
        yield Vertical(id="schedule-rows")

    @staticmethod
    def _ruler() -> str:
        return "  ".join(f"{hour:02}:00" for hour in range(0, 25, 3))

    def commands(self) -> list[tuple[str, str, object]]:
        return [
            ("Schedule: Add Block", "Add a scheduled time block", self.action_add_block),
            ("Schedule: Delete Block", "Delete a scheduled time block by title", self.action_delete_block),
        ]

    def action_add_block(self) -> None:
        domain_hint = "/".join(self.store.domains)

        def handle_end(title: str, domain_id: str, start: float, value: str | None) -> None:
            if value is None:
                return

            try:
                end = float(value)
            except ValueError:
                self.app.notify(f"invalid hour: {value}", severity="error")
                return

            self.store.add_schedule_block(title, domain_id, start, end)
            self.refresh_from_store()

        def handle_start(title: str, domain_id: str, value: str | None) -> None:
            if value is None:
                return

            try:
                start = float(value)
            except ValueError:
                self.app.notify(f"invalid hour: {value}", severity="error")
                return

            self.app.push_screen(PromptScreen("End hour (e.g. 17.5)"), lambda v: handle_end(title, domain_id, start, v))

        def handle_domain(title: str, domain_id: str | None) -> None:
            if domain_id is None:
                return

            if domain_id not in self.store.domains:
                self.app.notify(f"unknown domain — use one of: {domain_hint}", severity="error")
                return

            self.app.push_screen(PromptScreen("Start hour (e.g. 9.5)"), lambda v: handle_start(title, domain_id, v))

        def handle_title(title: str | None) -> None:
            if not title:
                return

            self.app.push_screen(PromptScreen(f"Domain ({domain_hint})"), lambda d: handle_domain(title, d))

        self.app.push_screen(PromptScreen("Block title"), handle_title)

    def action_delete_block(self) -> None:
        def handle(title: str | None) -> None:
            if not title:
                return

            match = next((b for b in self.store.schedule if b.title == title), None)
            if match is None:
                self.app.notify(f"no block titled '{title}'", severity="error")
                return

            self.store.delete_schedule_block(match.id)
            self.refresh_from_store()

        self.app.push_screen(PromptScreen("Title of block to delete"), handle)

    def refresh_from_store(self) -> None:
        container = self.query_one("#schedule-rows", Vertical)
        container.remove_children()

        if not self.store.schedule:
            container.mount(Static("nothing scheduled - press a to add a block", classes="page-hint"))
            return

        for block in self.store.schedule:
            domain = self.store.domains[block.domain_id]
            row = TimelineRow(classes="schedule-row")
            row.start_hour = block.start_hour
            row.end_hour = block.end_hour
            row.color = domain.color
            row.label = f"{block.title} ({domain.title})"
            container.mount(row)
