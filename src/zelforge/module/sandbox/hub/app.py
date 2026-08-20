"""Hub: one TUI mixing tasks, trackers, leveling, notes, timers, a
schedule, a fake repo dashboard, a character sheet, and an activity feed —
all reading and writing one shared in-memory `Store` so completing a task
actually grants XP, a habit "done day" actually grants XP, stopping a timer
actually grants XP, and the Home/Activity pages actually see all of it.

Navigation is a `TabbedContent` bar (click a tab, or `ctrl+left`/`right` to
cycle) rather than per-page global hotkeys — with 11 pages each carrying
their own local keymap, auditing global letters for zero collisions (the
approach used in life_app.py/xp_app.py) stops being worth it. Each page is
still a focusable `Page` widget with its own `BINDINGS`, exactly like every
other block in this module; the app just focuses the active page's `Page`
on every tab switch instead of a hotkey doing it.

Nothing here is real. See `hub/store.py` and the sandbox README for what
the real version would defer to.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane

from ..commands import ActionListProvider
from .pages.achievements import AchievementsPage
from .pages.activity import ActivityPage
from .pages.base import Page
from .pages.home import HomePage
from .pages.levels import LevelsPage
from .pages.notes import NotesPage
from .pages.profile import ProfilePage
from .pages.repos import ReposPage
from .pages.schedule import SchedulePage
from .pages.tasks import TasksPage
from .pages.timer import TimerPage
from .pages.trackers import TrackersPage
from .store import Store

PAGES: list[type[Page]] = [
    HomePage,
    TasksPage,
    TrackersPage,
    LevelsPage,
    NotesPage,
    TimerPage,
    AchievementsPage,
    SchedulePage,
    ReposPage,
    ProfilePage,
    ActivityPage,
]


def run() -> None:
    """Run the Hub TUI."""
    HubApp().run()


class HubApp(App):
    """A showcase of what a combined, cross-linked ZelForge TUI could look like."""

    CSS_PATH = Path(__file__).parent / "hub.tcss"
    TITLE = "Hub"
    COMMANDS = App.COMMANDS | {ActionListProvider}

    BINDINGS = [
        ("ctrl+right", "next_page", "Next Page"),
        ("ctrl+left", "prev_page", "Prev Page"),
        ("colon", "command_palette", "Commands"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.store = Store()
        self._last_focused_tab: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            for page_cls in PAGES:
                with TabPane(page_cls.TAB_TITLE, id=page_cls.TAB_ID):
                    yield page_cls()
        yield Footer()

    def on_mount(self) -> None:
        # ansi-dark maps colors to the terminal's own ANSI palette and
        # leaves the background untouched (transparent here), instead of
        # painting Textual's truecolor theme over the terminal. Switch via
        # the command palette ("Change theme") or the Profile page.
        self.theme = "ansi-dark"
        self.call_after_refresh(self._focus_active_page)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        # Focusing a widget inside a TabPane appears to itself trigger a
        # further TabActivated (reproduced empirically — a single explicit
        # switch fires this handler 2-3 times), which would otherwise chain
        # into repeated, possibly-stale focus() calls. Two guards:
        # skip if this is a re-fire for a tab we already handled, and defer
        # the actual focus() call past the current refresh so it isn't
        # racing TabbedContent's own active-pane bookkeeping.
        tabbed = self.query_one("#tabs", TabbedContent)
        if tabbed.active == self._last_focused_tab:
            return

        self._last_focused_tab = tabbed.active
        self.call_after_refresh(self._focus_active_page)

    def _focus_active_page(self) -> None:
        tabbed = self.query_one("#tabs", TabbedContent)
        pane = tabbed.active_pane
        if pane is None:
            return

        page = pane.query_one(Page)
        page.refresh_from_store()
        page.initial_focus_target().focus()

    def action_next_page(self) -> None:
        self._shift_page(1)

    def action_prev_page(self) -> None:
        self._shift_page(-1)

    def _shift_page(self, direction: int) -> None:
        tabbed = self.query_one("#tabs", TabbedContent)
        ids = [page_cls.TAB_ID for page_cls in PAGES]
        if tabbed.active not in ids:
            return

        index = ids.index(tabbed.active)
        tabbed.active = ids[(index + direction) % len(ids)]

    def command_list(self) -> list[tuple[str, str, object]]:
        commands: list[tuple[str, str, object]] = [("Quit", "Quit the app", self.action_quit)]

        for page_cls in PAGES:
            commands.append((f"Go: {page_cls.TAB_TITLE}", f"Switch to the {page_cls.TAB_TITLE} page", self._goto(page_cls.TAB_ID)))

        tabbed = self.query_one("#tabs", TabbedContent)
        pane = tabbed.active_pane
        if pane is not None:
            page = pane.query_one(Page)
            if hasattr(page, "commands"):
                commands.extend(page.commands())

        return commands

    def _goto(self, tab_id: str):
        def _handler(screen) -> str:
            tabbed = self.query_one("#tabs", TabbedContent)
            tabbed.active = tab_id
            return f"switched to {tab_id}"

        return _handler


if __name__ == "__main__":
    run()
