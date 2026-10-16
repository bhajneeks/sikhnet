# Team, roles, and branches

Everyone builds toward the judge requirements R1-R5 in `docs/REQUIREMENTS.md`.

| Person | Role | Branch | Owns (only they edit) | Judge reqs |
|---|---|---|---|---|
| **Jaspreet** | **Product & PM** — client expectations, priorities, scope, acceptance, demo | `jaspreet/product` | `docs/REQUIREMENTS.md`, `docs/DEMO.md`, `evals/questions.jsonl` (acceptance cases), priority calls | owns the definition of done for all |
| **Avneet** | **RAG engine** — ingest, retrieval, prompts, Claude call, `/api/ask` | `avneet/rag` | `ingest/ingest.py`, `backend/retrieval.py`, `backend/prompts.py`, `backend/llm.py`, `backend/app.py`, `data/`, `evals/run_evals.py` | R1 citations, R2 follow-ups, R4 perspectives |
| **Bhajneek** | **Future features** — multi-property scaling + new features | `bhajneek/features` | `backend/features/` (incl. `/api/categories`, `/api/surprise`), `ingest/sources/`, `docs/ROADMAP.md` | R3 multi-source, R5 Surprise me |
| **Manveer** | **UI / UX** — the whole chat experience, designed with Claude Design | `manveer/ui` | `frontend/` | the visible side of R1-R5 |

Shared (anyone, small PRs, tell the team): `docs/ARCHITECTURE.md` (via
`capture-decision`), `CLAUDE.md`, `TEAM.md`, `.claude/`, `requirements.txt`.
Your own status file `docs/brain/status/<name>.md`: only you.

## Routing — who to ask

| Question type | Ask |
|---|---|
| What does the client/judge expect? Is this in scope? What's the priority? How should X behave for users? Wording/tone of answers? | **Jaspreet** |
| Retrieval quality, prompt behavior, `/api/ask` shape, dataset import | **Avneet** |
| Other properties (SikhiWiki etc.), Surprise me, categories, anything "later/next" | **Bhajneek** |
| Layout, visual design, interaction, how something looks on screen | **Manveer** |

Claude: when a question belongs to someone else, **don't guess** — draft a short,
specific message the user can send to that person (one question, options if
helpful), and once answered, record it with `capture-decision`. Product and
client-expectation questions always go to Jaspreet.

## How the pieces connect

```
data/raw ─ingest─▶ qa.jsonl ─search()─▶ /api/ask ───────────────▶ frontend chat (Manveer)
              (Avneet)          (Avneet)  (answer, citations,        ▲
ingest/sources ─▶ secondary records        follow_ups, perspectives)  │
   (Bhajneek)                                                         │
backend/features ─▶ /api/categories, /api/surprise ───────────────────┘
   (Bhajneek)
docs/REQUIREMENTS.md + evals/questions.jsonl (Jaspreet) ─▶ acceptance for everything
```

`main` always runs end to end; each owner upgrades their piece without breaking
the contracts in `docs/ARCHITECTURE.md`.

## Git workflow

```bash
git checkout <name>/<role>       # your branch already exists on origin
git pull origin main             # pick up merged work, often
# ...work...
git add -A && git commit -m "ui: follow-up chips"
git push origin HEAD
# open a PR into main when a piece works; Jaspreet checks it against REQUIREMENTS.md
```

- Small PRs, merge to `main` at least every 3-4 hours. `main` must always run.
- Conflicts in a shared file → the person merging second resolves it.

## Timeline (aim to finish well under 24h)

| Hour | Milestone |
|---|---|
| 0-1 | Everyone runs `main`; Jaspreet confirms priorities; real dataset in `data/raw/`; Manveer starts UI in Claude Design |
| 1-4 | Real data ingested; cited answers + follow-ups (Avneet); Surprise me works (Bhajneek); UI v1 (Manveer); acceptance questions (Jaspreet) |
| 4-8 | Perspectives, multi-source, UI polish; **merge everything** |
| 8-10 | Deploy, demo script, fix top failures. **Feature freeze.** |
| 10-12 | Rehearse demo, sleep 😴 |
