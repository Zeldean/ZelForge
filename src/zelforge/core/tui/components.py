"""Shared Textual modal screens for ZelForge module TUIs.

Kept intentionally small — one prompt, one confirm. Modules that use this
(currently `timer`, `task`) take on a real Textual dependency, unlike most
of `core`/`module`, which stay stdlib-only so they're importable by a bare
`python3` without the project's venv. Only reach for Textual in a module
that genuinely needs an interactive TUI.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class PromptScreen(ModalScreen[str | None]):
    """A small centered dialog that asks for one line of text."""

    DEFAULT_CSS = """
    PromptScreen {
        align: center middle;
    }

    PromptScreen > Vertical {
        width: 50;
        height: auto;
        border: round $accent;
        padding: 1 2;
        background: $surface;
    }

    PromptScreen Label {
        margin-bottom: 1;
    }
    """

    def __init__(self, label: str, default: str = "") -> None:
        super().__init__()
        self._label = label
        self._default = default

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._label)
            yield Input(value=self._default, id="value")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def key_escape(self) -> None:
        self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    """A small centered yes/no dialog."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    ConfirmScreen > Vertical {
        width: 50;
        height: auto;
        border: round $warning;
        padding: 1 2;
        background: $surface;
    }

    ConfirmScreen Label {
        margin-bottom: 1;
    }

    ConfirmScreen Horizontal {
        height: auto;
        align: center middle;
    }

    ConfirmScreen Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._message)
            with Horizontal():
                yield Button("Yes", id="yes", variant="error")
                yield Button("No", id="no")

    def on_mount(self) -> None:
        self.query_one("#no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def key_escape(self) -> None:
        self.dismiss(False)

    def key_y(self) -> None:
        self.dismiss(True)

    def key_n(self) -> None:
        self.dismiss(False)

