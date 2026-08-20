"""Trackers page: water/sleep/medication/mood/habit, same sub-block pattern
as the standalone life dashboard, but reading and writing the shared store
(so, e.g., a habit "done day" here shows up as XP on the Levels page)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Sparkline, Static

from ...graphics import HabitHeatmap, MoodStrip, WaterGlass
from ...screens import PromptScreen
from .base import Page

SUB_BLOCKS = [
    ("water", "w", "Water"),
    ("sleep", "s", "Sleep"),
    ("medication", "m", "Medication"),
    ("mood", "o", "Mood"),
    ("habits", "b", "Habits"),
]


class SubBlock(Vertical, can_focus=True):
    ALLOW_MAXIMIZE = True

    def __init__(self, sub_id: str, hotkey: str, title: str) -> None:
        super().__init__(id=f"tracker-{sub_id}", classes="block")
        self.sub_id = sub_id
        self.border_title = f"({hotkey}) {title}"

    @property
    def store(self):
        return self.app.store  # type: ignore[attr-defined]

    def refresh_from_store(self) -> None:
        pass


class WaterSub(SubBlock):
    BINDINGS = [
        ("1", "add(200)", "+200ml"),
        ("2", "add(250)", "+250ml"),
        ("3", "add(500)", "+500ml"),
        ("4", "add(1000)", "+1000ml"),
        ("c", "custom", "Custom"),
        ("g", "goal", "Goal"),
    ]

    def compose(self) -> ComposeResult:
        yield WaterGlass(id="tracker-water-glass")
        yield Static("", id="tracker-water-stat")

    def action_add(self, amount: int) -> None:
        self.store.add_water(amount)
        self.app.notify(f"added {amount}ml water", timeout=2)
        self.refresh_from_store()

    def action_custom(self) -> None:
        def handle(value: str | None) -> None:
            if value is None:
                return

            try:
                amount = int(value)
            except ValueError:
                self.app.notify(f"invalid amount: {value}", severity="error")
                return

            if amount <= 0:
                self.app.notify("amount must be positive", severity="error")
                return

            self.store.add_water(amount)
            self.refresh_from_store()

        self.app.push_screen(PromptScreen("Custom amount (ml)"), handle)

    def action_goal(self) -> None:
        def handle(value: str | None) -> None:
            if value is None:
                return

            try:
                goal = int(value)
            except ValueError:
                self.app.notify(f"invalid goal: {value}", severity="error")
                return

            if goal <= 0:
                self.app.notify("goal must be positive", severity="error")
                return

            self.store.water_goal_ml = goal
            self.refresh_from_store()

        self.app.push_screen(PromptScreen("Daily goal (ml)", default=str(self.store.water_goal_ml)), handle)

    def refresh_from_store(self) -> None:
        store = self.store
        glass = self.query_one("#tracker-water-glass", WaterGlass)
        glass.percent = (store.water_total_ml / store.water_goal_ml) if store.water_goal_ml else 0.0
        percent = round(store.water_total_ml / store.water_goal_ml * 100) if store.water_goal_ml else 0
        self.query_one("#tracker-water-stat", Static).update(f"{store.water_total_ml}ml / {store.water_goal_ml}ml ({percent}%)")


class SleepSub(SubBlock):
    BINDINGS = [("l", "log", "Log hours")]

    def compose(self) -> ComposeResult:
        yield Static("no nights logged yet", id="tracker-sleep-stat")
        yield Sparkline([], id="tracker-sleep-chart")

    def action_log(self) -> None:
        def handle(value: str | None) -> None:
            if value is None:
                return

            try:
                hours = float(value)
            except ValueError:
                self.app.notify(f"invalid hours: {value}", severity="error")
                return

            if hours < 0 or hours > 24:
                self.app.notify("hours must be between 0 and 24", severity="error")
                return

            self.store.log_sleep(hours)
            self.refresh_from_store()

        self.app.push_screen(PromptScreen("Hours slept last night"), handle)

    def refresh_from_store(self) -> None:
        nights = self.store.sleep_nights
        stat = self.query_one("#tracker-sleep-stat", Static)
        if nights:
            avg = sum(nights) / len(nights)
            stat.update(f"last {nights[-1]:g}h   avg {avg:.1f}h")
        else:
            stat.update("no nights logged yet")

        self.query_one("#tracker-sleep-chart", Sparkline).data = list(nights)


class MedicationSub(SubBlock):
    BINDINGS = [
        ("j", "move(1)", "Next"),
        ("k", "move(-1)", "Prev"),
        ("t", "toggle", "Toggle"),
    ]

    def __init__(self, sub_id: str, hotkey: str, title: str) -> None:
        super().__init__(sub_id, hotkey, title)
        self._selected = 0

    def compose(self) -> ComposeResult:
        yield Vertical(id="tracker-dose-list")

    def action_move(self, delta: int) -> None:
        doses = self.store.doses
        if not doses:
            return

        self._selected = (self._selected + delta) % len(doses)
        self.refresh_from_store()

    def action_toggle(self) -> None:
        if not self.store.doses:
            return

        self.store.toggle_dose(self._selected)
        self.refresh_from_store()

    def refresh_from_store(self) -> None:
        container = self.query_one("#tracker-dose-list", Vertical)
        container.remove_children()
        doses = self.store.doses
        if not doses:
            container.mount(Static("no medications", classes="dose-empty"))
            return

        for index, dose in enumerate(doses):
            marker = "x" if dose["taken"] else " "
            pointer = ">" if index == self._selected else " "
            label = Static(f"{pointer}[{marker}] {dose['name']}", classes="dose-row")
            label.set_class(index == self._selected, "dose-selected")
            label.set_class(dose["taken"], "dose-taken")
            container.mount(label)


class MoodSub(SubBlock):
    BINDINGS = [
        ("1", "log(1)", "Rough"),
        ("2", "log(2)", "Low"),
        ("3", "log(3)", "Okay"),
        ("4", "log(4)", "Good"),
        ("5", "log(5)", "Great"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("no mood logged yet", id="tracker-mood-stat")
        yield MoodStrip(id="tracker-mood-strip")

    def action_log(self, level: int) -> None:
        self.store.log_mood(level)
        self.refresh_from_store()

    def refresh_from_store(self) -> None:
        entries = self.store.mood_entries
        labels = {1: "Rough", 2: "Low", 3: "Okay", 4: "Good", 5: "Great"}
        stat = self.query_one("#tracker-mood-stat", Static)
        stat.update(f"today: {labels[entries[-1]]}" if entries else "no mood logged yet")
        self.query_one("#tracker-mood-strip", MoodStrip).entries = tuple(entries)


class HabitsSub(SubBlock):
    BINDINGS = [
        ("t", "mark(True)", "Done Day"),
        ("n", "mark(False)", "Missed Day"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("streak: 0 days", id="tracker-habit-stat")
        yield HabitHeatmap(id="tracker-habit-grid")

    def action_mark(self, done: bool) -> None:
        event = self.store.mark_habit_day(done)
        self.refresh_from_store()
        if event and event.domain_leveled_up:
            self.app.notify(f"LEVEL UP! {event.domain.title} is now level {event.domain.level}", timeout=4)

    def refresh_from_store(self) -> None:
        streak = self.store.habit_streak()
        day_word = "day" if streak == 1 else "days"
        self.query_one("#tracker-habit-stat", Static).update(f"streak: {streak} {day_word}   logged: {len(self.store.habit_days)}")
        self.query_one("#tracker-habit-grid", HabitHeatmap).days = tuple(self.store.habit_days)


SUB_CLASSES = {
    "water": WaterSub,
    "sleep": SleepSub,
    "medication": MedicationSub,
    "mood": MoodSub,
    "habits": HabitsSub,
}


class TrackersPage(Page):
    TAB_ID = "trackers"
    TAB_TITLE = "Trackers"

    BINDINGS = [(hotkey, f"focus_sub('{sub_id}')", title) for sub_id, hotkey, title in SUB_BLOCKS]

    def compose(self) -> ComposeResult:
        with Container(id="trackers-grid"):
            for sub_id, hotkey, title in SUB_BLOCKS:
                yield SUB_CLASSES[sub_id](sub_id, hotkey, title)

    def action_focus_sub(self, sub_id: str) -> None:
        self.query_one(f"#tracker-{sub_id}").focus()

    def refresh_from_store(self) -> None:
        for sub_id, _hotkey, _title in SUB_BLOCKS:
            self.query_one(f"#tracker-{sub_id}").refresh_from_store()

    def commands(self) -> list[tuple[str, str, object]]:
        commands: list[tuple[str, str, object]] = []
        for sub_id, _hotkey, title in SUB_BLOCKS:
            commands.append((f"Focus {title}", f"Switch focus to {title}", lambda s=sub_id: self.action_focus_sub(s)))

        for sub_id, _hotkey, _title in SUB_BLOCKS:
            widget = self.query_one(f"#tracker-{sub_id}")
            if hasattr(widget, "commands"):
                commands.extend(widget.commands())

        return commands
