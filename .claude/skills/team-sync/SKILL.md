---
name: team-sync
description: Start-of-session and end-of-session sync for the 4-person sikhnet team. Use at the start of every session, when asked "what is everyone working on", "sync", "catch me up", "who owns X", or before starting any new piece of work, and again before ending a session ("wrap up", "I'm done for now", "push my work").
---

# Team Sync

Four people (Manveer, Bhajneek, Avneet, Jaspreet) work in parallel on separate
branches. This skill keeps every Claude session aware of what the others are
building so work does not overlap and the pieces connect.

The shared brain lives in `docs/brain/`. Every claim about what someone is doing
must come from a status file or a git log, never from a guess.

## Start of session

1. Run `scripts/team-context.sh` (the SessionStart hook already runs it; re-run
   if the session is long or you are about to start new work). It fetches
   origin and prints every teammate's status file as it exists **on their own
   branch**, plus their unmerged commits.
2. Read `TEAM.md` (lanes and ownership) and `docs/ARCHITECTURE.md` (the
   contracts between lanes).
3. Identify who the current user is (`git config user.name`, or ask once).
4. Tell the user in 3-6 lines:
   - what each teammate is doing right now (from their status file),
   - anything that touches the user's lane (a contract change, a blocker
     they're waiting on, a file someone else is editing),
   - anything stale (a status file not updated in > 3 hours — say so).
5. Before starting a task, check `docs/brain/status/*.md` "Now" lines and
   `TEAM.md` ownership. If the task belongs to another lane, say who owns it and
   ask before touching their files.

## During the session

- Changing a contract in `docs/ARCHITECTURE.md` (data schema, API shape,
  function signature another lane calls) is a **team decision**: write it with
  the `capture-decision` skill and tell the user to ping the affected owner.
- Hit a blocker or something confusing? Use the `friction-log` skill.

## End of session (or every ~1-2 hours)

1. Update your own `docs/brain/status/<name>.md` (format below). Keep it short.
2. Commit on your branch and push: `git push origin HEAD`.
3. If a piece is usable by others, open a PR into `main` (small PRs, often).
   Merge to main at least every few hours so others can build on it.

## Status file format

```markdown
# <Name> — <lane>
updated: 2026-10-16 14:30
branch: <name>/<lane>

## Now
One line: what I'm doing right now.

## Done
- bullets, newest first

## Next
- bullets

## Blocked on / needs from others
- "@Avneet: need final /api/ask response shape" (or "nothing")

## Files I'm touching
- backend/app.py, backend/llm.py
```

## Rules

- Never edit another person's status file.
- Never claim someone is working on something without a source (status file,
  commit, PR). Say "no status yet" instead.
- Don't rewrite files in another lane; propose the change to the owner.
