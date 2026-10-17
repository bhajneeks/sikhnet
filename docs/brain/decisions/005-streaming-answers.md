---
id: 005
title: Stream answers over SSE — POST /api/ask/stream
date: 2026-10-16
decided_by: Avneet
affects: [rag, frontend, product]
status: active
source: Avneet in chat ("same thing as gpt and claude ... it streams the bytes, not all at once"); docs/ARCHITECTURE.md § 3 already reserved the endpoint
---

**Decision:** `POST /api/ask/stream` returns Server-Sent Events. `POST /api/ask`
is unchanged, so nothing that already works breaks.

Event order is always `citations` → `delta`* → `meta` → `done`, or `error`.

| Event | Payload | When |
|---|---|---|
| `citations` | `{citations: [...], mode}` | Immediately — before the model has produced a token |
| `delta` | `{text}` | Each fragment of the answer prose, in order |
| `meta` | `{coverage, perspectives, follow_ups, citations, mode}` | Once, after the prose |
| `done` | `{}` | Last |
| `error` | `{message}` | Instead of `done` if the stream breaks |

**Why citations come first:** they are built from retrieval, not from the model,
so they are known the moment `search()` returns. The source cards can render
while the answer is still being written — measured at 0.01s versus 17.0s for the
complete response.

**Why `meta` repeats `citations`:** a `not_found` answer must cite nothing, and
that is only known once the model has judged coverage. The `meta` list is
authoritative — on `not_found` it is empty and the client should drop the cards
it rendered from the earlier event.

**Concatenating every `delta` gives exactly the `answer` string that
`/api/ask` returns** — verified byte-identical. Structured outputs mean the model
emits JSON, so the deltas are extracted from the `answer` field as it streams
(`backend/llm.py::_AnswerTextParser`); the client never sees JSON syntax.

**Impact on other lanes:**
- Manveer: switch the chat call to `/api/ask/stream` and append `delta.text` as
  it arrives; render source cards on `citations`, then follow-up chips and
  perspectives on `meta`, replacing citations with `meta.citations`. `/api/ask`
  still works unchanged if you'd rather not.
- Bhajneek: no change. `/api/surprise` still returns a question the client sends
  to either endpoint.
- Jaspreet: expect a visible pause before the first word in llm mode — ~6.8s at
  `SIKHNET_EFFORT=high`, which is the model thinking, not latency. A "thinking"
  indicator covers it; `SIKHNET_EFFORT=medium` shortens it at some quality cost.
- Fallback mode streams too, in word groups, so the UI path is identical with or
  without an API key.
