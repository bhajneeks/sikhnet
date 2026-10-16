---
id: 001
title: Initial stack, lanes, and branch-per-person workflow
date: 2026-10-16
decided_by: Manveer (proposal — confirm with team in first 15 min)
affects: [data, backend, frontend, evals]
status: active
source: initial repo setup
---

**Decision:** Python 3.9+/FastAPI backend, static HTML/JS frontend served by the
backend, Claude (`claude-opus-5-5`) via the `anthropic` SDK, in-memory keyword
retrieval for v1. Four lanes (see TEAM.md), one long-lived branch per person,
small PRs into `main`.

**Why:** zero infra, one `pip install`, everyone can run the whole app locally
from minute one; contracts in docs/ARCHITECTURE.md let lanes evolve separately.

**Impact on other lanes:** none yet — this is the baseline.
