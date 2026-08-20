"""Achievements page: badges computed live from every other page's data."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from .base import Page


class AchievementsPage(Page):
    TAB_ID = "achievements"
    TAB_TITLE = "Achievements"

    def compose(self) -> ComposeResult:
        yield Container(id="achievements-grid")

    def refresh_from_store(self) -> None:
        grid = self.query_one("#achievements-grid", Container)
        grid.remove_children()

        for _aid, title, description, unlocked in self.store.achievements():
            marker = "✓" if unlocked else "·"
            card = Static(f"{marker} {title}\n{description}", classes="achievement-card")
            card.set_class(unlocked, "achievement-unlocked")
            grid.mount(card)
