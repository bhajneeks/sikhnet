# Architecture & contracts

These contracts are how 4 people build separately and still connect. Change one
only through the `capture-decision` skill, and tell the affected owners.

## Overview

Retrieval-augmented chat: retrieve the most relevant Q&A pairs from our
dataset, give them to Claude with strict grounding rules, return an answer plus
citations to the original entries.

- Language: Python 3.9+ (FastAPI) for ingest, retrieval, API, evals.
- Frontend: static HTML/CSS/JS in `frontend/`, served by the backend at `/`
  (no build step). Avneet may switch to React/Next if wanted — the API contract
  stays the same.
- LLM: Claude via the official `anthropic` SDK, model `claude-opus-5-5`.
- Retrieval v1: in-memory BM25-style keyword search (no extra services).
  v2 (optional): embeddings.

## 1. Data contract — `data/processed/qa.jsonl` (owner: Bhajneek)

One JSON object per line, UTF-8:

```json
{
  "id": "qa_3f9a1c2b7d",
  "question": "What is the significance of Vaisakhi?",
  "answer": "…full answer text as in the dataset…",
  "source": "sikhnet-qa-dataset",
  "source_url": "https://… (optional)",
  "tags": ["history", "gurpurab"],
  "extra": {}
}
```

- `id`, `question`, `answer`, `source` are required; others optional.
- `id` is stable across re-ingestion: `"qa_" + sha1(normalized question + source)[:10]`.
- Unknown dataset columns go in `extra` (never dropped silently).

## 2. Retrieval contract — `backend/retrieval.py` (owner: Bhajneek)

```python
def search(query: str, k: int = 5) -> list[dict]:
    """Return up to k records from qa.jsonl, best first.
    Each record is the qa.jsonl object plus "score": float (higher = better)."""
```

Backend calls only `search()`. Internals (BM25, embeddings, hybrid) are
Bhajneek's to change freely.

## 3. API contract — `POST /api/ask` (owner: Manveer)

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
    {"n": 1, "id": "qa_3f9a1c2b7d", "question": "…", "answer_excerpt": "first ~300 chars", "source_url": null}
  ],
  "coverage": "grounded | partial | not_found",
  "mode": "llm | fallback"
}
```

- `history` is optional; max ~10 turns are used.
- `mode: "fallback"` = no API key configured; the answer is the top retrieved
  entry verbatim. The frontend must work in both modes.
- `GET /api/health` → `{"ok": true, "records": <int>, "llm": <bool>}`.
- Streaming (`POST /api/ask/stream`, SSE) may be added later — additive only.

## 4. Eval contract — `evals/` (owner: Jaspreet)

- `evals/questions.jsonl`: `{"question": "...", "expected_ids": ["qa_..."], "should_cover": true}`.
- `python3 evals/run_evals.py [--base-url http://localhost:8000]` prints
  per-question results and totals: retrieval hit@5, citation rate,
  correct "not_found" on out-of-scope questions. Appends a summary to
  `evals/results.md`.
- No prompt/retrieval change merges if it lowers these scores (see
  `grounded-answer` skill).
