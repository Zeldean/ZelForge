# Task Module

## Purpose

The task module manages active work items, completed work, and reusable task
blueprints.

It should be simple enough for quick CLI capture, but structured enough to feed
daily planning, timer links, and future dashboard views.

## Intended Flow

```text
create task
edit task
list active tasks
complete task
review completed tasks
create reusable blueprint
generate recurring or repeated tasks from blueprints
```

## Important Ideas

- Active tasks are things still needing attention.
- Completed tasks should move into history instead of disappearing.
- Blueprints describe reusable tasks or recurring task shapes.
- Tasks may later link to timer sessions, journal notes, projects, or domains.
- The first version should stay small: create, edit, list, show, complete,
  cancel, and reopen.

## Possible Commands

```bash
zeltask add "Write timer service"
zeltask add "Index journal vault" --priority high --tag journal --tag index
zeltask list
zeltask list --all
zeltask show <task-id>
zeltask edit <task-id> --title "Write task service"
zeltask done <task-id>
zeltask cancel <task-id>
zeltask reopen <task-id>
```

## Notes From Old Attempts

The old task app had active tasks, completed/archive storage, and blueprint
commands. Those concepts are worth keeping, but the new version should use the
shared ZelForge config, paths, and app-layer structure.

Blueprints and recurring tasks are planned for later.
