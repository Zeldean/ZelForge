"""Activity page: a running feed of everything that happened, everywhere."""

from __future__ import annotations

import datetime

from textual.app import ComposeResult
from textual.widgets import RichLog

from .base import Page


class ActivityPage(Page):
    TAB_ID = "activity"
    TAB_TITLE = "Activity"

    def compose(self) -> ComposeResult:
        yield RichLog(id="activity-log", wrap=True, markup=False, auto_scroll=True)

    def refresh_from_store(self) -> None:
        log = self.query_one("#activity-log", RichLog)
        log.clear()
        for timestamp, message in self.store.activity:
            when = datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            log.write(f"[{when}] {message}")
