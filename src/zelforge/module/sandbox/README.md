# Sandbox Module

## Purpose

The sandbox module is a home for standalone TUI mockups used to test frontend
ideas: layout, colors, widgets, input flows. Nothing here talks to a real
service or storage layer, and nothing is persisted between runs.

Use it to try out a UI idea quickly before deciding whether it deserves a real
module with its own service/storage layer.

## Important Ideas

- State lives only in memory for the run; closing the TUI throws it away.
- No `service.py` or `storage.py` here on purpose — that's the point.
- If an idea proves out and needs to persist real data, promote it into its
  own proper module instead of growing this one.
- This module (and now `timer`/`task`, for their real TUIs) depends on
  **Textual**. `timer`'s and `task`'s `service.py`/`storage.py` stay
  stdlib-only on purpose, so scripts can `sys.path.insert` straight to
  `src/` and import the data layer with a bare `python3` — no venv, no
  `typer`, no Textual. Their `cli.py` already needed `typer` regardless;
  what matters is it doesn't *also* need Textual at import time — `tui.py`
  is imported lazily, only from inside the bare-command branch, so
  `zeltimer status` (or any other subcommand) never pays for it. Sandbox
  itself has no callers at all, so it's still the lowest-risk place to try
  a TUI idea before it's real.
- `screens.py`, `commands.py`, and `graphics.py` hold small pieces shared by
  everything in this module (a prompt dialog, a command-palette provider,
  custom Rich-rendered widgets like the water glass, XP bar, streak heatmap,
  and Gantt-style timeline row).
- The app defaults to the `ansi-dark` theme, so colors come from the
  terminal's own ANSI palette and the background is left alone (transparent
  if your terminal is). Switch to any of Textual's built-in themes from the
  command palette (`:` then "theme") or the Profile page.

## Command

```bash
zelsandbox hub
```

## The Hub

One TUI mixing tasks, trackers, a leveling/XP system, notes, timers, a daily
schedule, a fake repo dashboard, achievements, a character sheet, and an
activity feed — eleven pages behind one `Tabs` bar, all reading and writing
one shared in-memory `Store` (`hub/store.py`) so the pages genuinely
cross-link instead of being eleven separate demos glued together:

- completing a task on **Tasks** grants XP to that task's domain
- marking a habit "done" on **Trackers** grants XP too
- **Timer** is a block per domain — a big total time up top, a scrolling
  session history below it (fixed block size; the list scrolls, the block
  doesn't grow), a couple of preset one-key session starts, and a normal
  start that asks for a title. Stopping a session past a minute grants XP
- **Levels** shows those five domains (Career/Health/Learning/Creative/
  Social) leveling up, plus a character level aggregating all of them
- **Achievements** are computed live from everything above (complete a
  task, hit a streak, fill the water goal — badges unlock themselves)
- **Home** and **Activity** are pure rollups of everything that happened
  anywhere else
- **Schedule** and **Repos** are lighter, more decorative pages (a Gantt-
  style day timeline; a fake `git status` dashboard with a simulated async
  refresh) — the sandbox equivalent of `zelblock` and `zelrepo`
- **Notes** and **Profile** round it out: a real `TextArea` + `Markdown`
  preview note editor, and a character-sheet-style settings page

```text
click a tab, or ctrl+left / ctrl+right   switch pages
<page's own keys>                        each page has its own local keymap,
                                          shown in the footer — e.g. on Tasks,
                                          a add, enter complete, d delete
:                                        command palette — "Go: <Page>" plus
                                          every visible page's own actions
q                                        quit
```

Nothing here is real. In the actual system this would be driven by real
completions from `zeltask`/`zeltimer`/`zelhabit`/`zeljournal`/`zelrepo`, and
the domain list would come from `zelforge.core.domains` instead of the
hardcoded five in `hub/store.py`.

## Why Textual

Sandbox exists to prototype frontend ideas, so it's the place in this repo
that benefits most from a real TUI framework instead of raw `curses`:
reactive widgets, CSS-driven layout and theming, `TabbedContent` for
multi-page navigation with state that survives switching away, `DataTable`
for the Tasks/Timer/Repos pages, `TextArea` + `Markdown` for Notes, a
built-in fuzzy command palette, toast notifications, async workers (the
Repos page's simulated refresh), mouse support, and a proper async test
harness (`App.run_test()` / `Pilot`) all come for free. `curses` makes you
rebuild the app shell every time; Textual lets you write the app.

### The block/keymap pattern

Every page is a `Page(Vertical, can_focus=True)` subclass (`hub/pages/
base.py`) with its own `BINDINGS` — those only fire while the page (or its
focused child) has focus, which `HubApp` sets automatically on every tab
switch. Verified empirically (`Pilot`-driven test): a focused widget's own
`BINDINGS` shadow an ancestor's for the same key, but a key that widget
*doesn't* claim correctly bubbles up to the ancestor — so a page with a
`DataTable` can bind plain letters like `a`/`d` for its own actions even
while the table itself holds focus for arrow-key navigation, while `enter`
(which `DataTable` claims for `select_cursor`) is instead handled via its
`RowSelected` message.

Pages that need a whole sub-navigation layer of their own (Trackers'
water/sleep/medication/mood/habits; Levels' five domains) nest a second
tier of focusable, `BINDINGS`-carrying widgets inside the page — the same
pattern, one level deeper, each sub-block's hotkey letter kept out of every
other sub-block's own keymap on purpose.

### A real bug worth knowing about

Focusing a widget that lives inside a `TabbedContent` pane appears to itself
trigger further `TabActivated` events (reproduced: a single explicit tab
switch fired the handler 2-3 times). Handling that message with a
synchronous `.focus()` call raced `TabbedContent`'s own active-pane
bookkeeping and could bounce `.active` back to the first tab. Fixed with two
guards in `HubApp`: skip re-handling a `TabActivated` for a tab already
handled, and defer the actual `.focus()` call past the current refresh via
`call_after_refresh` so it isn't racing the switch. Also: `Pilot.press()` in
rapid, zero-delay succession isn't a reliable stand-in for a human typing —
some of the above only reproduced under scripted back-to-back key presses
with no `asyncio.sleep` between them, and was confirmed fine both with
realistic delays in a headless test and live in a real terminal.

To add a new Hub page: create `hub/pages/<name>.py` with a `<Name>Page(Page)`
class (set `TAB_ID`/`TAB_TITLE`), add it to the `PAGES` list in `hub/app.py`,
and add any new shared state/methods to `hub/store.py`.
