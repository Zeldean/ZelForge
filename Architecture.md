# ZelForge Architecture

ZelForge is being rebuilt as one Python package instead of many separate tools.
The goal is a small, clear structure that is easy to work on over time.

The app is CLI-first today, but the design should also support a future TUI or
web dashboard without rewriting the real behavior.

## Main Idea

Keep the interfaces thin and put the real behavior in app modules.

```text
CLI command -> app service -> app storage -> data
TUI screen   -> app service -> app storage -> data
Web route   -> app service -> app storage -> data
```

The CLI should parse arguments and print results. It should not own the main app
rules. A future TUI or web app should be able to call the same service code.

## Package Shape

Recommended structure:

```text
src/zelforge/
  cli.py

  core/
    paths.py
    storage.py
    config.py
    time.py
    errors.py

  module/
    timer/
      cli.py
      service.py
      storage.py
      models.py

    task/
      cli.py
      service.py
      storage.py
      models.py

    journal/
      cli.py
      service.py
      storage.py
      models.py

    media/
      cli.py
      service.py
      storage.py
      models.py
```

The `module/` name is the current working name. It may become `apps/` later if
that feels clearer.

## What Goes In Core

`core/` is for shared infrastructure only. It should not know about timers,
tasks, journals, media, habits, or any other specific app.

Good things for `core/`:

- `paths.py`: where state, config, and cache files live.
- `storage.py`: generic JSON and text file helpers.
- `config.py`: global user settings, if needed.
- `time.py`: UTC timestamp helpers.
- `ids.py`: ID helpers, if needed.
- `errors.py`: shared exception types.

Avoid putting app-specific behavior in `core/`.

For example, this does not belong in `core/`:

```text
core/timer.py
core/task_storage.py
core/journal_service.py
```

If a file knows about a specific app's nouns, it usually belongs in that app
module.

## App Layers

Each app should own its own small set of layers.

```text
module/timer/
  cli.py       # terminal commands and output
  service.py   # workflows and rules
  storage.py   # loading and saving timer data
  models.py    # timer/session data shapes
```

Layer meaning:

- `cli.py`: Typer command parsing and terminal output.
- `service.py`: the real workflow rules.
- `storage.py`: persistence for that app.
- `models.py`: data structures for that app.

This keeps the project simple without turning it into a large enterprise-style
folder tree.

## Data Storage

For now, ZelForge should use JSON files because they are easy to inspect,
change, and back up during the rebuild.

Runtime data should live under the user's state directory:

```text
~/.local/state/zelforge/
```

Scratch or reference data may exist under `src/data/` while designs are being
worked out, but normal app behavior should not depend on `src/data/`.

Preferred JSON file shape:

```json
{
  "id": "file-level-uuid",
  "schema_version": 1,
  "description": "",
  "created_at": "2026-05-31T10:00:00+00:00",
  "updated_at": "2026-05-31T10:00:00+00:00",
  "timers": []
}
```

Use separate JSON files when data has separate lifecycles. For the timer app,
timer definitions and timer sessions should be separate:

```text
~/.local/state/zelforge/timer/timers.json
~/.local/state/zelforge/timer/sessions.json
```

## Root CLI Commands

The root `zel` command should handle ZelForge-wide setup, inspection, and
configuration.

Module-specific work should have its own root command:

```text
zeltimer
zeltask
zeljournal
zelmedia
zelscript
zelrepo
zelhabit
zelblock
```

This keeps quick daily commands short while still allowing `zel` to manage the
whole ZelForge environment.

Current root command direction:

```bash
zel init
zel paths
zel paths list
zel paths set journal.vault ~/Vault
zel paths get journal.vault
zel paths unset journal.vault
zel modules
zel config
zel config set journal.date_format "%Y-%m-%d"
zel config get journal.date_format
zel config unset journal.date_format
zel version
```

`zel init` should initialize the base folders and global config file using the
paths resolved by `core.paths`.

Module storage should be initialized by module commands such as `zeltimer init`.

Core state/config/cache locations are not stored as normal user config yet.
They come from `core.paths` and may be overridden with environment variables:

```text
ZEL_STATE_DIR
ZEL_CONFIG_DIR
ZEL_CACHE_DIR
```

`zel init` should show both the resolved paths and whether each path came from
the default or from an environment variable.

Module paths are different. They are user-facing app paths, such as where the
journal vault lives. These should be stored in config with module-prefixed keys:

```text
journal.vault
journal.daily_dir
media.library
```

General settings should use the same key style:

```text
journal.date_format
timer.day_start
```

## Timer App Direction

The timer should be the first real vertical slice of ZelForge.

The basic idea:

1. Create a timer, such as `writing`, `coding`, or `admin`.
2. Start a timer when work begins.
3. Write the active work into a live log while it is happening.
4. Stop the timer when work ends.
5. Convert the live log into permanent JSON storage.
6. Use the stored sessions later for summaries, reports, and dashboards.

The live log is useful because active timer work is temporary and may change
quickly. The permanent JSON files are useful because completed sessions should
be stable, queryable, and easier to summarize later.

Possible timer commands:

```bash
zeltimer init
zeltimer add writing --code write
zeltimer list
zeltimer start write
zeltimer status
zeltimer stop
zeltimer sessions
```

Possible future commands:

```bash
zeltimer pause
zeltimer resume
zeltimer cancel
zeltimer edit-session
zeltimer summary --today
zeltimer summary --week
```

Plain flow:

```text
start timer
  -> create or update active live log
  -> show status while running

stop timer
  -> read active live log
  -> create finished session record
  -> save session to JSON
  -> clear active live log
```

The timer should prevent confusing states. For example, if one timer is already
running, starting another timer should either fail clearly or ask for an
explicit switch command later.

## Current Build Priority

Build one small timer slice first:

```text
create timer
list timers
start timer
show status
stop timer
list sessions
```

After that works cleanly, add summaries and editing.

The important thing is to keep each step small and understandable. ZelForge
should grow by adding useful vertical slices, not by copying large chunks of old
code back into the project.
