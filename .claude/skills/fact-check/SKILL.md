---
name: fact-check
description: Check a bot answer (or a batch of eval outputs) claim-by-claim against the dataset entries it cites, labeling each claim supported / unsupported / contradicted. Use when the user says "fact check", "is this answer right", "verify the claims", "check this response", or when reviewing eval failures.
---

# Fact Check

Adapted from gbrain's `fact-check` skill, narrowed to our dataset as the single
source of truth.

## Steps

1. Split the answer into atomic claims (one fact each). Ignore pleasantries.
2. For each claim, look up the cited entry ids in `data/processed/qa.jsonl`
   (`grep '"id": "<id>"'`). If no citation, search the dataset for the topic.
3. Label each claim:
   - `supported` — the cited entry says this.
   - `unsupported` — no entry says this (possible hallucination).
   - `contradicted` — an entry says the opposite.
   - `misquoted` — Gurbani/quote text differs from the entry's exact text.
4. Output a table: claim · label · entry id · the exact supporting line.
5. Verdict: PASS only if zero `contradicted`/`misquoted` and no `unsupported`
   claim on a factual/religious point.
6. For eval runs, append the failures to `evals/results.md` so the backend lane
   can see what to fix.

## Rules

- The dataset is the authority here, not your general knowledge. If you believe
  the dataset itself is wrong, flag it separately as "dataset issue" — don't
  silently "correct" the bot toward your own knowledge.
