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
zeltask add "Plan career work" --priority 3 --domain career
zeltask list
zeltask list --all
zeltask show <task-id>
zeltask edit <task-id> --title "Write task service"
zeltask done <task-id>
zeltask cancel <task-id>
zeltask reopen <task-id>
zeltask tui
```

Subtask commands:

```bash
zeltask sub add <task-id> "Draft service changes"
zeltask sub list <task-id>
zeltask sub list <task-id> --all
zeltask sub edit <task-id> <subtask-id> --title "Draft CLI changes"
zeltask sub done <task-id> <subtask-id>
zeltask sub cancel <task-id> <subtask-id>
zeltask sub reopen <task-id> <subtask-id>
zeltask sub remove <task-id> <subtask-id>
```

## Demo TUI

`zeltask tui` opens a small curses interface over the same task services used by
the CLI. It can browse active or all tasks, show details for the selected task,
create a new task, and change task status.

Subtasks are displayed in the selected task details. Parent tasks do not
automatically change status when subtasks are completed; that workflow should
remain explicit until recurring tasks and completion rules are designed.

Controls:

```text
up/down or j/k  select task
tab             switch active/all tasks
a               add task
d               mark selected task done
c               cancel selected task
o               reopen selected task
r               refresh
q               quit
```

## Notes From Old Attempts

The old task app had active tasks, completed/archive storage, and blueprint
commands. Those concepts are worth keeping, but the new version should use the
shared ZelForge config, paths, and app-layer structure.

Blueprints and recurring tasks are planned for later.

Priorities are defined by the task model in code:

```text
0 none
1 low
2 medium
3 high
4 urgent
```

`--priority` accepts either the number or label. New task records store the
normalized number.

Domains are shared user state managed by the root `zel` command:

```bash
zel domains list
zel domains add career --name "Career Work"
zel domains default career
```

When a default domain is configured, new tasks use it if `--domain` is omitted.
