"""Profile page: a character sheet with aggregate stats and a theme picker."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static

from ...screens import PromptScreen
from ..store import title_for_level
from .base import Page

THEMES = ["ansi-dark", "ansi-light", "nord", "gruvbox", "dracula", "catppuccin-mocha", "tokyo-night"]


class ProfilePage(Page):
    TAB_ID = "profile"
    TAB_TITLE = "Profile"

    BINDINGS = [("n", "rename", "Rename")]

    def compose(self) -> ComposeResult:
        yield Static("", id="profile-name")
        yield Static("", id="profile-stats")
        yield Static("Theme", id="profile-theme-label")
        with Horizontal(id="profile-themes"):
            for theme in THEMES:
                yield Button(theme, id=f"theme-{theme}", classes="theme-btn")

    def commands(self) -> list[tuple[str, str, object]]:
        commands: list[tuple[str, str, object]] = [("Profile: Rename", "Change your character's name", self.action_rename)]
        commands += [(f"Theme: {theme}", f"Switch to the {theme} theme", self._theme_handler(theme)) for theme in THEMES]
        return commands

    def _theme_handler(self, theme: str):
        def handler() -> str:
            self.app.theme = theme
            return f"theme set to {theme}"

        return handler

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("theme-"):
            theme = button_id.removeprefix("theme-")
            self.app.theme = theme
            self.app.notify(f"theme set to {theme}", timeout=2)

    def action_rename(self) -> None:
        def handle(value: str | None) -> None:
            if not value:
                return

            self.store.profile.name = value
            self.refresh_from_store()

        self.app.push_screen(PromptScreen("Character name", default=self.store.profile.name), handle)

    def refresh_from_store(self) -> None:
        store = self.store
        level, _remaining, _target = store.character_level()

        self.query_one("#profile-name", Static).update(f"{store.profile.name}   —   {title_for_level(level)} (Level {level})")

        stats = (
            f"Tasks completed: {store.tasks_completed()} / {len(store.tasks)}\n"
            f"Notes written: {len(store.notes)}\n"
            f"Longest current habit streak: {store.habit_streak()} days\n"
            f"Time logged on sessions: {store.total_session_seconds() // 60} minutes\n"
            f"Lifetime XP: {store.character_total_xp()}"
        )
        self.query_one("#profile-stats", Static).update(stats)
