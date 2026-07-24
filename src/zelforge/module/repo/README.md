# Repo Module

## Purpose

The repo module helps track and maintain local code repositories.

It should focus on the user's local project collection: indexing repositories,
recording metadata, grouping by category, and later helping with maintenance
tasks.

## Intended Flow

```text
configure repo roots
scan for repositories
index repo metadata
list repos by category or status
open or inspect a repo
run safe maintenance checks later
```

## Important Ideas

- Repo roots should be configured as module paths, such as `repo.root`.
- Repository metadata should be stored as state, not scattered across source
  folders.
- Maintenance commands should be explicit and safe.
- This module should not replace Git; it should organize the user's repo
  workspace around Git.

## Possible Commands

```bash
zel paths set repo.root ~/Repos
zel repo scan
zel repo list
zel repo list --category active
zel repo status
```

## Notes From Old Attempts

The old repo attempt contained centralized repo metadata, category data, and
plans for discovering, cloning, updating, and release helpers. The new version
should begin with indexing and listing local repos.
