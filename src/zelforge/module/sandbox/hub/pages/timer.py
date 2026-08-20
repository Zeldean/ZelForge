"""Timer page: one block per domain — a big total, a scrolling session
history below it (fixed height, doesn't grow the block), a couple of preset
one-key session starts, and a normal start that asks for a title."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Digits, Static

from ...screens import PromptScreen
from ..store import DOMAIN_DEFS
from .base import Page

PRESETS = ["Subscriptions", "Testing"]

DOMAIN_HOTKEYS = {
    "career": "c",
    "health": "e",
    "learning": "l",
    "creative": "v",
    "social": "o",
}


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(seconds, 0), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    return f"{minutes}:{secs:02}"


class DomainTimerBlock(Vertical, can_focus=True):
    ALLOW_MAXIMIZE = True
    BINDINGS = [
        ("1", "start_preset(0)", f"Start {PRESETS[0]}"),
        ("2", "start_preset(1)", f"Start {PRESETS[1]}"),
        ("t", "start_custom", "Start"),
        ("x", "stop", "Stop"),
    ]

    def __init__(self, domain_id: str, hotkey: str, title: str) -> None:
        super().__init__(id=f"timer-{domain_id}", classes=f"block timer-domain domain-{domain_id}")
        self.domain_id = domain_id
        self.domain_title = title
        self.border_title = f"({hotkey}) {title}"

    @property
    def store(self):
        return self.app.store  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        yield Digits("0:00", id="timer-total")
        yield VerticalScroll(id="timer-sessions")

    def on_mount(self) -> None:
        self.set_interval(1, self._tick)

    def _tick(self) -> None:
        if self.store.active_session(self.domain_id) is not None:
            self.refresh_from_store()

    def commands(self) -> list[tuple[str, str, object]]:
        prefix = self.domain_title
        commands = [
            (f"{prefix}: Start {name}", f"Start a '{name}' session", self._preset_handler(index))
            for index, name in enumerate(PRESETS)
        ]
        commands += [
            (f"{prefix}: Start (Custom Title)", "Start a session with a custom title", self.action_start_custom),
            (f"{prefix}: Stop", "Stop the running session", self.action_stop),
        ]
        return commands

    def _preset_handler(self, index: int):
        return lambda: self.action_start_preset(index)

    def action_start_preset(self, index: int) -> None:
        title = PRESETS[index]
        self.store.start_session(self.domain_id, title)
        self.refresh_from_store()
        self.app.notify(f"started '{title}'", timeout=2)

    def action_start_custom(self) -> None:
        def handle(title: str | None) -> None:
            if not title:
                return

            self.store.start_session(self.domain_id, title)
            self.refresh_from_store()
            self.app.notify(f"started '{title}'", timeout=2)

        self.app.push_screen(PromptScreen("Session title"), handle)

    def action_stop(self) -> None:
        event = self.store.stop_session(self.domain_id)
        self.refresh_from_store()
        if event is None:
            self.app.notify("stopped (under a minute, no xp)", timeout=2)
            return

        if event.domain_leveled_up:
            self.app.notify(f"LEVEL UP! {event.domain.title} is now level {event.domain.level}", timeout=4)
        else:
            self.app.notify(f"+{event.amount} xp — {event.label}", timeout=2)

        if event.character_leveled_up:
            self.app.notify(f"CHARACTER LEVEL UP! You are now level {event.character_level}", timeout=5)

    def refresh_from_store(self) -> None:
        total = self.store.domain_session_seconds(self.domain_id)
        self.query_one("#timer-total", Digits).update(_format_duration(total))

        container = self.query_one("#timer-sessions", VerticalScroll)
        container.remove_children()

        sessions = list(reversed(self.store.domain_sessions(self.domain_id)))
        if not sessions:
            container.mount(Static("no sessions yet", classes="page-hint"))
            return

        for session in sessions:
            duration = _format_duration(session.duration_seconds())
            marker = "●" if session.running else " "
            row = Static(f"{marker} {session.title}  {duration}", classes="session-row")
            row.set_class(session.running, "session-running")
            container.mount(row)


class TimerPage(Page):
    TAB_ID = "timer"
    TAB_TITLE = "Timer"

    BINDINGS = [(DOMAIN_HOTKEYS[domain_id], f"focus_domain('{domain_id}')", title) for domain_id, title, _color in DOMAIN_DEFS]

    def compose(self) -> ComposeResult:
        with Container(id="timer-grid"):
            for domain_id, title, _color in DOMAIN_DEFS:
                yield DomainTimerBlock(domain_id, DOMAIN_HOTKEYS[domain_id], title)

    def action_focus_domain(self, domain_id: str) -> None:
        self.query_one(f"#timer-{domain_id}").focus()

    def commands(self) -> list[tuple[str, str, object]]:
        commands: list[tuple[str, str, object]] = []
        for domain_id, title, _color in DOMAIN_DEFS:
            commands.append((f"Focus {title}", f"Switch focus to {title}", lambda d=domain_id: self.action_focus_domain(d)))

        for domain_id, _title, _color in DOMAIN_DEFS:
            widget = self.query_one(f"#timer-{domain_id}", DomainTimerBlock)
            commands.extend(widget.commands())

        return commands

    def refresh_from_store(self) -> None:
        for domain_id, _title, _color in DOMAIN_DEFS:
            self.query_one(f"#timer-{domain_id}", DomainTimerBlock).refresh_from_store()
