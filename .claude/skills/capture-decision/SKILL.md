---
name: capture-decision
description: Record a team decision, fact, or contract change into the shared brain (docs/brain/decisions/) with who decided, why, and the source. Use when the user says "remember this", "we decided", "let's go with", "capture this", "note that", or when a change affects another person's lane (schema, API shape, model choice, stack choice).
---

# Capture Decision

Adapted from gbrain's `capture` + `brain-ops` skills: the brain is only useful if
every entry is explicit, dated, attributed, and has a source. No vibes.

## When

- A choice that other lanes depend on (data schema, API contract, model, prompt
  rules, deploy target, UI flow).
- A fact learned the hard way ("the dataset has 412 rows with empty answers").
- A reversal of a previous decision — never delete the old one; mark it
  superseded and link the new one.

## How

1. Check `docs/brain/decisions/` for an existing entry on the same topic.
   Update it instead of creating a duplicate.
2. Otherwise create `docs/brain/decisions/NNN-short-slug.md` (next number):

```markdown
---
id: 007
title: Use BM25 for v1 retrieval, embeddings later
date: 2026-10-16
decided_by: Bhajneek, Manveer
affects: [data, backend]
status: active        # active | superseded-by-NNN
source: team chat 2pm / PR #12 / measurement in evals/results.md
---

**Decision:** ...
**Why:** ...
**Impact on other lanes:** what each affected owner must change, if anything.
```

3. Add a one-line entry to `docs/brain/decisions/README.md` index.
4. If a contract changed, update `docs/ARCHITECTURE.md` in the same commit.
5. Tell the user exactly who to ping (the owners in `affects`).

## Rules

- One decision per file. Short.
- `source` is required. If it's just "the user said so in chat", write that.
- Never silently overwrite a decision someone else made.
