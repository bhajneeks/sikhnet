"""FastAPI app: /api/ask + serves the frontend. Owner: Avneet, RAG lane.

Run: uvicorn backend.app:app --reload --port 8000
Contract: docs/ARCHITECTURE.md § 3.
"""
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend import llm, retrieval  # noqa: E402
from backend.features import router as features_router  # noqa: E402

app = FastAPI(title="sikhnet")
app.include_router(features_router)  # Bhajneek's feature endpoints

# Coverage gate for fallback mode. BM25 scores are not comparable across
# queries — measured on the real dataset, out-of-scope questions reached 11.5
# while in-scope went as low as 2.9, so a score threshold alone cannot separate
# them. Unseen vocabulary can: across 18 in-scope questions every word was one
# the dataset uses, while 8 of 10 out-of-scope questions had at least one word
# it has never used. Tuned for no false "not_found" on real questions — in llm
# mode the model judges coverage itself, having read the entries.
MIN_SCORE = 1.0
MIN_TERM_OVERLAP = 0.5
# How many of the top hit's sibling answers to pull in for perspectives (R4).
MAX_THREAD_SIBLINGS = 3
NOT_FOUND_TEXT = "I couldn't find this in our question bank yet. Try rephrasing?"


class Turn(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    history: list[Turn] = []


def _citations(hits: list[dict]) -> list[dict]:
    return [
        {
            "n": n,
            "id": h["id"],
            "question": h["question"],
            "answer_excerpt": h["answer"][:300] + ("…" if len(h["answer"]) > 300 else ""),
            "source": h.get("source", "sikhnet-qa-dataset"),
            "source_type": h.get("source_type", "primary"),
            "source_url": h.get("source_url"),
        }
        for n, h in enumerate(hits, 1)
    ]


def _term_overlap(question: str, hit: dict) -> float:
    """Fraction of the question's content words the entry actually contains."""
    terms = set(retrieval.tokenize(question))
    if not terms:
        return 0.0
    body = (hit.get("extra") or {}).get("question_body") or ""
    text = set(retrieval.tokenize(f"{hit['question']} {body} {hit['answer']}"))
    return len(terms & text) / len(terms)


def _covered(question: str, hits: list[dict]) -> bool:
    if not hits or hits[0]["score"] < MIN_SCORE:
        return False
    if retrieval.unseen_terms(question):
        return False
    return _term_overlap(question, hits[0]) >= MIN_TERM_OVERLAP


def _with_thread_siblings(hits: list[dict]) -> tuple[list[dict], int]:
    """Append the top hit's other answers. Returns (references, first_sibling_n).

    search() spreads top-k across threads so citations aren't five slices of one
    discussion; perspectives need the opposite, so the siblings are added back
    here, after the retrieved hits, keeping citation numbers stable.
    """
    if not hits:
        return [], 0
    thread = (hits[0].get("extra") or {}).get("thread_id")
    if not thread:
        return hits, 0
    siblings = retrieval.thread_answers(
        thread, exclude_ids={h["id"] for h in hits}, limit=MAX_THREAD_SIBLINGS
    )
    if not siblings:
        return hits, 0
    return hits + siblings, len(hits) + 1


def _fallback_follow_ups(hits: list[dict]) -> list[str]:
    """R2 without a model: the other retrieved entries are questions our dataset
    can answer by construction, which is what the grounded-answer contract asks for."""
    out, seen = [], {hits[0]["question"].strip().lower()} if hits else set()
    for h in hits[1:]:
        q = h["question"].strip()
        key = q.lower()
        if q and key not in seen:
            seen.add(key)
            out.append(q if q.endswith("?") else f"{q}?")
        if len(out) == 3:
            break
    return out


def _fallback_perspectives(refs: list[dict], first_sibling_n: int) -> list[dict]:
    """R4 without a model: the other answers to the same question are, literally,
    the other views on it. Quoted verbatim — nothing is paraphrased or invented."""
    if not first_sibling_n:
        return []
    views = []
    for n, h in enumerate(refs[first_sibling_n - 1:], start=first_sibling_n):
        excerpt = h["answer"][:400] + ("…" if len(h["answer"]) > 400 else "")
        views.append({
            "label": "Another answer in the same discussion",
            "text": f"{excerpt} [{n}]",
            "citation_ns": [n],
        })
    return views


@app.get("/api/health")
def health():
    return {"ok": True, "records": retrieval.records_count(), "data": retrieval.data_path(), "llm": llm.llm_enabled()}


@app.post("/api/ask")
def ask(req: AskRequest):
    hits = retrieval.search(req.question, k=5)
    refs, first_sibling_n = _with_thread_siblings(hits)

    if llm.llm_enabled():
        result = llm.answer(req.question, refs, [t.model_dump() for t in req.history])
        cited = [] if result["coverage"] == "not_found" else _citations(refs)
        return {
            "answer": result["answer"],
            "citations": cited,
            "perspectives": result["perspectives"],
            "follow_ups": result["follow_ups"],
            "coverage": result["coverage"],
            "mode": "llm",
        }

    # Fallback mode (no API key): the top entry verbatim, with follow-ups and
    # perspectives derived from retrieval so the UI is exercised in both modes.
    if not _covered(req.question, hits):
        return {"answer": NOT_FOUND_TEXT,
                "citations": [], "perspectives": [], "follow_ups": [],
                "coverage": "not_found", "mode": "fallback"}

    top = hits[0]
    return {
        "answer": f"**{top['question']}**\n\n{top['answer']} [1]",
        "citations": _citations(refs),
        "perspectives": _fallback_perspectives(refs, first_sibling_n),
        "follow_ups": _fallback_follow_ups(hits),
        "coverage": "grounded",
        "mode": "fallback",
    }


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunk_words(text: str, size: int = 6):
    """Fallback mode has the whole answer already; hand it over in word groups
    so the UI's streaming path is exercised identically in both modes."""
    words = text.split(" ")
    for i in range(0, len(words), size):
        yield (" " if i else "") + " ".join(words[i:i + size])


def _ask_events(req: AskRequest):
    """SSE for POST /api/ask/stream (docs/ARCHITECTURE.md § 3).

    citations are known the moment retrieval returns — they come from the
    dataset, not the model — so they go out before the first token and the
    source cards can render while the answer is still being written.
    """
    try:
        hits = retrieval.search(req.question, k=5)
        refs, first_sibling_n = _with_thread_siblings(hits)

        if llm.llm_enabled():
            yield _sse("citations", {"citations": _citations(refs), "mode": "llm"})
            result = None
            for kind, value in llm.answer_stream(
                req.question, refs, [t.model_dump() for t in req.history]
            ):
                if kind == "delta":
                    yield _sse("delta", {"text": value})
                else:
                    result = value
            result = result or {"answer": "", "coverage": "not_found",
                                "perspectives": [], "follow_ups": []}
            not_found = result["coverage"] == "not_found"
            yield _sse("meta", {
                "coverage": result["coverage"],
                "perspectives": result["perspectives"],
                "follow_ups": result["follow_ups"],
                # A not_found answer cites nothing, so retract the cards we sent.
                "citations": [] if not_found else _citations(refs),
                "mode": "llm",
            })
            yield _sse("done", {})
            return

        # Fallback mode (no API key).
        if not _covered(req.question, hits):
            yield _sse("citations", {"citations": [], "mode": "fallback"})
            for piece in _chunk_words(NOT_FOUND_TEXT):
                yield _sse("delta", {"text": piece})
            yield _sse("meta", {"coverage": "not_found", "perspectives": [],
                                "follow_ups": [], "citations": [], "mode": "fallback"})
            yield _sse("done", {})
            return

        top = hits[0]
        yield _sse("citations", {"citations": _citations(refs), "mode": "fallback"})
        for piece in _chunk_words(f"**{top['question']}**\n\n{top['answer']} [1]"):
            yield _sse("delta", {"text": piece})
        yield _sse("meta", {
            "coverage": "grounded",
            "perspectives": _fallback_perspectives(refs, first_sibling_n),
            "follow_ups": _fallback_follow_ups(hits),
            "citations": _citations(refs),
            "mode": "fallback",
        })
        yield _sse("done", {})
    except Exception as exc:  # a dropped stream must not look like a finished answer
        yield _sse("error", {"message": str(exc)[:200]})


@app.post("/api/ask/stream")
def ask_stream(req: AskRequest):
    return StreamingResponse(
        _ask_events(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"},   # stop proxies buffering the stream
    )


app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "frontend", html=True), name="frontend")
