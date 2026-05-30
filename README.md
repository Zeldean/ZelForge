# ZelForge

ZelForge is a CLI-first productivity toolkit being rebuilt from the earlier
Zel tools.

The current goal is a clean foundation:

- one repo
- one installable Python package
- one root CLI
- shared core utilities
- app modules added back deliberately over time

Old code has been moved to `dump/old/` as reference material. That folder is
ignored by git and should be treated as read-only while rebuilding.

## Install For Development

```bash
python -m pip install -e .
```

## Usage

```bash
zel --help
zel version
```

## Intended Architecture

```text
src/zelforge/
  cli.py
  core/
  apps/
    timer/
    task/
    journal/
    media/
```

The CLI should stay thin. Real behavior should live in app service modules so a
future web dashboard can call the same logic.
