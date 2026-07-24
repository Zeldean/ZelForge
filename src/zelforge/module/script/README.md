# Script Module

## Purpose

The script module is for small utility commands that do not yet deserve their
own full module.

It should be treated as a staging area for useful one-off tools. If a script
grows into a real domain, it should move into its own module.

## Intended Flow

```text
run small helper command
preview file changes when possible
promote stable scripts into focused modules
remove scripts that are no longer useful
```

## Important Ideas

- Keep scripts small and obvious.
- Avoid turning this into a junk drawer for important app logic.
- Prefer dry-run behavior for file operations.
- Promote repeated workflows into proper modules.

## Possible Commands

```bash
zelscript choose one two three
zelscript rename-sequential ./folder --dry-run
zelscript convert-png ./folder
```

## Notes From Old Attempts

The old script app included choice prompts, a pomodoro-like timer, sequential
renaming, and image conversion. Some of these may belong elsewhere now, so this
module should stay temporary and conservative.
