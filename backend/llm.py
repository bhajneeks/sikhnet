"""Claude call for grounded answers. Owner: Avneet, RAG lane.

Returns answer, coverage, perspectives (R4) and follow_ups (R2) in one call via
structured outputs, so nothing has to be scraped out of prose.
"""
from __future__ import annotations

import json
import os

import anthropic

from backend.prompts import ANSWER_SCHEMA, SYSTEM_PROMPT, build_user_message

MODEL = os.environ.get("SIKHNET_MODEL", "claude-opus-5")
MAX_TOKENS = 16000
# Citation discipline, judging whether entries genuinely disagree, and calling
# coverage honestly are the whole job here, so this is not low-effort work.
# Dial down with SIKHNET_EFFORT=medium if demo latency becomes the problem.
EFFORT = os.environ.get("SIKHNET_EFFORT", "high")
_client = None

REFUSAL_TEXT = "I'm not able to answer that one. Please try rephrasing your question."


def llm_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _normalize(data: dict, n_hits: int) -> dict:
    """Trust the schema for shape, not the model for counts or citation numbers."""
    coverage = data.get("coverage") or "grounded"

    follow_ups = [str(q).strip() for q in (data.get("follow_ups") or []) if str(q).strip()][:3]
    if coverage == "not_found":
        follow_ups = []

    perspectives = []
    for p in data.get("perspectives") or []:
        text = str(p.get("text") or "").strip()
        if not text:
            continue
        # Drop citation numbers that don't point at an entry we actually sent.
        ns = [int(n) for n in (p.get("citation_ns") or []) if isinstance(n, int) and 1 <= n <= n_hits]
        perspectives.append({
            "label": str(p.get("label") or "Another view").strip(),
            "text": text,
            "citation_ns": ns,
        })

    return {
        "answer": str(data.get("answer") or "").strip(),
        "coverage": coverage,
        "perspectives": perspectives,
        "follow_ups": follow_ups,
    }


def answer(question: str, hits: list[dict], history: list[dict] | None = None) -> dict:
    """Returns {answer, coverage, perspectives, follow_ups}."""
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (history or [])[-10:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    messages.append({"role": "user", "content": build_user_message(question, hits)})

    # Server-side fallback: if a safety classifier declines, the API retries on a
    # fallback model inside the same call. Religious questions can brush against
    # classifiers, and a refusal mid-demo is worse than a slower answer.
    response = _get_client().beta.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        cache_control={"type": "ephemeral"},
        output_config={
            "effort": EFFORT,
            "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
        },
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=messages,
    )

    if response.stop_reason == "refusal":
        return {"answer": REFUSAL_TEXT, "coverage": "not_found", "perspectives": [], "follow_ups": []}

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # The schema makes this near-impossible, but a demo shouldn't 500 over it.
        return {"answer": text, "coverage": "partial", "perspectives": [], "follow_ups": []}

    return _normalize(data, len(hits))
