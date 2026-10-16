"""FastAPI app: /api/ask + serves the frontend. Owner: backend lane.

Run: uvicorn backend.app:app --reload --port 8000
Contract: docs/ARCHITECTURE.md § 3.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend import llm, retrieval  # noqa: E402

app = FastAPI(title="sikhnet")
MIN_SCORE = 1.0  # below this, treat retrieval as a miss in fallback mode


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
            "source_url": h.get("source_url"),
        }
        for n, h in enumerate(hits, 1)
    ]


@app.get("/api/health")
def health():
    return {"ok": True, "records": retrieval.records_count(), "data": retrieval.data_path(), "llm": llm.llm_enabled()}


@app.post("/api/ask")
def ask(req: AskRequest):
    hits = retrieval.search(req.question, k=5)
    if llm.llm_enabled():
        text, coverage = llm.answer(req.question, hits, [t.model_dump() for t in req.history])
        return {"answer": text, "citations": _citations(hits), "coverage": coverage, "mode": "llm"}

    # Fallback mode (no API key): return the best-matching entry verbatim.
    if not hits or hits[0]["score"] < MIN_SCORE:
        return {"answer": "I couldn't find this in our question bank yet. Try rephrasing?",
                "citations": [], "coverage": "not_found", "mode": "fallback"}
    top = hits[0]
    return {"answer": f"**{top['question']}**\n\n{top['answer']} [1]",
            "citations": _citations([top]), "coverage": "grounded", "mode": "fallback"}


app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "frontend", html=True), name="frontend")
