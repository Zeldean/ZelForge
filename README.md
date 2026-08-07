<p align="center">
  <img src="assets/branding/zelforge-logo-title.png" alt="ZelForge" width="720">
</p>

<p align="center">
  CLI-first personal productivity tools rebuilt into one Python package.
</p>

# ZelForge

ZelForge is a rebuild of my earlier Zel command-line tools. The goal is one
small, deliberate toolkit for tracking time, tasks, notes, media, scripts,
repos, habits, and planning blocks.

The project is intentionally CLI-first. TUI and future web interfaces should
call the same service layer as the CLI instead of becoming separate apps with
separate logic.

## Status

ZelForge is an early rebuild. The current useful modules are:

| Module | Command | Status |
| --- | --- | --- |
| Core | `zel` | Init, paths, config, module listing, shared domains |
| Timer | `zeltimer` | Timers, live log, save, status, demo TUI |
| Task | `zeltask` | Basic tasks, priorities, shared domains, demo TUI |

Other module commands exist as placeholders while the old tools are rebuilt
piece by piece.

## Quick Start

```bash
python -m pip install -e .
zel init
zel modules
zeltimer status
zeltask list
```

For my development setup, the package can also be installed into a dedicated
virtual environment under `~/.venvs/`.

## Commands

Global commands:

```bash
zel init
zel version
zel modules
zel paths list
zel config show
zel domains list
```

Timer commands:

```bash
zeltimer add "Career Work" --code 10
zeltimer start 10 --title "Daily Stand-Up"
zeltimer stop 10
zeltimer status
zeltimer save
zeltimer tui
```

Task commands:

```bash
zeltask add "Review timer flow" --priority 3 --domain career
zeltask list
zeltask show <task-id>
zeltask done <task-id>
zeltask tui
```

## Storage

Default runtime paths:

```text
state   ~/.local/state/zelforge
config  ~/.config/zelforge
cache   ~/.cache/zelforge
```

These can be overridden with:

```bash
export ZEL_STATE_DIR=/path/to/state
export ZEL_CONFIG_DIR=/path/to/config
export ZEL_CACHE_DIR=/path/to/cache
```

Timer data is currently stored as:

```text
timer/log.txt       live start/stop event log
timer/timers.json   timer definitions
timer/sessions.json saved sessions
```

Shared domains are stored globally:

```text
domains.json
```

## Architecture

The intended shape is:

```text
CLI command -> module service -> module storage -> data
TUI screen   -> module service -> module storage -> data
Web route    -> module service -> module storage -> data
```

The CLI and TUI should stay thin. Business rules belong in each module's
`service.py`, persistence belongs in that module's `storage.py`, and shared
infrastructure belongs in `core/`.

Current package shape:

```text
src/zelforge/
  cli.py
  core/
  module/
    timer/
    task/
    journal/
    media/
    script/
    repo/
    habit/
    block/
```

## Roadmap

- Improve timer date/range display.
- Add timer resume.
- Promote and clean timer logs safely over time.
- Expand task filtering and editing.
- Add recurring tasks and task history/archive behavior.
- Rebuild journal, media, script, repo, habit, and block modules deliberately.
- Add richer TUI screens once the service layer settles.
- Consider a small web dashboard later.

## Old Code

Old attempts live under `dump/old/` as read-only reference material. The rebuild
should reuse ideas deliberately, not copy old code wholesale.
