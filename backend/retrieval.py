"""Retrieval over data/processed/qa.jsonl. Owner: data lane (see TEAM.md).

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


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in STOPWORDS]


@lru_cache(maxsize=1)
def _index():
    path = DATA_PATH if DATA_PATH.exists() else SAMPLE_PATH
    records = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    # Questions are weighted double: they're the best match signal for user questions.
    docs = [Counter(tokenize(r["question"]) * 2 + tokenize(r["answer"])) for r in records]
    lengths = [sum(d.values()) for d in docs]
    avg_len = sum(lengths) / max(len(lengths), 1)
    df = Counter(term for d in docs for term in d)
    return path, records, docs, lengths, avg_len, df


def records_count() -> int:
    return len(_index()[1])


def data_path() -> str:
    return str(_index()[0])


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
    scored.sort(reverse=True)
    return [{**records[i], "score": round(s, 3)} for s, i in scored[:k]]
