---
name: friction-log
description: Log blockers, confusing behavior, and wasted time to docs/brain/friction.md so teammates don't hit the same wall. Use when something fails unexpectedly, setup needs a workaround, docs and code disagree, or the user says "this is broken", "why doesn't this work", "ugh", "stuck".
---

# Friction Log

Adapted from gbrain's `_friction-protocol.md`. Four people hitting the same
setup bug is four times the wasted hours. Log it once, fix it once.

## When to log

- A command failed with an unhelpful error.
- Setup needed a manual workaround (env var, version pin, missing dep).
- The code did something different from what `docs/ARCHITECTURE.md` says.
- You were blocked waiting on another lane.
- Also log *delight*: a trick that saved a lot of time.

## How

Append to `docs/brain/friction.md` (newest at top of the list):

```markdown
- 2026-10-16 15:10 · Avneet · **error** · frontend
  CORS error calling /api/ask from file:// page.
  Fix: open via http://localhost:8000/ (backend serves frontend/).
```

Severity: `blocker` (can't proceed) · `error` (failed unexpectedly) ·
`confused` (docs/tool mismatch) · `nit` (polish) · `delight`.

If there's a fix, include it. If it's a blocker owned by another lane, also add
it to your status file's "Blocked on" section so `team-sync` surfaces it.

Before debugging anything, grep `docs/brain/friction.md` — someone may have
already solved it.
