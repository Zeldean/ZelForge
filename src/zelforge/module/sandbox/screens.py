"""Shared modal screens for sandbox TUIs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class PromptScreen(ModalScreen[str | None]):
    """A small centered dialog that asks for one line of text."""

    DEFAULT_CSS = """
    PromptScreen {
        align: center middle;
    }

    PromptScreen > Vertical {
        width: 44;
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
