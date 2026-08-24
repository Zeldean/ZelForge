"""Shared Textual modal screens for ZelForge module TUIs.

Kept intentionally small. Modules that use this (currently `timer`, `task`,
`journal`) take on a real Textual dependency, unlike most of `core`/`module`,
which stay stdlib-only so they're importable by a bare `python3` without the
project's venv. Only reach for Textual in a module that genuinely needs an
interactive TUI.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList
from textual.widgets.option_list import Option

from zelforge.core import domains as domain_store


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


def _domain_picker_options(domains: list[dict], filter_text: str) -> list[dict]:
    query = filter_text.strip().lower()
    options = []

    if not query or "none".startswith(query):
        options.append({"kind": "none", "code": "", "name": "No domain"})

    for domain in domains:
        code = domain.get("code") or domain.get("key") or ""
        name = domain.get("name") or code
        haystack = f"{code} {name}".lower()
        if not query or query in haystack:
            options.append({"kind": "domain", "code": code, "name": name})

    add_code = query if query else ""
    exact_code = any(option.get("code") == query for option in options if query)
    if not exact_code:
        options.append({"kind": "add", "code": add_code, "name": "Add new domain"})

    return options or [{"kind": "add", "code": add_code, "name": "Add new domain"}]


def _domain_option_label(option: dict) -> str:
    if option["kind"] == "none":
        return "none"
    if option["kind"] == "add":
        code = option.get("code") or ""
        return f"add {code}" if code else "add new domain"

    return f"{option['name']} ({option['code']})"


def _default_domain_index(options: list[dict], default_domain: str | None) -> int:
    if not default_domain:
        return 0

    for index, option in enumerate(options):
        if option.get("code") == default_domain:
            return index

    return 0


class DomainPickerScreen(ModalScreen[str | None]):
    """Type-to-filter picker for a domain, with an inline 'add new domain'
    flow — mirrors the old curses fuzzy picker."""

    DEFAULT_CSS = """
    DomainPickerScreen {
        align: center middle;
    }
    DomainPickerScreen > Vertical {
        width: 60;
        height: 20;
        border: round $accent;
        padding: 1 2;
        background: $surface;
    }
    DomainPickerScreen Input {
        margin-bottom: 1;
    }
    DomainPickerScreen OptionList {
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._domains = domain_store.list_domains()
        self._default_domain = domain_store.get_default_domain()
        self._current_options: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="type to filter", id="filter")
            yield OptionList(id="options")

    def on_mount(self) -> None:
        self._refresh_options("")
        self.query_one("#filter", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_options(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        options = self.query_one("#options", OptionList)
        self._choose(options.highlighted or 0)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._choose(event.index)

    def key_escape(self) -> None:
        self.dismiss(None)

    def _refresh_options(self, query: str) -> None:
        self._current_options = _domain_picker_options(self._domains, query)
        options = self.query_one("#options", OptionList)
        options.clear_options()
        for option in self._current_options:
            options.add_option(Option(_domain_option_label(option)))

        if not query and self._default_domain:
            options.highlighted = _default_domain_index(self._current_options, self._default_domain)

    def _choose(self, index: int | None) -> None:
        if index is None or index >= len(self._current_options):
            self.dismiss(None)
            return

        option = self._current_options[index]
        if option["kind"] == "none":
            self.dismiss("")
            return

        if option["kind"] == "add":
            self._start_add_domain(option.get("code") or "")
            return

        self.dismiss(option["code"])

    def _start_add_domain(self, default_code: str) -> None:
        def handle_name(code: str, name: str | None) -> None:
            if name is None:
                self.dismiss(None)
                return

            try:
                domain = domain_store.add_domain(code=code, name=name)
                self.dismiss(domain["code"])
            except ValueError:
                self.dismiss(code)

        def handle_code(code: str | None) -> None:
            if not code:
                self.dismiss(None)
                return

            self.app.push_screen(PromptScreen("Domain name", default=code), lambda n: handle_name(code, n))

        self.app.push_screen(PromptScreen("Domain code", default=default_code), handle_code)


def _tag_picker_options(known_tags: list[str], filter_text: str) -> list[dict]:
    query = filter_text.strip().lower()
    options = [
        {"kind": "tag", "value": tag}
        for tag in known_tags
        if not query or query in tag.lower()
    ]

    exact = any(option["value"].lower() == query for option in options if query)
    if query and not exact:
        options.append({"kind": "add", "value": query})

    return options


def _tag_option_label(option: dict) -> str:
    if option["kind"] == "add":
        return f"add #{option['value']}"

    return f"#{option['value']}"


class TagPickerScreen(ModalScreen[str | None]):
    """Type-to-filter picker for selecting or adding one tag."""

    DEFAULT_CSS = """
    TagPickerScreen {
        align: center middle;
    }
    TagPickerScreen > Vertical {
        width: 50;
        height: 16;
        border: round $accent;
        padding: 1 2;
        background: $surface;
    }
    TagPickerScreen Input {
        margin-bottom: 1;
    }
    TagPickerScreen OptionList {
        height: 1fr;
    }
    """

    def __init__(self, known_tags: list[str]) -> None:
        super().__init__()
        self._known_tags = known_tags
        self._current_options: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="type to filter or add a tag", id="filter")
            yield OptionList(id="options")

    def on_mount(self) -> None:
        self._refresh_options("")
        self.query_one("#filter", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_options(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        options = self.query_one("#options", OptionList)
        self._choose(options.highlighted or 0)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._choose(event.index)

    def key_escape(self) -> None:
        self.dismiss(None)

    def _refresh_options(self, query: str) -> None:
        self._current_options = _tag_picker_options(self._known_tags, query)
        options = self.query_one("#options", OptionList)
        options.clear_options()
        for option in self._current_options:
            options.add_option(Option(_tag_option_label(option)))

    def _choose(self, index: int | None) -> None:
        if index is None or index >= len(self._current_options):
            self.dismiss(None)
            return

        self.dismiss(self._current_options[index]["value"])
