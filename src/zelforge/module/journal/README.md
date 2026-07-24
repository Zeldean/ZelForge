# Journal Module

## Purpose

The journal module captures notes and indexes markdown files in the user's
vault.

It should support quick note capture from the CLI, but it should also understand
configured vault paths so other modules can refer to journal files later.

## Intended Flow

```text
configure journal vault path
add quick note
create or append daily note
index markdown vault
list or search indexed files
manage ignored paths
```

## Important Ideas

- Journal paths are module paths stored in config, such as `journal.vault`.
- Date and file naming behavior should be settings, such as
  `journal.date_format`.
- Quick notes and vault indexing are related but separate workflows.
- Index data should live in ZelForge state, not inside the source tree.
- Journal should be usable by future task, timer, and summary features.

## Possible Commands

```bash
zel paths set journal.vault ~/Vault
zel config set journal.date_format "%Y-%m-%d"
zel journal note "Worked on timer architecture"
zel journal daily
zel journal index
zel journal files
zel journal ignore add "archive/**"
```

## Notes From Old Attempts

The old journal app handled note capture, editor input, automatic tags, vault
indexing, file listing, and ignore patterns. The rebuilt version should start
with vault configuration and one reliable capture/index flow.
