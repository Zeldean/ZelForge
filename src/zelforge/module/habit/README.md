# Habit Module

## Purpose

The habit module tracks small daily habits and health-style check-ins.

It should make daily logging quick from the CLI while keeping the data simple
enough for summaries later.

## Intended Flow

```text
record today's habit value
add to numeric habit totals
show today's habit summary
review a specific date
summarize streaks or trends later
```

## Important Ideas

- Some habits are boolean, such as taking a pill.
- Some habits are numeric, such as water amount.
- Some habits are durations, such as sleep.
- Daily records should be easy to display as one compact day view.
- The first version should use a small fixed habit set before adding custom
  habit definitions.

## Possible Commands

```bash
zelhabit pill
zelhabit water add 500
zelhabit sleep 7 30
zelhabit read-book
zelhabit show
zelhabit show --date 2026-07-24
```

## Notes From Old Attempts

The old habits app tracked pill, water, sleep, Duolingo, reading, and daily
display output. That scope is useful, but the rebuilt version should start with
the smallest daily check-in flow.
