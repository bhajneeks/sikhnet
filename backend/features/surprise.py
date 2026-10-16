"""R5 "Surprise me": topic list + a random rabbit-hole question. Owner: Bhajneek.

- Topics are a fixed, curated list (theology, history, music, literature, art,
  practice). A record's topics come from its `category` field if set, otherwise
  from keywords in its question, tags and answer — so the dropdown works on the
  raw dataset without hand-tagging.
- `category` may also be any free-text subject ("kirtan", "Bhai Gurdas", …);
  then the pool is whatever search() finds for it.
- No repeats: each topic cycles through its whole pool before showing a question again.
- Primary (the org's own) entries are preferred when the pool has any (R3).
- With an API key, Claude rewrites the seed question into a short, intriguing hook
  using only facts from that one entry (grounded-answer skill). Without a key,
  or on any error, the original dataset question is returned.
"""
from __future__ import annotations

import os
import random
import re
from typing import Optional

from fastapi import APIRouter

from backend import llm, retrieval

router = APIRouter()

# key -> (label, keywords). Keywords match on word starts, case-insensitive.
TOPICS: dict[str, tuple[str, list[str]]] = {
    "theology": ("Theology", [
        "god", "waheguru", "ik onkar", "naam", "hukam", "karma", "karam", "mukti", "soul",
        "simran", "meditat", "prayer", "ardas", "ego", "haumai", "maya", "grace", "kirpa",
        "faith", "belief", "gurmat", "reincarnat", "heaven", "hell", "spiritual", "divine",
        "afterlife", "sach khand", "creation", "doubt",
    ]),
    "history": ("History", [
        "history", "historic", "founded", "founder", "guru nanak", "guru gobind", "guru arjan",
        "guru tegh", "battle", "martyr", "shaheed", "shahid", "khalsa", "vaisakhi", "1699",
        "1984", "empire", "maharaja", "ranjit singh", "misl", "mughal", "partition",
        "banda singh", "century", "gurus",
    ]),
    "music": ("Music", [
        "kirtan", "raag", "raga", "shabad", "music", "sing", "rabab", "tabla", "harmonium",
        "dilruba", "taus", "sarangi", "ragi", "dhadi", "kavishri", "melod", "instrument",
    ]),
    "literature": ("Literature", [
        "gurbani", "bani", "granth", "dasam", "japji", "jaap", "sukhmani", "rehras", "poet",
        "poem", "verse", "bhai gurdas", "vaar", "gurmukhi", "script", "scripture", "book",
        "janamsakhi", "janam sakhi", "author", "ang", "hymn", "writing", "text", "translat",
    ]),
    "art": ("Art & Architecture", [
        "art", "painting", "paint", "architect", "harmandir", "golden temple", "darbar sahib",
        "akal takht", "calligraph", "sculpt", "miniature", "fresco", "gatka", "khanda",
        "nishan sahib", "phulkari", "design", "symbol", "dome",
    ]),
    "practice": ("Practice & Daily Life", [
        "kesh", "hair", "turban", "dastar", "pagg", "five k", "5 k", "kara", "kirpan",
        "kangha", "kachera", "amrit", "rehat", "rahit", "langar", "seva", "sewa", "nitnem",
        "diet", "meat", "alcohol", "wedding", "anand karaj", "marriage", "naming",
        "gurpurab", "daily", "gurdwara", "sangat", "parents",
    ]),
}
# Dataset tags that map to a topic without appearing in the keyword lists.
TAG_TOPICS = {"gurus": "history", "rehat": "practice", "seva": "practice", "kirtan": "music"}

_PATTERNS = {k: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in kws) + r")", re.I)
             for k, (_, kws) in TOPICS.items()}
_shown: dict[str, set[str]] = {}   # topic key -> ids already served this cycle
_hooks: dict[str, str] = {}        # record id -> generated hook (cache)
_last: dict[str, str] = {}         # topic key -> id served last
_topics: dict[str, frozenset] = {}  # record id -> topics (cache; records are static per process)


def _key(text: str) -> str:
    return text.strip().lower()


def _record_topics(record: dict) -> frozenset:
    if record["id"] not in _topics:
        _topics[record["id"]] = frozenset(_classify(record))
    return _topics[record["id"]]


def _classify(record: dict) -> set[str]:
    cat = _key(record.get("category") or "")
    if cat in TOPICS:
        return {cat}
    tags = [_key(t) for t in record.get("tags", [])]
    found = {t for t in tags if t in TOPICS} | {TAG_TOPICS[t] for t in tags if t in TAG_TOPICS}
    head = record["question"] + " " + " ".join(tags)
    body = record["answer"][:800]
    for k, pat in _PATTERNS.items():
        # Question/tags are strong evidence; the answer alone needs two hits.
        if pat.search(head) or len(pat.findall(body)) >= 2:
            found.add(k)
    if cat and cat != "other":
        found.add(cat)  # custom categories from the dataset still work
    return found


def _resolve(topic: Optional[str]) -> Optional[str]:
    """Map a topic key or label (any case) to a TOPICS key; None if free text."""
    t = _key(topic or "")
    for k, (label, _) in TOPICS.items():
        if t in (k, label.lower()):
            return k
    return None


def categories() -> list[str]:
    counts: dict[str, int] = {}
    for r in retrieval.all_records():
        for t in _record_topics(r):
            counts[t] = counts.get(t, 0) + 1
    return [k for k in TOPICS if counts.get(k)] + sorted(t for t in counts if t not in TOPICS)


def _pool(topic: Optional[str]) -> list[dict]:
    if not topic or not topic.strip():
        pool = list(retrieval.all_records())
    elif (k := _resolve(topic)) or _key(topic) in categories():
        k = k or _key(topic)
        pool = [r for r in retrieval.all_records() if k in _record_topics(r)]
    else:
        pool = [r for r in retrieval.search(topic, k=25) if r.get("score", 0) > 0]
    primary = [r for r in pool if r.get("source_type", "primary") == "primary"]
    return primary or pool


def random_question(category: Optional[str] = None) -> Optional[dict]:
    pool = _pool(category)
    if not pool:
        return None
    key = _key(category or "*")
    shown = _shown.setdefault(key, set())
    fresh = [r for r in pool if r["id"] not in shown]
    if not fresh:  # whole pool served: new cycle, but never the same question twice in a row
        shown.clear()
        fresh = [r for r in pool if r["id"] != _last.get(key)] or pool
    r = random.choice(fresh)
    shown.add(r["id"])
    _last[key] = r["id"]
    return r


HOOK_PROMPT = """You turn one entry from SikhNet's Q&A archive into a single short, intriguing \
"rabbit-hole" question that makes a curious young person want to click it.

Rules:
- The ENTRY must fully answer your question. Use only facts stated in the entry; add nothing.
- Keep the entry's key terms (names, Punjabi words) so a search for your question finds this entry.
- Never quote, paraphrase or invent Gurbani.
- Respectful, warm, curious. Under 20 words. Output only the question, ending with "?"."""


def _hook(record: dict, label: str) -> str:
    seed = record["question"]
    if not llm.llm_enabled() or os.environ.get("SIKHNET_SURPRISE_HOOKS", "1") == "0":
        return seed
    if record["id"] in _hooks:
        return _hooks[record["id"]]
    try:
        resp = llm._get_client().messages.create(
            model=os.environ.get("SIKHNET_SURPRISE_MODEL", "claude-haiku-5-5"),
            max_tokens=120,
            system=HOOK_PROMPT,
            messages=[{"role": "user", "content":
                       f"Topic: {label}\n\nENTRY\nQuestion: {seed}\nAnswer: {record['answer'][:1500]}"}],
            timeout=8,
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip().strip('"')
    except Exception:
        return seed
    if not text.endswith("?") or len(text) > 200 or "\n" in text:
        return seed
    _hooks[record["id"]] = text
    return text


@router.get("/api/categories")
def get_categories():
    cats = categories()
    return {"categories": cats,
            "labels": {c: TOPICS[c][0] if c in TOPICS else c.title() for c in cats}}


@router.get("/api/surprise")
def surprise(category: Optional[str] = None):
    r = random_question(category)
    if not r:
        return {"question": None, "category": category, "id": None}
    k = _resolve(category) if category else None
    topics = _record_topics(r)
    cat = k or (_key(category) if category else next((t for t in TOPICS if t in topics), "other"))
    label = TOPICS[cat][0] if cat in TOPICS else (category or "Sikhi")
    return {"question": _hook(r, label), "category": cat, "id": r["id"], "seed_question": r["question"]}
