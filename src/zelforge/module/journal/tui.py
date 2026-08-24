"""Journal TUI, built on Textual.

One screen: a markdown editor block for quick note capture, with an inline
`#tag` autocomplete (type `#` + letters, digits, `-` or `/` — so hierarchical
tags like `#meta/test` work too — then `Tab` completes to the best known
tag), plus small tags/domain inputs at the bottom that are stored separately
from the inline `#tags` written in the note body. Pressing `Enter` inside
either of those inputs opens a fuzzy picker instead of just taking the typed
text. The editor also carries a few markdown QoL habits: pressing `Enter` on
a list/checkbox/blockquote line continues it on the next line, an empty item
exits the list instead of adding another blank one, and plain indentation is
carried forward. Saving clears the editor so the next note starts fresh.
"""

from __future__ import annotations

import re
import textwrap
from datetime import datetime
from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static, TextArea

from zelforge.core.tui.components import DomainPickerScreen, TagPickerScreen

from . import service


MAX_TAG_SUGGESTIONS = 8
TAG_PREFIX_PATTERN = re.compile(r"#([A-Za-z0-9_/-]*)$")

BULLET_LINE_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>[-*+])(?P<space>\s+)(?P<checkbox>\[[ xX]\]\s+)?(?P<rest>.*)$"
)
ORDERED_LINE_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<number>\d+)(?P<sep>[.)])(?P<space>\s+)(?P<rest>.*)$"
)
BLOCKQUOTE_LINE_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>>+)(?P<space>\s*)(?P<rest>.*)$"
)
INDENT_PATTERN = re.compile(r"^[ \t]*")


def run() -> None:
    """Run the journal TUI."""
    JournalApp().run()


def _format_timestamp(value: str) -> str:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp.astimezone().strftime("%Y-%m-%d %H:%M")


def _note_summary_line(note: dict) -> str:
    first_line = next((line.strip() for line in note["body"].splitlines() if line.strip()), "")
    if len(first_line) > 60:
        first_line = first_line[:57] + "..."

    return f"{_format_timestamp(note['created_at'])}  {first_line}"


def _note_matches(note: dict, query: str) -> bool:
    haystack = " ".join([note["body"], note.get("domain") or "", " ".join(note.get("tags", []))])
    return query in haystack.lower()


class NotesBrowserScreen(ModalScreen[None]):
    """Centered popup: search past notes, newest first, with a live preview."""

    DEFAULT_CSS = """
    NotesBrowserScreen {
        align: center middle;
    }
    NotesBrowserScreen > Horizontal {
        width: 90%;
        height: 80%;
        border: round $accent;
        background: $surface;
    }
    NotesBrowserScreen #notes-search-pane {
        width: 40%;
        height: 100%;
        padding: 1;
        border-right: solid $primary-muted;
    }
    NotesBrowserScreen #notes-search {
        margin-bottom: 1;
    }
    NotesBrowserScreen #notes-list {
        height: 1fr;
    }
    NotesBrowserScreen #notes-preview {
        width: 60%;
        height: 100%;
        padding: 1 2;
    }
    """

    def __init__(self, notes: list[dict]) -> None:
        super().__init__()
        self._all_notes = sorted(notes, key=lambda note: note["created_at"], reverse=True)
        self._current: list[dict] = []

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="notes-search-pane"):
                yield Input(placeholder="search notes", id="notes-search")
                yield ListView(id="notes-list")
            yield Static("no notes", id="notes-preview")

    def on_mount(self) -> None:
        self._refresh_list("")
        self.query_one("#notes-search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_list(event.value)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._update_preview()

    def key_escape(self) -> None:
        self.dismiss(None)

    def key_up(self) -> None:
        self._move_highlight(-1)

    def key_down(self) -> None:
        self._move_highlight(1)

    def _move_highlight(self, delta: int) -> None:
        if not self._current:
            return

        list_view = self.query_one("#notes-list", ListView)
        index = (list_view.index or 0) + delta
        list_view.index = max(0, min(index, len(self._current) - 1))

    def _refresh_list(self, query: str) -> None:
        cleaned = query.strip().lower()
        if cleaned:
            self._current = [note for note in self._all_notes if _note_matches(note, cleaned)]
        else:
            self._current = list(self._all_notes)

        list_view = self.query_one("#notes-list", ListView)
        list_view.clear()
        for note in self._current:
            list_view.append(ListItem(Label(_note_summary_line(note))))

        if self._current:
            list_view.index = 0

        self._update_preview()

    def _update_preview(self) -> None:
        preview = self.query_one("#notes-preview", Static)
        if not self._current:
            preview.update("no notes")
            return

        list_view = self.query_one("#notes-list", ListView)
        index = min(list_view.index or 0, len(self._current) - 1)
        note = self._current[index]

        meta = _format_timestamp(note["created_at"])
        if note.get("domain"):
            meta += f"  ·  {note['domain']}"
        if note.get("tags"):
            meta += f"  ·  {', '.join(note['tags'])}"

        body = "\n".join(
            "\n".join(textwrap.wrap(line, width=60)) if line.strip() else ""
            for line in note["body"].splitlines()
        )
        preview.update(f"{meta}\n\n{body}")


def _bullet_continuation(match: re.Match) -> str:
    prefix = match.group("indent") + match.group("marker") + match.group("space")
    if match.group("checkbox"):
        prefix += "[ ] "
    return prefix


def _ordered_continuation(match: re.Match) -> str:
    next_number = int(match.group("number")) + 1
    return f"{match.group('indent')}{next_number}{match.group('sep')}{match.group('space')}"


def _blockquote_continuation(match: re.Match) -> str:
    return f"{match.group('indent')}{match.group('marker')} "


# Checked in order; the first pattern to match the current line decides how
# `Enter` continues it. Each entry: (pattern, continuation-prefix builder).
CONTINUATION_PATTERNS = [
    (BULLET_LINE_PATTERN, _bullet_continuation),
    (ORDERED_LINE_PATTERN, _ordered_continuation),
    (BLOCKQUOTE_LINE_PATTERN, _blockquote_continuation),
]


class JournalEditor(TextArea):
    """The note body editor: `#tag` autocomplete and markdown-aware Enter."""

    def __init__(self, journal_app: "JournalApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self._journal_app = journal_app
        self.active_suggestions: list[str] = []

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "tab" and self.active_suggestions:
            event.prevent_default()
            event.stop()
            self._accept_suggestion(self.active_suggestions[0])
            return

        if event.key == "enter" and self._handle_smart_enter():
            event.prevent_default()
            event.stop()
            self._refresh_suggestions()
            return

        await super()._on_key(event)
        self._refresh_suggestions()

    # --- markdown QoL: list/quote continuation on Enter -----------------

    def _handle_smart_enter(self) -> bool:
        row, _ = self.cursor_location
        line = str(self.get_line(row)).rstrip("\n")

        for pattern, build_continuation in CONTINUATION_PATTERNS:
            match = pattern.match(line)
            if match is None:
                continue

            if not match.group("rest").strip():
                # Empty item: exit the list instead of adding another one.
                indent = match.group("indent")
                self.replace(indent, (row, 0), (row, len(line)))
                self.move_cursor((row, len(indent)))
                self.insert("\n")
                return True

            self.insert("\n" + build_continuation(match))
            return True

        indent = INDENT_PATTERN.match(line).group(0)
        if indent:
            self.insert("\n" + indent)
            return True

        return False

    # --- inline #tag autocomplete ----------------------------------------

    def _current_tag_prefix(self) -> str | None:
        row, column = self.cursor_location
        line = str(self.get_line(row))[:column]
        match = TAG_PREFIX_PATTERN.search(line)
        return match.group(1) if match else None

    def _refresh_suggestions(self) -> None:
        prefix = self._current_tag_prefix()
        if prefix is None:
            self.active_suggestions = []
        else:
            query = prefix.lower()
            self.active_suggestions = [
                tag for tag in self._journal_app.known_tags if tag.startswith(query)
            ][:MAX_TAG_SUGGESTIONS]

        self._journal_app.update_tag_suggestions(self.active_suggestions)

    def _accept_suggestion(self, tag: str) -> None:
        row, column = self.cursor_location
        line = str(self.get_line(row))[:column]
        match = TAG_PREFIX_PATTERN.search(line)
        if match is None:
            return

        start = (row, match.start())
        end = (row, column)
        self.replace(f"#{tag} ", start, end)
        self.active_suggestions = []
        self._journal_app.update_tag_suggestions([])


class JournalApp(App):
    """Capture a markdown journal note."""

    CSS_PATH = Path(__file__).parent / "tui.tcss"
    TITLE = "ZelJournal"

    BINDINGS = [
        ("ctrl+s", "save", "Save"),
        ("ctrl+l", "browse_notes", "Browse Notes"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.known_tags: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield JournalEditor(self, id="editor")
        yield Static("", id="tag-suggestions")
        with Horizontal(id="meta-row"):
            yield Input(placeholder="tags (comma separated, Enter to pick)", id="tags-input")
            yield Input(placeholder="domain (Enter to pick)", id="domain-input")
        yield Footer()

    def on_mount(self) -> None:
        # ansi-dark maps colors to the terminal's own ANSI palette and
        # leaves the background untouched (transparent here), instead of
        # painting Textual's truecolor theme over the terminal.
        self.theme = "ansi-dark"
        self._refresh_known_tags()
        self.query_one("#editor", JournalEditor).focus()

    def update_tag_suggestions(self, suggestions: list[str]) -> None:
        label = self.query_one("#tag-suggestions", Static)
        if not suggestions:
            label.update("")
            return

        first, rest = suggestions[0], suggestions[1:]
        text = f"[{first}]" + ("  " + "  ".join(rest) if rest else "")
        label.update(text)

    def action_browse_notes(self) -> None:
        notes = service.list_notes()
        if not notes:
            self.notify("no notes yet", severity="warning")
            return

        self.push_screen(NotesBrowserScreen(notes))

    def _refresh_known_tags(self) -> None:
        self.known_tags = service.list_known_tags()

    # --- domain/tag pickers ----------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "domain-input":
            event.stop()
            self.push_screen(DomainPickerScreen(), self._apply_domain_choice)
        elif event.input.id == "tags-input":
            event.stop()
            self.push_screen(TagPickerScreen(self.known_tags), self._apply_tag_choice)

    def _apply_domain_choice(self, code: str | None) -> None:
        if code is not None:
            self.query_one("#domain-input", Input).value = code

        self.query_one("#editor", JournalEditor).focus()

    def _apply_tag_choice(self, tag: str | None) -> None:
        tags_input = self.query_one("#tags-input", Input)
        if tag:
            current = [t.strip() for t in tags_input.value.split(",") if t.strip()]
            if tag not in current:
                current.append(tag)
            tags_input.value = ", ".join(current)

        tags_input.focus()

    # --- save --------------------------------------------------------------

    def action_save(self) -> None:
        editor = self.query_one("#editor", JournalEditor)
        body = editor.text.strip()
        if not body:
            self.notify("nothing to save", severity="warning")
            return

        tags_input = self.query_one("#tags-input", Input)
        domain_input = self.query_one("#domain-input", Input)
        tags = [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]

        try:
            note = service.create_note(body=body, tags=tags, domain=domain_input.value)
        except ValueError as error:
            self.notify(str(error), severity="error")
            return

        editor.text = ""
        tags_input.value = ""
        self.update_tag_suggestions([])
        self._refresh_known_tags()
        editor.focus()
        self.notify(f"saved note {note['id'][:8]}", timeout=2)


if __name__ == "__main__":
    run()
