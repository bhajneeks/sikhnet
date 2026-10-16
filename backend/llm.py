"""Claude call for grounded answers. Owner: Avneet, RAG lane."""
from __future__ import annotations

import os
import re

import anthropic

from backend.prompts import SYSTEM_PROMPT, build_user_message

MODEL = os.environ.get("SIKHNET_MODEL", "claude-opus-5-5")
_client = None


def llm_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def answer(question: str, hits: list[dict], history: list[dict] | None = None) -> tuple[str, str]:
    """Returns (answer_markdown, coverage)."""
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (history or [])[-10:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    messages.append({"role": "user", "content": build_user_message(question, hits)})

    # Server-side fallback: if a safety classifier declines, the API retries on a fallback model.
    response = _get_client().beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        cache_control={"type": "ephemeral"},
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=messages,
    )
    if response.stop_reason == "refusal":
        return ("I'm not able to answer that one. Please try rephrasing your question.", "not_found")

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    coverage = "grounded"
    m = re.search(r"COVERAGE:\s*(grounded|partial|not_found)\s*$", text)
    if m:
        coverage = m.group(1)
        text = text[: m.start()].rstrip()
    return text, coverage
