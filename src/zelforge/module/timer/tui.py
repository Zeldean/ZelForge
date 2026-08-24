"""Timer TUI, built on Textual.

Feature parity with the previous curses version: a list of timers on the
left, that timer's sessions (as cards) on the right, date/range navigation,
and start/stop with a title prompt. Ticks every second so an active
session's duration stays live without needing a keypress.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from zelforge.core.tui.components import PromptScreen

from . import service


def run() -> None:
    """Run the timer TUI."""
    TimerApp().run()


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
    running = " ● running" if _timer_has_active_session(timer) else ""
    return f"{timer.get('name') or '-'} ({timer.get('code') or '-'}){running}  {_format_duration(group['total_seconds'])}"


class SessionCard(Vertical):
    """One session, shown as a bordered card (title, time range, duration)."""

    DEFAULT_CSS = """
    SessionCard {
        border: round $primary-muted;
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }
    SessionCard.active {
        border: round $accent;
    }
    SessionCard #session-title {
        text-style: bold;
        text-align: center;
    }
    SessionCard.active #session-title {
        color: $accent;
    }
    SessionCard #session-meta {
        color: $text-muted;
        text-align: center;
    }
    """

    def __init__(self, session: dict, include_date: bool) -> None:
        super().__init__()
        self._session = session
        self._include_date = include_date
        if session.get("active"):
            self.add_class("active")

    def compose(self) -> ComposeResult:
        yield Static(id="session-title")
        yield Static(id="session-meta")

    def on_mount(self) -> None:
        self.update_session(self._session, self._include_date)

    def update_session(self, session: dict, include_date: bool) -> None:
        """Refresh this card's text in place — no remount, no flicker."""
        self._session = session
        self._include_date = include_date
        self.set_class(bool(session.get("active")), "active")

        marker = "●" if session.get("active") else "•"
        self.query_one("#session-title", Static).update(f"{marker} {session['title']}")

        started = _format_time(session["started_at"], include_date)
        stopped = "active" if session["active"] else _format_time(session["stopped_at"], include_date)
        duration = _format_duration(session["duration_seconds"])
        self.query_one("#session-meta", Static).update(f"{started} -> {stopped}    {duration}")


class TimerApp(App):
    """Browse timers, review sessions, and start/stop the selected one."""

    CSS_PATH = Path(__file__).parent / "tui.tcss"
    TITLE = "ZelTimer"

    BINDINGS = [
        ("p", "shift_range(-1)", "Prev"),
        ("n", "shift_range(1)", "Next"),
        ("t", "today", "Today"),
        ("d", "set_date", "Set Date"),
        ("g", "set_range", "Set Range"),
        ("r", "refresh", "Refresh"),
        ("s", "toggle_selected", "Start/Stop"),
        ("colon", "command_palette", "Commands"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.start_date = date.today()
        self.end_date = date.today()
        self.groups: list[dict] = []
        self._timer_labels: list[Label] = []
        self._session_cards: list[SessionCard] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="range-label")
        with Horizontal(id="panes"):
            with Vertical(id="timer-pane"):
                yield ListView(id="timer-list")
            with Vertical(id="session-pane"):
                yield Static("", id="session-header")
                yield VerticalScroll(id="session-list")
        yield Footer()

    def on_mount(self) -> None:
        # ansi-dark maps colors to the terminal's own ANSI palette and
        # leaves the background untouched (transparent here), instead of
        # painting Textual's truecolor theme over the terminal.
        self.theme = "ansi-dark"
        self.set_interval(1, self._tick)
        self.refresh_data(preserve_selection=False)

    def _tick(self) -> None:
        # A full clear-and-rebuild every second (the old approach) flickers
        # the whole screen and drops any mouse-hover state, since it
        # destroys and recreates every widget. Update label/card text in
        # place instead — only falls back to a full rebuild if the set of
        # timers/sessions itself changed shape (rare: only via an action).
        if not any(_timer_has_active_session(group.get("timer", {})) for group in self.groups):
            return

        single_day = self.start_date == self.end_date
        try:
            groups = service.get_status(
                date_filter=self.start_date if single_day else None,
                start_date=None if single_day else self.start_date,
                end_date=None if single_day else self.end_date,
            )
        except ValueError:
            return

        if len(groups) != len(self._timer_labels):
            self.groups = groups
            self.refresh_data(preserve_selection=True)
            return

        self.groups = groups
        for label, group in zip(self._timer_labels, self.groups):
            label.update(_timer_summary(group))

        self._tick_session_detail()

    def _tick_session_detail(self) -> None:
        if not self.groups:
            return

        list_view = self.query_one("#timer-list", ListView)
        index = min(list_view.index or 0, len(self.groups) - 1)
        group = self.groups[index]
        timer = group.get("timer", {})
        sessions = group.get("sessions", [])

        if len(sessions) != len(self._session_cards):
            self._render_session_detail()
            return

        self.query_one("#session-header", Static).update(
            f"{timer.get('name') or '-'}   code {timer.get('code') or '-'}   total {_format_duration(group['total_seconds'])}"
        )

        include_date = self.start_date != self.end_date
        for card, session in zip(self._session_cards, sessions):
            card.update_session(session, include_date)

    def refresh_data(self, preserve_selection: bool = True) -> None:
        single_day = self.start_date == self.end_date
        try:
            self.groups = service.get_status(
                date_filter=self.start_date if single_day else None,
                start_date=None if single_day else self.start_date,
                end_date=None if single_day else self.end_date,
            )
        except ValueError as error:
            self.notify(str(error), severity="error")
            return

        self.query_one("#range-label", Static).update(self._range_label())
        self._render_timer_list(preserve_selection)
        self._render_session_detail()

    def _render_timer_list(self, preserve_selection: bool) -> None:
        list_view = self.query_one("#timer-list", ListView)
        previous_index = list_view.index or 0
        list_view.clear()
        self._timer_labels = []
        for group in self.groups:
            label = Label(_timer_summary(group))
            self._timer_labels.append(label)
            list_view.append(ListItem(label))

        if self.groups:
            list_view.index = min(previous_index, len(self.groups) - 1) if preserve_selection else 0

    def _render_session_detail(self) -> None:
        header = self.query_one("#session-header", Static)
        container = self.query_one("#session-list", VerticalScroll)
        container.remove_children()
        self._session_cards = []

        if not self.groups:
            header.update("No timers to display")
            return

        list_view = self.query_one("#timer-list", ListView)
        index = min(list_view.index or 0, len(self.groups) - 1)
        group = self.groups[index]
        timer = group.get("timer", {})
        header.update(f"{timer.get('name') or '-'}   code {timer.get('code') or '-'}   total {_format_duration(group['total_seconds'])}")

        sessions = group.get("sessions", [])
        if not sessions:
            container.mount(Static("No sessions in this range"))
            return

        include_date = self.start_date != self.end_date
        for session in sessions:
            card = SessionCard(session, include_date)
            self._session_cards.append(card)
            container.mount(card)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        # Fires as the cursor moves (arrow keys or mouse), not just on
        # Enter/click — keep the detail panel in sync with the highlighted
        # timer the same way the old curses version redrew every loop.
        if event.list_view.id == "timer-list":
            self._render_session_detail()

    # --- actions -------------------------------------------------------

    def action_shift_range(self, days: int) -> None:
        delta = timedelta(days=days)
        self.start_date += delta
        self.end_date += delta
        self.refresh_data(preserve_selection=False)

    def action_today(self) -> None:
        today = date.today()
        self.start_date = today
        self.end_date = today
        self.refresh_data(preserve_selection=False)
        self.notify("showing today", timeout=2)

    def action_set_date(self) -> None:
        def handle(value: str | None) -> None:
            if value is None:
                return

            try:
                selected = date.fromisoformat(value)
            except ValueError:
                self.notify(f"invalid date: {value}", severity="error")
                return

            self.start_date = selected
            self.end_date = selected
            self.refresh_data(preserve_selection=False)

        self.push_screen(PromptScreen("Date (YYYY-MM-DD)", default=self.start_date.isoformat()), handle)

    def action_set_range(self) -> None:
        def handle_end(start: date, value: str | None) -> None:
            if value is None:
                return

            try:
                end = date.fromisoformat(value)
            except ValueError:
                self.notify(f"invalid date: {value}", severity="error")
                return

            if start > end:
                self.notify("start date cannot be after end date", severity="error")
                return

            self.start_date = start
            self.end_date = end
            self.refresh_data(preserve_selection=False)

        def handle_start(value: str | None) -> None:
            if value is None:
                return

            try:
                start = date.fromisoformat(value)
            except ValueError:
                self.notify(f"invalid date: {value}", severity="error")
                return

            self.push_screen(PromptScreen("End date", default=self.end_date.isoformat()), lambda v: handle_end(start, v))

        self.push_screen(PromptScreen("Start date", default=self.start_date.isoformat()), handle_start)

    def action_refresh(self) -> None:
        self.refresh_data(preserve_selection=True)
        self.notify("refreshed", timeout=1)

    def action_toggle_selected(self) -> None:
        self._toggle_selected()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._toggle_selected()

    def _toggle_selected(self) -> None:
        if not self.groups:
            self.notify("no timers to select", severity="warning")
            return

        list_view = self.query_one("#timer-list", ListView)
        index = min(list_view.index or 0, len(self.groups) - 1)
        group = self.groups[index]
        timer = group.get("timer", {})
        timer_ref = timer.get("id")
        if not timer_ref:
            self.notify("selected timer is missing an id", severity="error")
            return

        if _timer_has_active_session(timer):
            try:
                session = service.stop_timer(timer_ref)
            except ValueError as error:
                self.notify(str(error), severity="error")
                return

            self.notify(f"stopped {timer.get('name')}: {session['title']} ({_format_duration(session['duration_seconds'])})", timeout=3)
            self.refresh_data(preserve_selection=True)
            return

        def handle(title: str | None) -> None:
            if title is None:
                return

            try:
                session = service.start_timer(timer_ref, title=title)
            except ValueError as error:
                self.notify(str(error), severity="error")
                return

            self.notify(f"started {timer.get('name')}: {session['title']}", timeout=2)
            self.start_date = date.today()
            self.end_date = date.today()
            self.refresh_data(preserve_selection=True)

        self.push_screen(PromptScreen("Session title", default=timer.get("name") or ""), handle)

    def _is_single_day(self) -> bool:
        return self.start_date == self.end_date

    def _range_label(self) -> str:
        if self._is_single_day():
            return self.start_date.isoformat()

        return f"{self.start_date.isoformat()} -> {self.end_date.isoformat()}"


if __name__ == "__main__":
    run()
