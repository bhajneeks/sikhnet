---
id: 007
title: Deploy on Railway (one service + volume), not Vercel
date: 2026-10-17
decided_by: Bhajneek (captain)
affects: [product, rag, features, frontend]
status: active
source: Bhajneek in chat ("we can do railway"), after comparing Vercel vs Railway
---

**Decision:** Deploy the existing FastAPI app on Railway as one service with a
persistent volume at `/data`. `railway.json` + `scripts/start.sh` start it; the
dataset is fetched once from a private URL into the volume and ingested
(never through git). Setup steps: docs/DEPLOY.md.

**Why:** Vercel's serverless functions have no persistent disk (community SQLite
would lose posts), freeze background threads (AI moderation, Surprise-me prefetch)
and would need the dataset at build time. Railway runs the app unchanged.

**Impact on other lanes:**
- Jaspreet: owns the demo; please confirm with SikhNet that hosting the dataset on
  Railway for the demo is OK, and put "delete the Railway volume within 30 days"
  on the wrap-up list.
- Avneet: none. `SIKHNET_DATA` / `SIKHNET_DB` now point into the volume on Railway.
- Manveer: none.
- Everyone: `main` auto-deploys, so keep it working.
