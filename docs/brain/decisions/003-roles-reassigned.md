---
id: 003
title: Roles reassigned — Jaspreet PM, Avneet RAG, Bhajneek future features, Manveer UI
date: 2026-10-16
decided_by: Manveer (for the team)
affects: [all]
status: active
source: Manveer in chat, 2026-10-16; supersedes the lane split in 001
---

**Decision:** Jaspreet = Product & PM (client expectations, priorities, acceptance;
route product questions to him). Avneet = RAG engine (ingest, retrieval, prompts,
LLM, /api/ask). Bhajneek = future features (R3 multi-source, R5 Surprise me,
backend/features/). Manveer = UI/UX (frontend/, designed with Claude Design).
Branches renamed to jaspreet/product, avneet/rag, bhajneek/features, manveer/ui.

**Why:** plays to each person's strengths; Jaspreet understands the client best.

**Impact:** R5 helpers moved from retrieval.py to backend/features/surprise.py
(Bhajneek), mounted in app.py via include_router. Old branches deleted (they had no work).
