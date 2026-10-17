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
- LLM: Claude via the official `anthropic` SDK, model `claude-opus-5`.
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
- `category` (R5): one of `theology | history | music | literature | art | practice | other`.
  Optional: if missing, `backend/features/surprise.py` infers topics from keywords
  in the question, tags and answer (a record can belong to several).
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
- `GET /api/categories` (R5) → `{"categories": ["theology", "history", …], "labels": {"art": "Art & Architecture", …}}`.
  Only topics with at least one record are listed.
- `GET /api/surprise?category=history` (R5) → `{"question": "…", "category": "history", "id": "qa_…", "seed_question": "…"}`.
  `category` is a topic key/label **or any free-text subject** (e.g. `kirtan`), or omitted for any topic.
  `question` is a rabbit-hole hook grounded in entry `id` (= `seed_question` without an API key);
  no repeats until a topic's pool is exhausted; primary entries preferred; `question: null` if nothing matches.
  Frontend then sends that question to `/api/ask`.
- `POST /api/ask/stream` (R1/R2/R4) — same request body, Server-Sent Events.
  Order is `citations` → `delta`* → `meta` → `done` (or `error`).
  `citations` arrives before the first token (it comes from retrieval, not the
  model); each `delta` is `{text}` and concatenating them gives exactly the
  `answer` of `POST /api/ask`; `meta` carries `{coverage, perspectives,
  follow_ups, citations, mode}` and its `citations` is authoritative — empty on
  `not_found`. `POST /api/ask` is unchanged. See decision 005.

## 3b. Community contract — `backend/features/community.py` (owner: Bhajneek, decision 006)

SikhNet's feedback: answer ratings, popular topics, age groups, moderation, and a
bulletin board. Storage is SQLite at `data/community/community.db` (gitignored;
override with `SIKHNET_DB`). Anonymous: the browser sends a random `voter` id
(8-64 chars `[A-Za-z0-9_-]`); IPs are stored only as salted hashes.
**Board content is never passed to the answering model.**

Ages: `audience` = `kids | teens | adults` (omit = no filter). Content `age_rating` =
`all | teen | adult` from keyword rules; a list only shows items the audience allows.

| Endpoint | Body / query | Returns |
|---|---|---|
| `POST /api/check` | `{text, audience?}` | `{crisis, help, age_rating, allowed}`; UI calls it before `/api/ask*`. Crisis → show `help`, never call the model. |
| `POST /api/vote` | `{target, value: 1\|-1\|0, voter, reason?}`, target = `answer:<hash>` \| `source:<record id>` \| `post:<id>` | `{up, down, score, mine, tag}`. `score` = Wilson lower bound; `tag` = `{kind: good\|mixed\|low, label}` after 3+ votes |
| `GET /api/ratings` | `?targets=a,b&voter=` | `{ratings: {target: {...}}}` |
| `POST /api/track` | `{question, voter, audience?}` | counts a question for "most asked" (crisis text never stored) |
| `GET /api/popular` | `?audience=` | `{topics, topics_source, asked, discussed, board}` |
| `GET /api/board` | `?sort=top\|new\|unanswered&topic=&audience=&q=&voter=` | `{threads, total, topics}` |
| `GET /api/board/{id}` | `?audience=&voter=` | `{thread, replies (verified, then score), related (archive questions)}` |
| `POST /api/board` | `{title, body?, topic?, audience?, author?, voter, elapsed_ms, website}` | `{ok, id, status: visible\|review, message, help?}` or `{ok: false, status: "blocked", message}` |
| `POST /api/board/{id}/reply` | `{body, author?, voter, elapsed_ms, website}` | same as above |
| `POST /api/report` | `{target, voter, reason?}` | 3 reports → post hidden for review |
| `GET /api/mod/queue`, `POST /api/mod/post/{id}` `{action: approve\|hide\|delete\|verify\|unverify}` | header `X-Admin-Token` = `SIKHNET_ADMIN_TOKEN` (unset → localhost only) | moderator queue, low-rated answers, log |

`GET /api/surprise` also takes `?audience=` and returns `age_rating`; well-rated
archive answers are picked more often.

## 4. Eval contract — `evals/` (acceptance questions: Jaspreet · runner: Avneet)

- `evals/questions.jsonl`: `{"question": "...", "expected_ids": ["qa_..."], "should_cover": true}`.
- `python3 evals/run_evals.py [--base-url http://localhost:8000]` prints
  per-question results and totals: retrieval hit@5, citation rate,
  correct "not_found" on out-of-scope questions, plus the per-requirement
  checks listed in `docs/REQUIREMENTS.md`. Appends a summary to
  `evals/results.md`.
- No prompt/retrieval change merges if it lowers these scores (see
  `grounded-answer` skill).
