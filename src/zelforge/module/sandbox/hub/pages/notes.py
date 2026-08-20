"""Notes page: a note list, a text editor, and a live Markdown preview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Markdown, OptionList, TextArea
from textual.widgets.option_list import Option

from ...screens import PromptScreen
from .base import Page


class NotesPage(Page):
    TAB_ID = "notes"
    TAB_TITLE = "Notes"

    def __init__(self) -> None:
        super().__init__(id="notes-page")
        self._selected_note_id: int | None = None
        self._preview = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="notes-body"):
            with Vertical(id="notes-sidebar"):
                yield OptionList(id="notes-list")
                with Horizontal(id="notes-buttons"):
                    yield Button("New", id="notes-new-btn")
                    yield Button("Delete", id="notes-delete-btn", variant="error")
            with Vertical(id="notes-editor-panel"):
                yield Button("Toggle Preview", id="notes-preview-btn")
                yield TextArea(id="notes-editor", language="markdown", show_line_numbers=True)
                yield Markdown("", id="notes-preview")

    def on_mount(self) -> None:
        self.query_one("#notes-preview", Markdown).display = False

    def initial_focus_target(self):
        return self.query_one("#notes-list", OptionList)

    def commands(self) -> list[tuple[str, str, object]]:
        return [
            ("Notes: New", "Create a new note", self.action_new_note),
            ("Notes: Delete Selected", "Delete the selected note", self.action_delete_note),
            ("Notes: Toggle Preview", "Toggle the markdown preview", self.action_toggle_preview),
        ]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "notes-new-btn":
            self.action_new_note()
        elif event.button.id == "notes-delete-btn":
            self.action_delete_note()
        elif event.button.id == "notes-preview-btn":
            self.action_toggle_preview()

    def action_new_note(self) -> None:
        def handle(title: str | None) -> None:
            if not title:
                return

            note = self.store.add_note(title, "")
            self.refresh_from_store()
            self._select_note(note.id)

        self.app.push_screen(PromptScreen("Note title"), handle)

    def action_delete_note(self) -> None:
        if self._selected_note_id is None:
            self.app.notify("no note selected", severity="warning")
            return

        self.store.delete_note(self._selected_note_id)
        self._selected_note_id = None
        self.refresh_from_store()

    def action_toggle_preview(self) -> None:
        self._save_current()
        self._preview = not self._preview
        editor = self.query_one("#notes-editor", TextArea)
        preview = self.query_one("#notes-preview", Markdown)
        editor.display = not self._preview
        preview.display = self._preview
        if self._preview:
            preview.update(editor.text)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._save_current()
        note_id = int(event.option.id) if event.option.id else None
        self._select_note(note_id)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._save_current()

    def _select_note(self, note_id: int | None) -> None:
        self._selected_note_id = note_id
        note = next((n for n in self.store.notes if n.id == note_id), None)
        editor = self.query_one("#notes-editor", TextArea)
        editor.text = note.body if note else ""
        if self._preview:
            self.query_one("#notes-preview", Markdown).update(editor.text)

    def _save_current(self) -> None:
        if self._selected_note_id is None:
            return

        note = next((n for n in self.store.notes if n.id == self._selected_note_id), None)
        if note is not None:
            note.body = self.query_one("#notes-editor", TextArea).text

    def refresh_from_store(self) -> None:
        self._save_current()
        option_list = self.query_one("#notes-list", OptionList)
        option_list.clear_options()
        for note in self.store.notes:
            option_list.add_option(Option(note.title, id=str(note.id)))

        if self.store.notes and self._selected_note_id is None:
            self._select_note(self.store.notes[0].id)
