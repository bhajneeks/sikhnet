# sikhnet

A ChatGPT-style assistant that answers questions about Sikhi, grounded in our
curated Q&A dataset, with citations back to the original answers.

Team: Jaspreet (Product & PM) · Avneet (RAG) · Bhajneek (future features) · Manveer (UI) — see [TEAM.md](TEAM.md).

**New teammate? Start here:** [docs/ONBOARDING_PROMPT.md](docs/ONBOARDING_PROMPT.md)

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

Then check out your own branch: `git checkout <yourname>/<role>` (see TEAM.md).

## Community features (decision 006)

From SikhNet's feedback, all anonymous and moderated:

- **Rate answers:** 👍/👎 on every answer, source and reply; the best rise to the top, with tags like "Highly rated · 92% helpful".
- **Popular:** trending topics, most-asked questions and most-discussed archive threads on the landing page.
- **Age groups:** "Who's asking? Kid / Teen / Adult" filters what's shown and gently gates grown-up questions for kids.
- **Moderation:** bot checks, hate/spam filters, Claude review, reports, and a moderator queue at `/moderate.html`
  (set `SIKHNET_ADMIN_TOKEN` to use it from another computer). Crisis messages get help lines, never an AI answer.
- **Community board:** `/community.html`, where people post questions, reply, vote and report.

Community data lives in `data/community/community.db` (gitignored, never commit it).

## Working with Claude Code

Open this folder in Claude Code. At session start a hook runs
`scripts/team-context.sh`, which shows what each teammate is doing (read from
their own branch, even before it's merged). Project skills live in
`.claude/skills/` — see [CLAUDE.md](CLAUDE.md). The shared team memory is
`docs/brain/` (status, decisions, friction log).

## GitHub MCP (lets Claude see branches, PRs and issues)

`.mcp.json` adds the GitHub MCP server for everyone. Each person uses their own token:

1. Create a classic token at https://github.com/settings/tokens/new with the `repo` scope.
2. Add it to your shell, then restart Claude Code / the desktop app:
   ```bash
   echo 'export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_yourtoken' >> ~/.zshrc && source ~/.zshrc
   ```
3. Approve the `github` server when Claude Code asks; check it with `/mcp`.

Without it, `scripts/team-context.sh` still tracks branches via plain `git fetch`.

## Layout

```
ingest/        raw export → data/processed/qa.jsonl         (Avneet)  · ingest/sources/ (Bhajneek)
backend/       retrieval, prompts, llm, app — the RAG engine (Avneet)  · backend/features/ (Bhajneek)
frontend/      chat UI, served at /                          (Manveer)
evals/         acceptance questions (Jaspreet) + runner (Avneet)
docs/          REQUIREMENTS.md (judge criteria) · ARCHITECTURE.md (contracts) · brain/ (status, decisions, friction)
.claude/       shared skills + session-start hook
```
