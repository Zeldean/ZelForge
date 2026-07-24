# Task Module

## Purpose

The task module manages active work items, completed work, and reusable task
blueprints.

It should be simple enough for quick CLI capture, but structured enough to feed
daily planning, timer links, and future dashboard views.

## Intended Flow

```text
create task
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
- The first version should stay small: create, list, complete.

## Possible Commands

```bash
zel task add "Write timer service"
zel task list
zel task done <task-id>
zel task blueprint add daily-review "Daily review"
zel task blueprint list
```

## Notes From Old Attempts

The old task app had active tasks, completed/archive storage, and blueprint
commands. Those concepts are worth keeping, but the new version should use the
shared ZelForge config, paths, and app-layer structure.
