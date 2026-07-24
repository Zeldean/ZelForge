# Timer Module

## Purpose

The timer module tracks time spent on named activities such as coding, writing,
admin, study, or chores.

It should support frequent start/stop use without making the user think too
much about storage. Active work is recorded in a live log first. Older closed
entries are later saved into permanent JSON session storage.

## Intended Flow

```text
create timer
start timer
stop timer
resume timer-specific previous session
review sessions by day, range, or timer
summarize time later
```

## Important Ideas

- A timer is a reusable thing, such as `coding`.
- A session is one period of work for a timer.
- The live log records active and recent start/stop events.
- Permanent JSON stores closed sessions after they are old enough to save.
- Display commands should combine saved sessions and current live-log entries.
- Sessions should group by day, then by timer when no timer is selected.

## Possible Commands

```bash
zel timer add coding --code code
zel timer start code
zel timer stop
zel timer resume code
zel timer status
zel timer sessions
zel timer sessions code --date 2026-07-24
zel timer sessions --from 2026-07-20 --to 2026-07-24
```

## Notes From Old Attempts

The old timer already had useful ideas around a text log, session rebuilding,
status filtering by date, and timer-specific resume. Those ideas should be
rebuilt deliberately rather than copied directly.
