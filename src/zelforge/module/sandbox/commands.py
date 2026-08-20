"""Generic command-palette provider for sandbox TUIs.

Any App using this just needs a `command_list()` method returning
`list[tuple[str, str, Callable[[], None]]]` (name, help text, callback).
Typing "?" with an empty query, or opening the palette fresh, lists
everything via `discover()` — that's the built-in Textual answer to
"show me what commands and keybinds are available".
"""

from __future__ import annotations

from textual.command import DiscoveryHit, Hit, Hits, Provider


class ActionListProvider(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for name, help_text, callback in self.app.command_list():
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), callback, help=help_text)

    async def discover(self) -> Hits:
        for name, help_text, callback in self.app.command_list():
            yield DiscoveryHit(name, callback, help=help_text)
