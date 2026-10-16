# Paste this into Claude Code (first message of your session)

First, in a terminal:

```bash
git clone https://github.com/bhajneeks/sikhnet.git && cd sikhnet
```

Then open the `sikhnet` folder in Claude Code (desktop Code tab, or `claude` in
the terminal) and paste this, replacing `<MY NAME>`:

---

I'm **<MY NAME>** on the sikhnet hackathon team (Manveer, Bhajneek, Avneet, Jaspreet). We're building a ChatGPT-style assistant that answers questions about Sikhi from our Q&A dataset.

Before doing anything else:
1. Set my git identity for this repo (`git config user.name "<MY NAME>"`) and check out my branch from TEAM.md (`git checkout <my-branch> && git pull origin main`).
2. Read CLAUDE.md, TEAM.md, docs/REQUIREMENTS.md and docs/ARCHITECTURE.md, then run the `team-sync` skill: tell me in a few lines what each teammate is doing, what affects my role, and which judge requirements (R1-R5) are still unbuilt.
3. Give me a short plan for my next 2-3 hours, in my role only, ordered by impact on R1-R5.

Rules for this whole session:
- Every task must serve a judge requirement in docs/REQUIREMENTS.md. If I ask for something that doesn't, say so and suggest the most valuable unfinished one.
- Stay in my lane. Only edit files my role owns in TEAM.md. If something belongs to someone else, draft a short message I can send them instead of editing their files.
- Questions about what the client or judges expect, scope, priority, or how something should behave for users go to **Jaspreet** (Product & PM). Don't guess; draft the question for me to send him.
- Never break the contracts in docs/ARCHITECTURE.md. A contract change goes through the `capture-decision` skill, and you tell me who to notify.
- Bot answers must be grounded in our dataset with citations (`grounded-answer` skill). No invented Gurbani or outside facts.
- Update my status file docs/brain/status/<my-name>.md when I start something new and before I stop, and commit and push to my branch often. Open small PRs into main every few hours, and keep main working.
- Log anything that blocks or confuses me with `friction-log`, so nobody else hits it.

---

## Branches

| Person | Role | Branch |
|---|---|---|
| Jaspreet | Product & PM | `jaspreet/product` |
| Avneet | RAG engine | `avneet/rag` |
| Bhajneek | Future features | `bhajneek/features` |
| Manveer | UI / UX (Claude Design) | `manveer/ui` |

Optional: set up the GitHub MCP (README → "GitHub MCP") so Claude can also see PRs.
