# Team, lanes, and branches

Lanes are a starting proposal — swap them in the first 15 minutes if you want,
then record the final split with the `capture-decision` skill.

| Person | Lane | Branch | Owns (only they edit) | Delivers to |
|---|---|---|---|---|
| **Bhajneek** | Data + retrieval | `bhajneek/data` | `ingest/`, `backend/retrieval.py`, `data/` | `qa.jsonl` + `search()` → backend |
| **Manveer** | Backend + LLM | `manveer/backend` | `backend/app.py`, `backend/llm.py`, `backend/prompts.py` | `/api/ask` → frontend |
| **Avneet** | Frontend chat UI | `avneet/frontend` | `frontend/` | the demo experience |
| **Jaspreet** | Evals, QA, deploy, demo | `jaspreet/evals` | `evals/`, deploy config, demo script/slides | quality scores → everyone |

Shared (anyone, small PRs, tell the team): `docs/`, `CLAUDE.md`, `TEAM.md`,
`.claude/skills/`, `requirements.txt`. Your own status file: only you.

## How the pieces connect

```
data/raw/*  ──ingest.py──▶  data/processed/qa.jsonl  ──search()──▶  /api/ask  ──▶  frontend chat
 (Bhajneek)                       (Bhajneek)          (Bhajneek)   (Manveer)      (Avneet)
                                        ▲                               │
                                        └──── evals/run_evals.py ◀──────┘  (Jaspreet)
```

Every lane can work from minute one: `main` ships with a sample dataset, a
keyword `search()`, a working `/api/ask` (falls back to "top match" mode with no
API key), and a basic chat page. Each owner replaces their stub with the real
thing without breaking the contract.

## Git workflow

```bash
git checkout <name>/<lane>       # your branch already exists on origin
git pull origin main             # pick up others' merged work, often
# ...work...
git add -A && git commit -m "backend: stream answers"
git push origin HEAD
# open a PR into main when a piece works; ask one teammate to glance at it
```

- Small PRs, merge to `main` at least every 3-4 hours.
- `main` must always start and answer a question.
- Conflicts in a shared file → the person merging second resolves it.

## Timeline (aim to finish well under 24h)

| Hour | Milestone |
|---|---|
| 0-1 | Clone, run `main` end-to-end, confirm lanes, real dataset in `data/raw/` |
| 1-4 | Real data ingested; Claude answers with citations; chat UI renders citations; 20 eval questions |
| 4-8 | Better retrieval, streaming, UI polish, eval scores tracked; **merge everything** |
| 8-10 | Deploy, demo script, fix top eval failures. **Feature freeze.** |
| 10-12 | Rehearse demo, sleep 😴 |
