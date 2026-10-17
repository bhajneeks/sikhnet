"""Claude call for grounded answers. Owner: Avneet, RAG lane.

Returns answer, coverage, perspectives (R4) and follow_ups (R2) in one call via
structured outputs, so nothing has to be scraped out of prose.
"""
from __future__ import annotations

import json
import os
import re

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


def _history_messages(history: list[dict] | None) -> list[dict]:
    """Contract: history is optional and at most ~10 turns are used."""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in (history or [])[-10:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]


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
    messages = _history_messages(history)
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



class _AnswerTextParser:
    r"""Pull the `answer` string out of a JSON object while it is still streaming.

    Structured outputs mean the model emits JSON, so the raw token stream looks
    like `{"answer":"Sikhs wear…`. Streaming that straight to the browser would
    show the user JSON syntax. `answer` is the first property in ANSWER_SCHEMA,
    so its characters arrive before anything else and can be surfaced as prose
    while coverage, perspectives and follow_ups are still being generated.

    Decoding goes through json.loads on the partial string literal, so escapes
    (\n, \", \uXXXX) come out right and a chunk that splits an escape
    sequence is held back until it completes rather than emitting mojibake.
    """

    def __init__(self) -> None:
        self._buf = ""          # everything seen so far
        self._raw = ""          # characters inside the answer string literal
        self._emitted = 0       # decoded characters already handed out
        self._started = False
        self._finished = False

    def feed(self, chunk: str) -> str:
        """Return the newly available decoded prose (may be empty)."""
        if self._finished:
            return ""
        self._buf += chunk

        if not self._started:
            marker = re.search(r'"answer"\s*:\s*"', self._buf)
            if not marker:
                return ""
            self._started = True
            self._raw = self._buf[marker.end():]
        else:
            self._raw += chunk

        # Find the closing quote that isn't escaped.
        end = None
        i = 0
        while i < len(self._raw):
            c = self._raw[i]
            if c == "\\":
                i += 2
                continue
            if c == '"':
                end = i
                break
            i += 1
        if end is not None:
            self._raw = self._raw[:end]
            self._finished = True

        return self._take()

    def _take(self) -> str:
        """Decode as much of the literal as is currently decodable."""
        literal = self._raw
        for trim in range(0, 7):           # back off past a split \uXXXX
            candidate = literal[: len(literal) - trim] if trim else literal
            try:
                decoded = json.loads('"' + candidate + '"')
            except json.JSONDecodeError:
                continue
            # A chunk can land between the halves of a surrogate pair (emoji).
            # json.loads decodes a lone high surrogate without complaint, which
            # would put a broken character on the wire, so hold it back until
            # its partner arrives.
            if decoded and "\ud800" <= decoded[-1] <= "\udbff":
                decoded = decoded[:-1]
            if len(decoded) <= self._emitted:
                return ""
            out = decoded[self._emitted:]
            self._emitted = len(decoded)
            return out
        return ""


def answer_stream(question: str, hits: list[dict], history: list[dict] | None = None):
    """Same call as answer(), yielding ("delta", prose) then ("final", result).

    One request, not two: the prose is surfaced as it arrives and the structured
    fields are parsed from the same completed JSON.
    """
    messages = _history_messages(history)
    messages.append({"role": "user", "content": build_user_message(question, hits)})

    parser = _AnswerTextParser()
    with _get_client().beta.messages.stream(
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
    ) as stream:
        for chunk in stream.text_stream:
            piece = parser.feed(chunk)
            if piece:
                yield ("delta", piece)
        final = stream.get_final_message()

    if final.stop_reason == "refusal":
        yield ("final", {"answer": REFUSAL_TEXT, "coverage": "not_found",
                         "perspectives": [], "follow_ups": []})
        return

    text = "".join(b.text for b in final.content if b.type == "text").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        yield ("final", {"answer": text, "coverage": "partial",
                         "perspectives": [], "follow_ups": []})
        return
    yield ("final", _normalize(data, len(hits)))
