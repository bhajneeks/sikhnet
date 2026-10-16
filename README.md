# sikhnet

A ChatGPT-style assistant that answers questions about Sikhi, grounded in our
curated Q&A dataset, with citations back to the original answers.

Team: Manveer · Bhajneek · Avneet · Jaspreet — see [TEAM.md](TEAM.md).

## Quick start

```bash
git clone https://github.com/bhajneeks/sikhnet.git && cd sikhnet
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add ANTHROPIC_API_KEY (optional: works without, in fallback mode)
uvicorn backend.app:app --reload --port 8000
# open http://localhost:8000
```

Load the real dataset (from the team Drive folder) into `data/raw/`, then:

```bash
python3 ingest/ingest.py data/raw/<file.csv|xlsx|json>
```

Then check out your own branch: `git checkout <yourname>/<lane>` (see TEAM.md).

## Working with Claude Code

Open this folder in Claude Code. At session start a hook runs
`scripts/team-context.sh`, which shows what each teammate is doing (read from
their own branch, even before it's merged). Project skills live in
`.claude/skills/` — see [CLAUDE.md](CLAUDE.md). The shared team memory is
`docs/brain/` (status, decisions, friction log).

## Layout

```
ingest/        raw export → data/processed/qa.jsonl         (Bhajneek)
backend/       retrieval.py (Bhajneek) · app.py, llm.py, prompts.py (Manveer)
frontend/      chat UI, served at /                          (Avneet)
evals/         eval questions + runner                       (Jaspreet)
docs/          ARCHITECTURE.md (contracts) · brain/ (status, decisions, friction)
.claude/       shared skills + session-start hook
```
