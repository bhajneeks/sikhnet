# Architecture & contracts

These contracts are how 4 people build separately and still connect. Change one
only through the `capture-decision` skill, and tell the affected owners.

## Overview

Retrieval-augmented chat: retrieve the most relevant Q&A pairs from our
dataset, give them to Claude with strict grounding rules, return an answer plus
citations to the original entries.

- Language: Python 3.9+ (FastAPI) for ingest, retrieval, API, evals.
- Frontend: static HTML/CSS/JS in `frontend/`, served by the backend at `/`
  (no build step). Manveer may switch to React/Next if wanted — the API contract
  stays the same.
- LLM: Claude via the official `anthropic` SDK, model `claude-opus-5-5`.
- Retrieval v1: in-memory BM25-style keyword search (no extra services).
  v2 (optional): embeddings.

## 1. Data contract — `data/processed/qa.jsonl` (owner: Avneet; secondary sources: Bhajneek)

One JSON object per line, UTF-8:

```json
{
  "id": "qa_3f9a1c2b7d",
  "question": "What is the significance of Vaisakhi?",
  "answer": "…full answer text as in the dataset…",
  "source": "sikhnet-qa-dataset",
  "source_type": "primary",
  "source_url": "https://… (optional)",
  "category": "history",
  "tags": ["history", "gurpurab"],
  "extra": {}
}
```

- `id`, `question`, `answer`, `source` are required; others optional.
- `source_type` (R3): `"primary"` = the org's own Q&A dataset (weighted most);
  `"secondary"` = other properties (e.g. SikhiWiki, other org sites). Missing → `"primary"`.
- `category` (R5): one of `theology | history | music | literature | practice | other`.
  Missing → `"other"`. Used by "Surprise me". Map dataset columns/tags to it in ingest.
- `id` is stable across re-ingestion: `"qa_" + sha1(normalized question + source)[:10]`.
- Unknown dataset columns go in `extra` (never dropped silently).

## 2. Retrieval contract — `backend/retrieval.py` (owner: Avneet)

```python
def search(query: str, k: int = 5) -> list[dict]:
    """Return up to k records from qa.jsonl, best first.
    Each record is the qa.jsonl object plus "score": float (higher = better).
    When relevance is close, primary sources rank above secondary (R3)."""

def all_records() -> list[dict]:
    """Every loaded record (used by backend/features)."""
```

R5 helpers live in `backend/features/surprise.py` (owner: Bhajneek):
`categories() -> list[str]` and `random_question(category=None) -> dict | None`.

Backend calls only `search()`. Internals (BM25, embeddings, hybrid) are
Avneet's to change freely.

## 3. API contract — `POST /api/ask` (owner: Avneet; `/api/categories` + `/api/surprise`: Bhajneek)

Request:

```json
{
  "question": "Why do Sikhs wear a turban?",
  "history": [{"role": "user", "content": "…"}, {"role": "assistant", "content": "…"}]
}
```

Response:

```json
{
  "answer": "markdown text, citations inline like [1], [2]",
  "citations": [
    {"n": 1, "id": "qa_3f9a1c2b7d", "question": "…", "answer_excerpt": "first ~300 chars",
     "source": "sikhnet-qa-dataset", "source_type": "primary", "source_url": null}
  ],
  "perspectives": [
    {"label": "Another interpretation", "text": "… [3]", "citation_ns": [3]}
  ],
  "follow_ups": ["What is the history of langar?", "…", "…"],
  "coverage": "grounded | partial | not_found",
  "mode": "llm | fallback"
}
```

- `answer` (R1, R4) is the org's position, from primary sources first.
- `perspectives` (R4): alternative views **only if the retrieved sources contain
  them**; otherwise `[]`. Secondary-source material (R3) goes here too, under
  label "From other sources". Never invented.
- `follow_ups` (R2): exactly 3 short questions the user might ask next, preferring
  ones our dataset can answer. Always present (may be `[]` only on `not_found`).

- `history` is optional; max ~10 turns are used.
- `mode: "fallback"` = no API key configured; the answer is the top retrieved
  entry verbatim. The frontend must work in both modes.
- `GET /api/health` → `{"ok": true, "records": <int>, "llm": <bool>}`.
- `GET /api/categories` (R5) → `{"categories": ["theology", "history", …]}`.
- `GET /api/surprise?category=history` (R5) → `{"question": "…", "category": "history", "id": "qa_…"}`.
  Frontend then sends that question to `/api/ask`.
- Streaming (`POST /api/ask/stream`, SSE) may be added later — additive only.

## 4. Eval contract — `evals/` (acceptance questions: Jaspreet · runner: Avneet)

- `evals/questions.jsonl`: `{"question": "...", "expected_ids": ["qa_..."], "should_cover": true}`.
- `python3 evals/run_evals.py [--base-url http://localhost:8000]` prints
  per-question results and totals: retrieval hit@5, citation rate,
  correct "not_found" on out-of-scope questions, plus the per-requirement
  checks listed in `docs/REQUIREMENTS.md`. Appends a summary to
  `evals/results.md`.
- No prompt/retrieval change merges if it lowers these scores (see
  `grounded-answer` skill).
