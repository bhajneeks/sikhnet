"""Retrieval over data/processed/qa.jsonl. Owner: Avneet, RAG lane (see TEAM.md).

Contract (docs/ARCHITECTURE.md § 2): search(query, k) -> list of qa records + "score".
v1 is a small in-memory BM25 — swap internals freely, keep the signature.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(os.environ.get("SIKHNET_DATA", "data/processed/qa.jsonl"))
SAMPLE_PATH = Path("data/sample/qa_sample.jsonl")

STOPWORDS = set("""a an and are as at be by do does for from how i in is it of on or
should the to was what when where which who why with you your we our can my me""".split())

# Forum answers quote earlier posts with "> " lines (datasheet: "Quoted replies"),
# which would otherwise count the same words several times in one thread.
QUOTE_LINE = re.compile(r"^\s*>.*$", re.MULTILINE)

# A tie-break, not a thumb on the scale: only reorders results already scoring
# within PRIMARY_MARGIN of each other (contract § 2, R3).
PRIMARY_MARGIN = 0.15


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in STOPWORDS]


def _indexed_text(record: dict) -> list[str]:
    """Questions weighted double: the best match signal for a user's question.

    The display `question` is the thread title; the poster's actual wording lives
    in extra.question_body (see ingest), so both are indexed.
    """
    body = (record.get("extra") or {}).get("question_body") or ""
    answer = QUOTE_LINE.sub("", record["answer"])
    return tokenize(record["question"]) * 2 + tokenize(body) + tokenize(answer)


@lru_cache(maxsize=1)
def _index():
    path = DATA_PATH if DATA_PATH.exists() else SAMPLE_PATH
    records = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    docs = [Counter(_indexed_text(r)) for r in records]
    lengths = [sum(d.values()) for d in docs]
    avg_len = sum(lengths) / max(len(lengths), 1)
    df = Counter(term for d in docs for term in d)
    return path, records, docs, lengths, avg_len, df


def all_records() -> list[dict]:
    return _index()[1]


def records_count() -> int:
    return len(_index()[1])


def data_path() -> str:
    return str(_index()[0])


def unseen_terms(query: str) -> list[str]:
    """Query words the dataset has never used anywhere.

    The strongest out-of-scope signal we have without a model: "brazil",
    "postgresql" and "javascript" appear in no Sikhi answer, while every
    in-scope question we measured used only words the corpus knows.
    """
    *_, df = _index()
    return [t for t in dict.fromkeys(tokenize(query)) if t not in df]


def thread_answers(thread_id: str, exclude_ids: set[str] | None = None, limit: int = 3) -> list[dict]:
    """The other answers posted to the same question, in their original order.

    Fetched explicitly rather than hoped for: search() deliberately spreads
    top-k across threads, so a thread's own disagreement never survives into
    the results — and that disagreement is exactly what R4 needs.
    """
    exclude = exclude_ids or set()
    siblings = [
        r for r in all_records()
        if _thread_of(r) == str(thread_id) and r["id"] not in exclude
    ]
    siblings.sort(key=lambda r: (r.get("extra") or {}).get("answer_position", 0))
    return siblings[:limit]


def _thread_of(record: dict) -> str:
    """Answers to one question share a thread; fall back to the record id."""
    return str((record.get("extra") or {}).get("thread_id") or record["id"])


def _rerank(scored: list[tuple[float, int]], records: list[dict], k: int) -> list[tuple[float, int]]:
    """Order by score, but keep top-k useful as citations.

    One thread can hold up to 9 answers, all matching the same query, which would
    otherwise fill every citation slot with the same source. So take the best hit
    per thread first, then fill any remaining slots with the runners-up — their
    disagreement is what `perspectives` (R4) is built from.
    """
    best_first, extras, seen = [], [], set()
    for score, i in scored:
        thread = _thread_of(records[i])
        (extras if thread in seen else best_first).append((score, i))
        seen.add(thread)

    ordered = best_first + extras
    # R3: where relevance is close, the org's own material leads.
    top = ordered[:k]
    if top:
        cutoff = top[0][0] * (1 - PRIMARY_MARGIN)
        near, rest = [t for t in top if t[0] >= cutoff], [t for t in top if t[0] < cutoff]
        near.sort(key=lambda si: (records[si[1]].get("source_type", "primary") != "primary", -si[0]))
        top = near + rest
    return top


def search(query: str, k: int = 5) -> list[dict]:
    _, records, docs, lengths, avg_len, df = _index()
    n = len(records)
    k1, b = 1.5, 0.75
    terms = tokenize(query)
    scored = []
    for i, doc in enumerate(docs):
        score = 0.0
        for t in terms:
            tf = doc.get(t, 0)
            if not tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * lengths[i] / avg_len))
        if score > 0:
            scored.append((score, i))
    scored.sort(key=lambda si: -si[0])
    return [{**records[i], "score": round(s, 3)} for s, i in _rerank(scored, records, k)]
