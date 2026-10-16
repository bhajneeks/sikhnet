# sikhnet — Claude instructions (shared by the whole team)

We're 4 people building a ChatGPT-style assistant that answers questions about
Sikhi, grounded in our existing Q&A dataset. Hackathon: ship a working demo
fast, don't overlap, keep the pieces connected.

## Every session, first

1. The SessionStart hook prints team context (`scripts/team-context.sh`).
   Read it. If it didn't run, run it yourself.
2. Read `TEAM.md` (who owns what) and `docs/ARCHITECTURE.md` (the contracts).
3. Use the `team-sync` skill to tell the user what teammates are doing and
   anything that affects their lane — before writing code.

## Rules

- **Stay in your lane.** Only edit files your owner owns (see `TEAM.md`).
  Need a change elsewhere? Ask the owner, or open a small PR and tell them.
- **Contracts are sacred.** `docs/ARCHITECTURE.md` defines the data schema, the
  retrieval function, and the `/api/ask` API. Change them only via the
  `capture-decision` skill, and update the doc in the same commit.
- **Work on your branch** (`<name>/<lane>`), push often, PR into `main` small
  and often (every few hours). `main` must always run.
- **Update your status file** `docs/brain/status/<name>.md` when you start
  something new and before you stop. That's how other sessions know.
- **Grounded answers only** — see the `grounded-answer` skill. No invented
  Gurbani, no outside facts in bot answers.
- Never commit secrets. API keys go in `.env` (gitignored); see `.env.example`.

## Project skills (`.claude/skills/`)

| Skill | Use when |
|---|---|
| `team-sync` | start/end of session, "what's everyone doing", before new work |
| `capture-decision` | "we decided", contract/stack changes, "remember this" |
| `friction-log` | blockers, broken setup, workarounds, "stuck" |
| `ingest-dataset` | loading / re-loading the Q&A dataset |
| `grounded-answer` | changing prompts, retrieval, answer format |
| `fact-check` | verifying an answer or eval output against the dataset |
| `measure-before-you-fix` | anything slow/broken/bad-answers, before fixing |
| `skillify` | turning a repeated workflow into a new team skill |

Skills are adapted from [garrytan/gbrain](https://github.com/garrytan/gbrain)
(capture, query, ingest, fact-check, friction protocol, measure-before-you-fix,
skillify), without needing the gbrain CLI or database — the "brain" is the
markdown in `docs/brain/`, versioned in git.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python3 ingest/ingest.py data/raw/<file>      # build data/processed/qa.jsonl
uvicorn backend.app:app --reload --port 8000  # API + UI at http://localhost:8000
python3 evals/run_evals.py                    # grounded/cited/coverage checks
```
