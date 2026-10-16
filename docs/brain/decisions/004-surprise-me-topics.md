---
id: 004
title: Surprise me — curated topics (incl. art), inferred from text, free-text topics, grounded hooks
date: 2026-10-16
decided_by: Bhajneek
affects: [features, frontend, rag, product]
status: active
source: Bhajneek in chat ("make it based on the requirements… literature, art, music, or any other subject"); docs/REQUIREMENTS.md R5
---

**Decision:** `/api/surprise` uses a fixed topic list — theology, history, music,
literature, art, practice — and infers each record's topics from keywords when
the dataset has no `category`. `category` also accepts any free-text subject
(searched via `search()`). The returned `question` is a short hook Claude writes
from that one entry only (falls back to the dataset question without a key).
No repeats per topic until its pool is exhausted; primary entries preferred.
Additive response fields: `labels` on `/api/categories`, `seed_question` on `/api/surprise`.
`art` added to the `category` values in the data contract.

**Why:** R5 asks for a topic dropdown that gives a fun rabbit-hole prompt from
our dataset. The real dataset has no category column, so tagging by hand isn't
feasible in the time we have.

**Impact on other lanes:**
- Manveer: optional — show `labels[c]` in the dropdown instead of the raw key; optionally a
  "type your own topic" input that sends free text as `category`.
- Avneet: none required. If ingest sets `category`, it overrides inference.
- Jaspreet: eval "surprise works for every category" can loop over `/api/categories`.

**Update (v3, same day):** with the real dataset (one record per answer, every
record has a forum `category`), Surprise me now picks per *thread*, unions the forum
category with keyword-inferred topics, skips weak seeds (short questions, thin
answers), weights rich threads, keeps a Claude hook only if `search()` finds the
same thread again, uses the team's verified `llm.MODEL`, and prefetches the next
pick per topic. API shape unchanged; `id` is the thread's first answer record.
