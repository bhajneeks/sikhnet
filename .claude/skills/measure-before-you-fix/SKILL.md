---
name: measure-before-you-fix
description: Debugging discipline — reproduce and measure the failing thing before changing code. Use when something is "slow", "broken", "timing out", "not returning good answers", "retrieval is bad", or before any refactor meant to fix a bug.
---

# Measure Before You Fix

Adapted from gbrain's `measure-before-you-fix`. In a 24-hour hackathon the
expensive mistake is a confident rewrite of the wrong thing.

## The rule

**One concrete measurement of the suspect step before any code change.**
If you can't state the number (latency in ms, recall@5, the exact failing
input), you don't know the cause yet.

## Procedure

1. Reproduce with the smallest input: one question, one curl, one function call.
   ```bash
   time curl -s localhost:8000/api/ask -H 'content-type: application/json' \
     -d '{"question":"What is Vaisakhi?"}' | python3 -m json.tool
   ```
2. Isolate the step: is it retrieval (`python3 -c "from backend.retrieval import search; print(search('...'))"`),
   the LLM call, or the UI?
3. Write down the measurement (in your reply and, if it took > 15 min to find,
   in `docs/brain/friction.md`).
4. Only now design the fix, sized to the number you measured.
5. Re-measure after the fix and report before → after.

## Red flags

- You have a root cause but no measurement.
- You're about to rewrite a module you haven't run once.
- "Answers are bad" with no eval run → run `python3 evals/run_evals.py` first.
