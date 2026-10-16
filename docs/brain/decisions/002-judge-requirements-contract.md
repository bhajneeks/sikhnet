---
id: 002
title: Contracts extended for judge requirements R1-R5
date: 2026-10-16
decided_by: Manveer
affects: [data, backend, frontend, evals]
status: active
source: judge/sponsor brief shared by Manveer; docs/REQUIREMENTS.md
---

**Decision:** Additive contract changes (nothing existing breaks):
- Data: `source_type` (primary|secondary) and `category` fields.
- Retrieval: primary ranks above secondary on near-ties; new `random_question()` and `categories()`.
- API: `perspectives`, `follow_ups`, citation `source`/`source_type`; new `GET /api/categories`, `GET /api/surprise`.

**Why:** the judge scores cited answers, follow-ups, multi-source weighting with the org's answer first,
multifaceted views, and a "Surprise me" topic feature. See docs/REQUIREMENTS.md.

**Impact on other lanes:**
- Bhajneek: ingest writes `source_type` + `category`; implement ranking tie-break, `random_question`, `categories`.
- Manveer: prompt + response fields, two new endpoints.
- Avneet: follow-up chips, "Other perspectives" section, topic dropdown + Surprise me button.
- Jaspreet: per-requirement eval checks.
