"""Levels page: the five domains, plus a character summary at the top."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Digits, Static

from ...graphics import XPBar
from ...screens import PromptScreen
from ..store import DOMAIN_DEFS, title_for_level
from .base import Page

DOMAIN_HOTKEYS = {
    "career": "c",
    "health": "e",
    "learning": "l",
    "creative": "v",
    "social": "o",
}


class DomainSub(Vertical, can_focus=True):
    ALLOW_MAXIMIZE = True
    BINDINGS = [
        ("1", "quick", "Quick +10"),
        ("2", "task", "Task +25"),
        ("3", "big", "Big +60"),
        ("n", "custom", "Custom"),
        ("u", "undo", "Undo"),
    ]

    def __init__(self, domain_id: str, hotkey: str, title: str) -> None:
        super().__init__(id=f"level-{domain_id}", classes=f"block domain domain-{domain_id}")
        self.domain_id = domain_id
        self.domain_title = title
        self.border_title = f"({hotkey}) {title}"

    @property
    def store(self):
        return self.app.store  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="domain-top"):
            yield Digits("1", id="level")
            with Vertical(classes="domain-info"):
                yield XPBar(id="xpbar")
                yield Static("0 / 100 xp", id="stat")

    def commands(self) -> list[tuple[str, str, object]]:
        prefix = self.domain_title
        return [
            (f"{prefix}: Quick Task", "Log a quick task (+10 xp)", self.action_quick),
            (f"{prefix}: Task", "Log a task (+25 xp)", self.action_task),
            (f"{prefix}: Big Task", "Log a big task (+60 xp)", self.action_big),
            (f"{prefix}: Custom Task", "Log a custom task with its own xp", self.action_custom),
            (f"{prefix}: Undo", "Undo the last task", self.action_undo),
        ]

    def action_quick(self) -> None:
        self._grant(10, "Quick task")

    def action_task(self) -> None:
        self._grant(25, "Task")

    def action_big(self) -> None:
        self._grant(60, "Big task")

    def action_custom(self) -> None:
        def handle_amount(title: str, value: str | None) -> None:
            if value is None:
                return

            try:
                amount = int(value)
            except ValueError:
                self.app.notify(f"invalid xp: {value}", severity="error")
                return

            if amount <= 0:
                self.app.notify("xp must be positive", severity="error")
                return

            self._grant(amount, title)

        def handle_title(title: str | None) -> None:
            if not title:
                return

            self.app.push_screen(PromptScreen("XP for this task", default="25"), lambda v: handle_amount(title, v))

        self.app.push_screen(PromptScreen("Task title"), handle_title)

    def action_undo(self) -> None:
        result = self.store.undo_last_xp(self.domain_id)
        if result is None:
            self.app.notify("nothing to undo", severity="warning")
            return

        label, amount = result
        self._refresh_everywhere()
        self.app.notify(f"undid +{amount} xp ({label})", timeout=2)

    def _grant(self, amount: int, label: str) -> None:
        event = self.store.add_xp(self.domain_id, amount, label)
        self._refresh_everywhere()

        if event.domain_leveled_up:
            self.app.notify(f"LEVEL UP! {event.domain.title} is now level {event.domain.level}", timeout=4)
            bar = self.query_one("#xpbar", XPBar)
            bar.flashing = True
            self.set_timer(1.2, lambda: setattr(bar, "flashing", False))
        else:
            self.app.notify(f"+{amount} xp — {label} ({self.domain_title})", timeout=2)

        if event.character_leveled_up:
            self.app.notify(f"CHARACTER LEVEL UP! You are now level {event.character_level}", timeout=5)

    def _refresh_everywhere(self) -> None:
        self.refresh_from_store()
        parent = self.parent
        while parent is not None and not isinstance(parent, Page):
            parent = parent.parent
        if parent is not None:
            parent.refresh_from_store()

    def refresh_from_store(self) -> None:
        domain = self.store.domains[self.domain_id]
        self.query_one("#level", Digits).update(str(domain.level))
        target = domain.xp_to_next()
        bar = self.query_one("#xpbar", XPBar)
        bar.percent = (domain.xp / target) if target else 0.0
        self.query_one("#stat", Static).update(f"{domain.xp} / {target} xp   (total {domain.total_xp})")


class LevelsPage(Page):
    TAB_ID = "levels"
    TAB_TITLE = "Levels"

    BINDINGS = [(DOMAIN_HOTKEYS[domain_id], f"focus_domain('{domain_id}')", title) for domain_id, title, _color in DOMAIN_DEFS]

    def compose(self) -> ComposeResult:
        with Vertical(id="levels-character"):
            with Horizontal(id="levels-character-top"):
                yield Digits("1", id="levels-char-level")
                with Vertical(id="levels-character-info"):
                    yield Static("Novice", id="levels-char-title")
                    yield XPBar(id="levels-char-xpbar")
                    yield Static("0 / 300 xp", id="levels-char-stat")
        with Container(id="levels-grid"):
            for domain_id, title, _color in DOMAIN_DEFS:
                yield DomainSub(domain_id, DOMAIN_HOTKEYS[domain_id], title)

    def action_focus_domain(self, domain_id: str) -> None:
        self.query_one(f"#level-{domain_id}").focus()

    def commands(self) -> list[tuple[str, str, object]]:
        commands: list[tuple[str, str, object]] = []
        for domain_id, title, _color in DOMAIN_DEFS:
            commands.append((f"Focus {title}", f"Switch focus to {title}", lambda d=domain_id: self.action_focus_domain(d)))

        for domain_id, _title, _color in DOMAIN_DEFS:
            widget = self.query_one(f"#level-{domain_id}", DomainSub)
            commands.extend(widget.commands())

        return commands

    def refresh_from_store(self) -> None:
        store = self.store
        level, remaining, target = store.character_level()

        self.query_one("#levels-char-level", Digits).update(str(level))
        self.query_one("#levels-char-title", Static).update(title_for_level(level))
        bar = self.query_one("#levels-char-xpbar", XPBar)
        bar.percent = (remaining / target) if target else 0.0
        self.query_one("#levels-char-stat", Static).update(f"{remaining} / {target} xp   (lifetime {store.character_total_xp()})")

        for domain_id, _title, _color in DOMAIN_DEFS:
            self.query_one(f"#level-{domain_id}", DomainSub).refresh_from_store()
