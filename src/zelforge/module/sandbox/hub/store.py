"""Shared in-memory data store for the Hub app.

Every page reads and mutates this one object (via `app.store`) instead of
owning private state, so pages can genuinely cross-link: completing a task
grants XP to its domain, stopping a timer does too, a habit "done day" does
too, and the Home/Activity pages can see everything that happened anywhere.

Nothing here is real. In the actual system this would be replaced by calls
into `zeltask`/`zeltimer`/`zelhabit`/`zeljournal`/`zelrepo` and domains would
come from `zelforge.core.domains` — see the sandbox README.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

DOMAIN_XP_PER_LEVEL = 100
CHARACTER_XP_PER_LEVEL = 300

LEVEL_TITLES = [
    (1, "Novice"),
    (5, "Apprentice"),
    (10, "Adept"),
    (20, "Expert"),
    (35, "Master"),
    (50, "Legend"),
]

# (id, title, ansi color). ansi_* colors are literal terminal ANSI colors,
# so every domain gets a stable, distinct hue that's still fully the
# terminal's own palette, regardless of theme.
DOMAIN_DEFS = [
    ("career", "Career", "ansi_blue"),
    ("health", "Health", "ansi_green"),
    ("learning", "Learning", "ansi_cyan"),
    ("creative", "Creative", "ansi_magenta"),
    ("social", "Social", "ansi_yellow"),
]


def _level_from_total(total: int, per_level: int) -> tuple[int, int]:
    level = 1
    remaining = total
    while remaining >= per_level * level:
        remaining -= per_level * level
        level += 1
    return level, remaining


def title_for_level(level: int) -> str:
    title = LEVEL_TITLES[0][1]
    for threshold, name in LEVEL_TITLES:
        if level >= threshold:
            title = name
    return title


@dataclass
class Domain:
    id: str
    title: str
    color: str
    level: int = 1
    xp: int = 0
    total_xp: int = 0
    history: list[tuple[str, int]] = field(default_factory=list)

    def xp_to_next(self) -> int:
        return DOMAIN_XP_PER_LEVEL * self.level


@dataclass
class Task:
    id: int
    title: str
    domain_id: str
    priority: str
    xp: int
    status: str = "todo"


@dataclass
class Note:
    id: int
    title: str
    body: str
    domain_id: str | None = None


@dataclass
class TimerSession:
    id: int
    domain_id: str
    title: str
    started_at: float
    stopped_at: float | None = None

    @property
    def running(self) -> bool:
        return self.stopped_at is None

    def duration_seconds(self) -> int:
        end = self.stopped_at if self.stopped_at is not None else time.monotonic()
        return int(end - self.started_at)


@dataclass
class ScheduleBlock:
    id: int
    title: str
    domain_id: str
    start_hour: float
    end_hour: float


@dataclass
class RepoInfo:
    name: str
    branch: str
    ahead: int
    behind: int
    dirty: bool
    last_commit: str


@dataclass
class Profile:
    name: str = "Adventurer"


@dataclass
class XPEvent:
    domain: Domain
    amount: int
    label: str
    domain_leveled_up: bool
    character_leveled_up: bool
    character_level: int


ACHIEVEMENT_DEFS = [
    ("first-blood", "First Blood", "Complete your first task", lambda s: s.tasks_completed() >= 1),
    ("task-master", "Task Master", "Complete 10 tasks", lambda s: s.tasks_completed() >= 10),
    ("rising-star", "Rising Star", "Reach level 3 in any domain", lambda s: any(d.level >= 3 for d in s.domains.values())),
    ("well-rounded", "Well Rounded", "Reach level 2 in every domain", lambda s: all(d.level >= 2 for d in s.domains.values())),
    ("hydrated", "Hydrated", "Hit your water goal", lambda s: s.water_total_ml >= s.water_goal_ml),
    ("night-owl", "Well Rested", "Log 3 nights of sleep", lambda s: len(s.sleep_nights) >= 3),
    ("streak-week", "One Week Strong", "A 7-day habit streak", lambda s: s.habit_streak() >= 7),
    ("wordsmith", "Wordsmith", "Write 3 notes", lambda s: len(s.notes) >= 3),
    ("clockwatcher", "Clockwatcher", "Log an hour across all sessions", lambda s: s.total_session_seconds() >= 3600),
    ("legend", "Legend", "Reach character level 5", lambda s: s.character_level()[0] >= 5),
]


class Store:
    def __init__(self) -> None:
        self.activity: list[tuple[float, str]] = []

        self.domains: dict[str, Domain] = {id_: Domain(id_, title, color) for id_, title, color in DOMAIN_DEFS}

        self.tasks: list[Task] = []
        self._next_task_id = 1
        self.add_task("Write project proposal", "career", "high", 60)
        self.add_task("Reply to emails", "career", "low", 10)
        self.add_task("Read a chapter", "learning", "medium", 25)
        self.add_task("Call a friend", "social", "medium", 25)

        self.notes: list[Note] = []
        self._next_note_id = 1
        self.add_note("Welcome", "This is the Notes page. Press n to write a new one.")

        self.sessions: list[TimerSession] = []
        self._next_session_id = 1
        self._seed_closed_session("career", "Subscriptions", 25 * 60)
        self._seed_closed_session("health", "Workout", 40 * 60)

        self.schedule: list[ScheduleBlock] = []
        self._next_schedule_id = 1
        self.add_schedule_block("Deep work", "career", 9.0, 11.0)
        self.add_schedule_block("Gym", "health", 12.0, 13.0)
        self.add_schedule_block("Study", "learning", 19.0, 20.5)

        self.repos: list[RepoInfo] = [
            RepoInfo("zelforge", "main", 2, 0, True, "3 hours ago"),
            RepoInfo("dotfiles", "main", 0, 0, False, "2 days ago"),
            RepoInfo("side-project", "feature/tui", 5, 1, True, "just now"),
        ]

        self.profile = Profile()
        self.water_total_ml = 0
        self.water_goal_ml = 2000
        self.water_entries: list[int] = []
        self.sleep_nights: list[float] = []
        self.doses: list[dict] = [
            {"name": "Vitamin D", "taken": False},
            {"name": "Omega-3", "taken": False},
        ]
        self.mood_entries: list[int] = []
        self.habit_days: list[bool] = []

        self.log("Welcome to the Hub. Nothing here is real — go make it real.")

    # --- activity -----------------------------------------------------------

    def log(self, message: str) -> None:
        self.activity.append((time.time(), message))
        self.activity = self.activity[-300:]

    # --- xp / leveling ----------------------------------------------------

    def add_xp(self, domain_id: str, amount: int, label: str) -> XPEvent:
        domain = self.domains[domain_id]
        old_level = domain.level
        old_char_level = self.character_level()[0]

        domain.history.append((label, amount))
        domain.total_xp += amount
        domain.level, domain.xp = _level_from_total(domain.total_xp, DOMAIN_XP_PER_LEVEL)

        new_char_level = self.character_level()[0]

        self.log(f"+{amount} xp in {domain.title} — {label}")
        return XPEvent(
            domain=domain,
            amount=amount,
            label=label,
            domain_leveled_up=domain.level > old_level,
            character_leveled_up=new_char_level > old_char_level,
            character_level=new_char_level,
        )

    def undo_last_xp(self, domain_id: str) -> tuple[str, int] | None:
        """Pop and reverse a domain's most recent XP gain, if any."""
        domain = self.domains[domain_id]
        if not domain.history:
            return None

        label, amount = domain.history.pop()
        domain.total_xp = max(domain.total_xp - amount, 0)
        domain.level, domain.xp = _level_from_total(domain.total_xp, DOMAIN_XP_PER_LEVEL)
        self.log(f"Undid +{amount} xp in {domain.title} ({label})")
        return label, amount

    def character_level(self) -> tuple[int, int, int]:
        total = sum(d.total_xp for d in self.domains.values())
        level, remaining = _level_from_total(total, CHARACTER_XP_PER_LEVEL)
        return level, remaining, CHARACTER_XP_PER_LEVEL * level

    def character_total_xp(self) -> int:
        return sum(d.total_xp for d in self.domains.values())

    # --- tasks --------------------------------------------------------------

    def add_task(self, title: str, domain_id: str, priority: str, xp: int) -> Task:
        task = Task(id=self._next_task_id, title=title, domain_id=domain_id, priority=priority, xp=xp)
        self._next_task_id += 1
        self.tasks.append(task)
        self.log(f"Added task '{title}'")
        return task

    def complete_task(self, task_id: int) -> XPEvent | None:
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task is None or task.status == "done":
            return None

        task.status = "done"
        self.log(f"Completed task '{task.title}'")
        return self.add_xp(task.domain_id, task.xp, f"Task: {task.title}")

    def delete_task(self, task_id: int) -> None:
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def tasks_completed(self) -> int:
        return sum(1 for t in self.tasks if t.status == "done")

    # --- notes ----------------------------------------------------------

    def add_note(self, title: str, body: str = "", domain_id: str | None = None) -> Note:
        note = Note(id=self._next_note_id, title=title, body=body, domain_id=domain_id)
        self._next_note_id += 1
        self.notes.append(note)
        self.log(f"Wrote note '{title}'")
        return note

    def delete_note(self, note_id: int) -> None:
        self.notes = [n for n in self.notes if n.id != note_id]

    # --- timer sessions -------------------------------------------------

    def _seed_closed_session(self, domain_id: str, title: str, duration_seconds: int) -> None:
        now = time.monotonic()
        session = TimerSession(
            id=self._next_session_id,
            domain_id=domain_id,
            title=title,
            started_at=now - duration_seconds,
            stopped_at=now,
        )
        self._next_session_id += 1
        self.sessions.append(session)

    def active_session(self, domain_id: str) -> TimerSession | None:
        for session in reversed(self.sessions):
            if session.domain_id == domain_id and session.running:
                return session
        return None

    def domain_sessions(self, domain_id: str) -> list[TimerSession]:
        return [s for s in self.sessions if s.domain_id == domain_id]

    def domain_session_seconds(self, domain_id: str) -> int:
        return sum(s.duration_seconds() for s in self.domain_sessions(domain_id))

    def start_session(self, domain_id: str, title: str) -> TimerSession:
        self.stop_session(domain_id)

        session = TimerSession(id=self._next_session_id, domain_id=domain_id, title=title, started_at=time.monotonic())
        self._next_session_id += 1
        self.sessions.append(session)
        self.log(f"Started '{title}' ({self.domains[domain_id].title})")
        return session

    def stop_session(self, domain_id: str) -> XPEvent | None:
        session = self.active_session(domain_id)
        if session is None:
            return None

        session.stopped_at = time.monotonic()
        minutes = session.duration_seconds() // 60
        self.log(f"Stopped '{session.title}' ({minutes}m)")

        if minutes <= 0:
            return None

        return self.add_xp(domain_id, minutes, f"Session: {session.title}")

    def total_session_seconds(self) -> int:
        return sum(s.duration_seconds() for s in self.sessions)

    # --- schedule -------------------------------------------------------

    def add_schedule_block(self, title: str, domain_id: str, start_hour: float, end_hour: float) -> ScheduleBlock:
        block = ScheduleBlock(id=self._next_schedule_id, title=title, domain_id=domain_id, start_hour=start_hour, end_hour=end_hour)
        self._next_schedule_id += 1
        self.schedule.append(block)
        self.schedule.sort(key=lambda b: b.start_hour)
        self.log(f"Scheduled '{title}'")
        return block

    def delete_schedule_block(self, block_id: int) -> None:
        self.schedule = [b for b in self.schedule if b.id != block_id]

    # --- trackers ---------------------------------------------------------

    def add_water(self, amount: int) -> None:
        self.water_entries.append(amount)
        self.water_total_ml += amount
        self.log(f"Logged {amount}ml of water")

    def log_sleep(self, hours: float) -> None:
        self.sleep_nights = (self.sleep_nights + [hours])[-7:]
        self.log(f"Logged {hours:g}h of sleep")

    def toggle_dose(self, index: int) -> None:
        if 0 <= index < len(self.doses):
            dose = self.doses[index]
            dose["taken"] = not dose["taken"]
            self.log(f"{'Took' if dose['taken'] else 'Un-took'} {dose['name']}")

    def log_mood(self, level: int) -> None:
        self.mood_entries.append(level)
        self.log(f"Logged mood: {level}/5")

    def mark_habit_day(self, done: bool) -> XPEvent | None:
        self.habit_days.append(done)
        self.log("Logged a done day" if done else "Logged a missed day")
        if done:
            return self.add_xp("health", 15, "Habit streak")
        return None

    def habit_streak(self) -> int:
        streak = 0
        for done in reversed(self.habit_days):
            if not done:
                break
            streak += 1
        return streak

    # --- achievements -------------------------------------------------------

    def achievements(self) -> list[tuple[str, str, str, bool]]:
        return [(aid, title, desc, bool(check(self))) for aid, title, desc, check in ACHIEVEMENT_DEFS]
