"""Base class shared by every Hub page."""

from __future__ import annotations

from textual.containers import Vertical

from ..store import Store


class Page(Vertical, can_focus=True):
    """One tab's content.

    Subclasses set their own `BINDINGS` — those only fire while the page is
    focused, which `HubApp` does automatically whenever its tab becomes
    active (same "focused widget's BINDINGS shadow the app's" mechanic used
    throughout this module). Read/write shared state via `self.store`.

    Override `refresh_from_store()` to pull fresh data every time the page
    is switched to (used by pages like Achievements/Activity/Home that show
    data owned by other pages).
    """

    @property
    def store(self) -> Store:
        return self.app.store  # type: ignore[attr-defined]

    def refresh_from_store(self) -> None:
        pass

    def initial_focus_target(self):
        """Widget to focus when this page's tab becomes active.

        Defaults to the page itself. Override to return an interactive
        child instead (e.g. a `DataTable`) — unclaimed keys still bubble up
        to this page's own `BINDINGS`, verified empirically, so the page's
        shortcuts keep working even though the child holds actual focus.
        """
        return self
