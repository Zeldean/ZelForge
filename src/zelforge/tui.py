"""ZelForge launcher TUI."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static

from zelforge.module.timer.service import get_status
from zelforge.module.task.service import list_tasks

def get_time_string() -> str:
    total_time = sum(timer["total_seconds"] for timer in get_status())
    h, r = divmod(total_time, 3600)
    m, s = divmod(r, 60)

    time_string = f"Timer Total: {h:02d}:{m:02d}:{s:02d}"
    return time_string

def get_task_string() -> str:
    total = len(list_tasks())

    task_string = f"Tasks: {total}"
    return task_string


class Home(App):
    """A Textual app to act as the HOME screen."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("r", "refresh", "Refresh the page"),
    ]

    # --- widgets -------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("Timer Total: 00:00:00", id="total_time")
        yield Static("Tasks: 0", id="total_tasks")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_total_time()
        self._refresh_total_tasks()

    # --- actions -------------------------------------------------------

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_refresh(self) -> None:
        self._refresh_total_time()
        self._refresh_total_tasks()

    # --- refresh helpers -------------------------------------------------

    def _refresh_total_time(self) -> None:
        time_string = get_time_string()
        self.query_one("#total_time", Static).update(time_string)

    def _refresh_total_tasks(self) -> None:
        task_string = get_task_string()
        self.query_one("#total_tasks", Static).update(task_string)


def run() -> None:
    app = Home()
    app.run()


if __name__ == "__main__":
    app = Home()
    app.run()
