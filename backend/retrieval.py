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


# Query-side vocabulary bridge. The dataset is forum English plus romanised
# Punjabi ("langar", "dastaar"); users ask in plain English ("community
# kitchen", "turban"). Only queries are expanded — the index stays a faithful
# record of what members actually wrote. Each entry adds terms, never replaces,
# so an exact-term query is unaffected.
QUERY_EXPANSIONS: dict[str, list[str]] = {
    "community kitchen": ["langar"],
    "free kitchen": ["langar"],
    "free food": ["langar"],
    "holy book": ["granth", "sggs", "gurbani"],
    "scripture": ["granth", "gurbani"],
    "sikh scripture": ["granth", "sggs"],
    "temple": ["gurdwara", "gurudwara"],
    "sikh temple": ["gurdwara", "gurudwara"],
    "place of worship": ["gurdwara"],
    "turban": ["dastaar", "pagri", "pagh"],
    "headscarf": ["chunni", "dupatta"],
    "head covering": ["dastaar", "chunni", "patka"],
    "uncut hair": ["kesh"],
    "comb": ["kangha"],
    "bracelet": ["kara"],
    "steel bangle": ["kara"],
    "sword": ["kirpan"],
    "dagger": ["kirpan"],
    "five ks": ["kakkar", "kakaar", "panj"],
    "5 ks": ["kakkar", "kakaar", "panj"],
    "initiation": ["amrit", "khande", "sanchar"],
    "baptism": ["amrit", "sanchar"],
    "baptised": ["amritdhari"],
    "daily prayers": ["nitnem", "paath", "banis"],
    "morning prayer": ["nitnem", "japji", "amritvela"],
    "hymn": ["shabad", "kirtan"],
    "hymns": ["shabad", "kirtan"],
    "music": ["kirtan", "raag", "shabad"],
    "musician": ["ragi", "raagi", "kirtani"],
    "congregation": ["sangat"],
    "selfless service": ["seva", "sewa"],
    "volunteering": ["seva", "sewa"],
    "code of conduct": ["rehat", "maryada"],
    "founded": ["started", "began", "origin"],
    "started": ["founded", "began", "origin"],
    "founder": ["founded", "started", "first"],
    "wedding": ["anand", "karaj", "lavan", "laavan"],
    "funeral": ["antam", "sanskar", "cremation"],
    "charity": ["daswandh", "daan"],
    "tithe": ["daswandh"],
}

# Longest phrases first, so "sikh temple" wins over "temple".
_EXPANSION_PHRASES = sorted(QUERY_EXPANSIONS, key=lambda s: -len(s))

# Expansion is a bridge for vocabulary the dataset lacks, not a blanket OR.
# If members already write "turban" (df 76), adding "pagri" (df 1) just drags
# in how-to-tie threads and buries the question that was asked. So a synonym is
# only added when the dataset clearly prefers it: the user's own word must be
# thinly represented, and the alternative meaningfully better represented.
WELL_REPRESENTED = 60   # user's word is common enough to stand on its own
BETTER_BY = 2           # alternative must be this many times more common


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in STOPWORDS]


def expand_query(query: str) -> list[str]:
    """Query terms plus bridged vocabulary, decided against the corpus itself.

    Added terms are appended after the user's own, deduplicated, so they add
    recall without outweighing what was actually typed.
    """
    terms = tokenize(query)
    *_, df = _index()
    lowered = " ".join(re.findall(r"\w+", query.lower()))

    added: list[str] = []
    for phrase in _EXPANSION_PHRASES:
        if phrase not in lowered:
            continue
        words = tokenize(phrase)
        if not words:
            continue
        source_df = min(df[w] for w in words)
        if source_df >= WELL_REPRESENTED:
            continue                      # the dataset uses the user's wording
        added.extend(
            target for target in QUERY_EXPANSIONS[phrase]
            if df[target] > source_df * BETTER_BY
        )

    seen = set(terms)
    return terms + [x for x in added if not (x in seen or seen.add(x))]


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
    terms = expand_query(query)
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
