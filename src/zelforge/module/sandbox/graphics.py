"""Small custom-rendered widgets shared between sandbox TUIs.

These draw with Rich `Text` directly instead of composing built-in widgets,
for the cases where a plain `ProgressBar`/`Static` isn't enough visual
personality. Colors always come from theme component classes (never
hardcoded), so they stay correct under every theme — including the `ansi-*`
themes, which map to the terminal's own colors and transparency.
"""

from __future__ import annotations

from rich.text import Text

from textual.reactive import reactive
from textual.widget import Widget

WAVE_FRAMES = ["~ ~ ~ ~ ~ ~ ~ ~", "~  ~  ~  ~  ~  ", " ~ ~ ~ ~ ~ ~ ~ ~"]


class WaterGlass(Widget):
    """A vertical glass that fills from the bottom, with an animated waterline."""

    COMPONENT_CLASSES = {
        "water-glass--rim",
        "water-glass--empty",
        "water-glass--fill",
        "water-glass--overfill",
        "water-glass--wave",
    }

    DEFAULT_CSS = """
    WaterGlass {
        width: auto;
        height: auto;
        content-align: center middle;
    }
    WaterGlass .water-glass--rim { color: $primary-muted; }
    WaterGlass .water-glass--empty { color: $primary-muted; }
    WaterGlass .water-glass--fill { color: $accent; }
    WaterGlass .water-glass--overfill { color: $success; }
    WaterGlass .water-glass--wave { color: $accent; text-style: bold; }
    """

    percent: reactive[float] = reactive(0.0)

    GLASS_WIDTH = 19
    GLASS_HEIGHT = 11

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._wave_frame = 0

    def on_mount(self) -> None:
        self.set_interval(0.7, self._tick_wave)

    def _tick_wave(self) -> None:
        self._wave_frame = (self._wave_frame + 1) % len(WAVE_FRAMES)
        if self.percent > 0:
            self.refresh()

    def render(self) -> Text:
        capped = min(max(self.percent, 0.0), 1.0)
        over = self.percent > 1.0

        interior_width = self.GLASS_WIDTH - 2
        interior_height = self.GLASS_HEIGHT - 2
        filled_rows = round(capped * interior_height)

        rim = self.get_component_rich_style("water-glass--rim")
        empty = self.get_component_rich_style("water-glass--empty")
        fill = self.get_component_rich_style("water-glass--overfill" if over else "water-glass--fill")
        wave = self.get_component_rich_style("water-glass--wave")

        lines: list[Text] = [Text("╭" + "─" * interior_width + "╮", style=rim)]

        wave_glyphs = (WAVE_FRAMES[self._wave_frame] * 2)[:interior_width]
        for row in range(interior_height):
            line = Text()
            line.append("│", style=rim)

            is_filled = row >= interior_height - filled_rows
            if is_filled:
                is_waterline = row == interior_height - filled_rows
                if is_waterline:
                    line.append(wave_glyphs.ljust(interior_width), style=wave)
                else:
                    line.append("█" * interior_width, style=fill)
            else:
                line.append(" " * interior_width, style=empty)

            line.append("│", style=rim)
            lines.append(line)

        lines.append(Text("╰" + "─" * interior_width + "╯", style=rim))

        result = Text()
        for index, line in enumerate(lines):
            if index:
                result.append("\n")
            result.append_text(line)

        return result


class XPBar(Widget):
    """A full-width progress bar toward the next level, with a flash state
    for level-up moments (call sites toggle `.flashing` for a bit)."""

    COMPONENT_CLASSES = {"xp-bar--fill", "xp-bar--empty", "xp-bar--flash"}

    DEFAULT_CSS = """
    XPBar {
        width: 1fr;
        height: 1;
    }
    XPBar .xp-bar--fill { color: $accent; }
    XPBar .xp-bar--empty { color: $primary-muted; }
    XPBar .xp-bar--flash { color: $warning; text-style: bold; }
    """

    percent: reactive[float] = reactive(0.0)
    flashing: reactive[bool] = reactive(False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._flash_on = False

    def on_mount(self) -> None:
        self.set_interval(0.15, self._tick_flash)

    def _tick_flash(self) -> None:
        if self.flashing:
            self._flash_on = not self._flash_on
            self.refresh()

    def render(self) -> Text:
        width = max(self.size.width, 1)
        capped = min(max(self.percent, 0.0), 1.0)
        filled = round(capped * width)

        fill_style = self.get_component_rich_style(
            "xp-bar--flash" if (self.flashing and self._flash_on) else "xp-bar--fill"
        )
        empty_style = self.get_component_rich_style("xp-bar--empty")

        text = Text()
        text.append("█" * filled, style=fill_style)
        text.append("░" * (width - filled), style=empty_style)
        return text


MOOD_GLYPHS = {1: "▁", 2: "▃", 3: "▅", 4: "▆", 5: "█"}


class MoodStrip(Widget):
    """A row of bars for the last few mood entries, one bar per entry."""

    COMPONENT_CLASSES = {
        "mood-strip--1",
        "mood-strip--2",
        "mood-strip--3",
        "mood-strip--4",
        "mood-strip--5",
        "mood-strip--empty",
    }

    DEFAULT_CSS = """
    MoodStrip {
        width: auto;
        height: 1;
    }
    MoodStrip .mood-strip--1 { color: $error; }
    MoodStrip .mood-strip--2 { color: $warning; }
    MoodStrip .mood-strip--3 { color: $text-muted; }
    MoodStrip .mood-strip--4 { color: $accent; }
    MoodStrip .mood-strip--5 { color: $success; }
    MoodStrip .mood-strip--empty { color: $primary-muted; }
    """

    entries: reactive[tuple[int, ...]] = reactive(())

    SLOTS = 7

    def render(self) -> Text:
        empty = self.get_component_rich_style("mood-strip--empty")
        values = list(self.entries[-self.SLOTS :])
        padding = self.SLOTS - len(values)

        text = Text()
        for _ in range(padding):
            text.append("· ", style=empty)

        for value in values:
            glyph = MOOD_GLYPHS.get(value, "?")
            style = self.get_component_rich_style(f"mood-strip--{value}")
            text.append(f"{glyph} ", style=style)

        return text


class HabitHeatmap(Widget):
    """A GitHub-style contribution grid: one cell per logged day."""

    COMPONENT_CLASSES = {"habit-heatmap--done", "habit-heatmap--missed", "habit-heatmap--empty"}

    DEFAULT_CSS = """
    HabitHeatmap {
        width: auto;
        height: auto;
    }
    HabitHeatmap .habit-heatmap--done { color: $success; }
    HabitHeatmap .habit-heatmap--missed { color: $error 60%; }
    HabitHeatmap .habit-heatmap--empty { color: $primary-muted; }
    """

    days: reactive[tuple[bool, ...]] = reactive(())

    COLUMNS = 7
    MAX_DAYS = 28

    def render(self) -> Text:
        done = self.get_component_rich_style("habit-heatmap--done")
        missed = self.get_component_rich_style("habit-heatmap--missed")
        empty = self.get_component_rich_style("habit-heatmap--empty")

        days: list[bool | None] = list(self.days[-self.MAX_DAYS :])
        pad = (-len(days)) % self.COLUMNS
        days = [None] * pad + days
        weeks = [days[index : index + self.COLUMNS] for index in range(0, len(days), self.COLUMNS)]

        lines: list[Text] = []
        for week in weeks:
            line = Text()
            for day in week:
                if day is None:
                    line.append("  ")
                elif day:
                    line.append("█ ", style=done)
                else:
                    line.append("▁ ", style=missed)
            lines.append(line)

        if not lines:
            lines.append(Text("  " * self.COLUMNS, style=empty))

        result = Text()
        for index, line in enumerate(lines):
            if index:
                result.append("\n")
            result.append_text(line)

        return result


RING_POSITIONS = [
    (0, 4),
    (1, 7),
    (2, 8),
    (3, 7),
    (4, 4),
    (3, 1),
    (2, 0),
    (1, 1),
]
RING_HEIGHT = 5
RING_WIDTH = 9


class FocusRing(Widget):
    """A little 8-point compass ring that fills clockwise as time elapses."""

    COMPONENT_CLASSES = {"focus-ring--filled", "focus-ring--empty", "focus-ring--next"}

    DEFAULT_CSS = """
    FocusRing {
        width: auto;
        height: auto;
        content-align: center middle;
    }
    FocusRing .focus-ring--filled { color: $accent; text-style: bold; }
    FocusRing .focus-ring--empty { color: $primary-muted; }
    FocusRing .focus-ring--next { color: $warning; text-style: bold; }
    """

    percent: reactive[float] = reactive(0.0)
    running: reactive[bool] = reactive(False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._pulse = False

    def on_mount(self) -> None:
        self.set_interval(0.5, self._tick_pulse)

    def _tick_pulse(self) -> None:
        self._pulse = not self._pulse
        if self.running:
            self.refresh()

    def render(self) -> Text:
        capped = min(max(self.percent, 0.0), 1.0)
        filled_count = round(capped * len(RING_POSITIONS))

        filled = self.get_component_rich_style("focus-ring--filled")
        empty = self.get_component_rich_style("focus-ring--empty")
        next_style = self.get_component_rich_style("focus-ring--next")

        grid = [[" " for _ in range(RING_WIDTH)] for _ in range(RING_HEIGHT)]
        styles = [[empty for _ in range(RING_WIDTH)] for _ in range(RING_HEIGHT)]

        for index, (row, col) in enumerate(RING_POSITIONS):
            is_next = self.running and index == filled_count and self._pulse
            if is_next:
                grid[row][col] = "◐"
                styles[row][col] = next_style
            elif index < filled_count:
                grid[row][col] = "●"
                styles[row][col] = filled
            else:
                grid[row][col] = "○"
                styles[row][col] = empty

        lines: list[Text] = []
        for row in range(RING_HEIGHT):
            line = Text()
            for col in range(RING_WIDTH):
                line.append(grid[row][col], style=styles[row][col])
            lines.append(line)

        result = Text()
        for index, line in enumerate(lines):
            if index:
                result.append("\n")
            result.append_text(line)

        return result


class TimelineRow(Widget):
    """One horizontal Gantt-style bar spanning `start_hour` to `end_hour`
    within a 24-hour-wide track, in a given ansi color."""

    DEFAULT_CSS = """
    TimelineRow {
        width: 1fr;
        height: 1;
    }
    """

    start_hour: reactive[float] = reactive(0.0)
    end_hour: reactive[float] = reactive(1.0)
    color: reactive[str] = reactive("ansi_blue")
    label: reactive[str] = reactive("")

    DAY_START = 0
    DAY_END = 24

    def render(self) -> Text:
        width = max(self.size.width, 1)
        span = self.DAY_END - self.DAY_START
        start_col = round((max(self.start_hour, self.DAY_START) - self.DAY_START) / span * width)
        end_col = round((min(self.end_hour, self.DAY_END) - self.DAY_START) / span * width)
        end_col = max(end_col, start_col + 1)
        end_col = min(end_col, width)

        bar_width = end_col - start_col
        label = f" {self.label} "[:bar_width].ljust(bar_width) if bar_width > 0 else ""

        text = Text(" " * start_col + label + " " * max(width - start_col - bar_width, 0))
        if bar_width > 0:
            # Rich's own color parser doesn't know Textual's "ansi_*" CSS
            # keyword — strip the prefix down to the plain 8-color name it
            # does understand (still rendered via the terminal's own ANSI
            # escape codes, so this stays theme/transparency-safe).
            rich_color = self.color.removeprefix("ansi_")
            text.stylize(f"on {rich_color}", start_col, start_col + bar_width)

        return text
