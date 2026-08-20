"""Home page: a rollup of everything happening on every other page."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Digits, Static

from ...graphics import XPBar
from ..store import title_for_level
from .base import Page


class HomePage(Page):
    TAB_ID = "home"
    TAB_TITLE = "Home"

    def compose(self) -> ComposeResult:
        with Vertical(id="home-character"):
            with Horizontal():
                yield Digits("1", id="home-level")
                with Vertical(id="home-character-info"):
                    yield Static("Novice", id="home-title")
                    yield XPBar(id="home-xpbar")
                    yield Static("", id="home-xpstat")
        with Horizontal(id="home-stats"):
            yield Static("", id="home-stat-tasks", classes="home-card")
            yield Static("", id="home-stat-water", classes="home-card")
            yield Static("", id="home-stat-mood", classes="home-card")
            yield Static("", id="home-stat-streak", classes="home-card")
            yield Static("", id="home-stat-notes", classes="home-card")
            yield Static("", id="home-stat-timers", classes="home-card")
        yield Static("Recent activity", id="home-activity-title")
        yield Static("", id="home-activity")

    def refresh_from_store(self) -> None:
        store = self.store
        level, remaining, target = store.character_level()

        self.query_one("#home-level", Digits).update(str(level))
        self.query_one("#home-title", Static).update(title_for_level(level))

        bar = self.query_one("#home-xpbar", XPBar)
        bar.percent = (remaining / target) if target else 0.0
        self.query_one("#home-xpstat", Static).update(f"{remaining} / {target} xp   (lifetime {store.character_total_xp()})")

        done = store.tasks_completed()
        self.query_one("#home-stat-tasks", Static).update(f"Tasks\n{done}/{len(store.tasks)} done")
        self.query_one("#home-stat-water", Static).update(f"Water\n{store.water_total_ml}ml / {store.water_goal_ml}ml")
        mood = store.mood_entries[-1] if store.mood_entries else "-"
        self.query_one("#home-stat-mood", Static).update(f"Mood\n{mood} / 5")
        self.query_one("#home-stat-streak", Static).update(f"Habit streak\n{store.habit_streak()} days")
        self.query_one("#home-stat-notes", Static).update(f"Notes\n{len(store.notes)} written")
        running = sum(1 for domain_id in store.domains if store.active_session(domain_id) is not None)
        self.query_one("#home-stat-timers", Static).update(f"Sessions\n{running} running")

        recent = list(reversed(store.activity[-8:]))
        lines = [message for _timestamp, message in recent]
        self.query_one("#home-activity", Static).update("\n".join(lines) if lines else "nothing yet")
