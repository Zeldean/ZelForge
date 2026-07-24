# Block Module

## Purpose

The block module is for time blocking and day layout planning.

It should help arrange tasks or plans into a visible day schedule. This may
become a web or TUI-first module later because visual layout matters more here
than in simple list commands.

## Intended Flow

```text
define day start and end
add planned blocks
arrange blocks into a day layout
display the plan
adjust or delete blocks
link blocks to tasks or timers later
```

## Important Ideas

- Time blocks are planned time, not the same as timer sessions.
- Timer sessions are what actually happened.
- Tasks are work items.
- Blocks can later connect planned work to actual timer data.
- A visual interface may be more useful than a pure CLI for this module.

## Possible Commands

```bash
zel config set block.day_start "08:00"
zel config set block.day_end "18:00"
zelblock add "Deep work" --from 09:00 --to 11:00
zelblock list
zelblock delete <block-id>
```

## Notes From Old Attempts

The old block attempt had a small Flask app that laid out tasks on a day
timeline. The rebuilt version should separate the planning data and service
logic first, then add a visual interface when the model is clear.
