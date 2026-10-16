"""R5 "Surprise me": topic list + a random rabbit-hole question. Owner: Bhajneek.

- Picks a *question* (forum thread), not an individual answer: the real dataset has
  one record per answer, and threads with many answers would otherwise dominate
  and repeat.
- Topics are a fixed, curated list (theology, history, music, literature, art,
  practice). A thread's topics = its forum `category` PLUS topics inferred from
  keywords in its question, question body and answers — so a kirtan thread filed
  under "theology" still shows up under Music.
- `category` may also be any free-text subject ("kirtan", "Bhai Gurdas", …);
  then the pool is whatever search() finds for it.
- Seeds are quality-filtered (real question, substantial answers, readable text)
  and weighted toward rich threads. Primary (the org's own) entries preferred (R3).
- No repeats: each topic cycles through its whole pool, never twice in a row.
- With an API key, Claude rewrites the seed into a short, intriguing hook using
  only facts from that thread (grounded-answer skill). The hook is kept only if
  search() finds the same thread again, so /api/ask can answer it. Otherwise,
  without a key, or on any error, the original dataset question is returned.
- The next pick per topic is prepared in the background, so the button is instant.
"""
from __future__ import annotations

import os
import random
import re
import threading
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
        "kirtan", "keertan", "raag", "raga", "shabad", "music", "sing", "rabab", "tabla",
        "harmonium", "dilruba", "taus", "sarangi", "ragi", "dhadi", "kavishri", "melod",
        "instrument", "jori",
    ]),
    "literature": ("Literature", [
        "gurbani", "bani", "granth", "dasam", "japji", "jaap", "sukhmani", "rehras", "poet",
        "poem", "verse", "bhai gurdas", "vaar", "gurmukhi", "script", "scripture", "book",
        "janamsakhi", "janam sakhi", "author", "ang", "hymn", "writing", "text", "translat",
    ]),
    "art": ("Art & Architecture", [
        "art", "artist", "painting", "paint", "architect", "harmandir", "golden temple",
        "darbar sahib", "akal takht", "calligraph", "sculpt", "miniature", "fresco", "gatka",
        "khanda", "nishan sahib", "phulkari", "design", "symbol", "dome", "tattoo", "picture",
        "photo", "portrait", "image",
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

MIN_QUESTION_WORDS = 4      # "Langar?" is not a rabbit hole
MIN_ANSWER_CHARS = 200      # the hook needs facts to draw on
ASCII_GURMUKHI = re.compile(r"\b[a-zA-Z]*[\]\[\\^`~|}{]{1,}[a-zA-Z]*\b")  # legacy font text

_PATTERNS = {k: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in kws) + r")", re.I)
             for k, (_, kws) in TOPICS.items()}
_lock = threading.Lock()
_shown: dict[str, set[str]] = {}   # topic key -> thread ids already served this cycle
_last: dict[str, str] = {}         # topic key -> thread id served last
_hooks: dict[str, str] = {}        # thread id -> verified hook (cache)
_ready: dict[str, dict] = {}       # topic key -> prepared response for the next click
_threads: Optional[dict[str, dict]] = None


def _key(text: Optional[str]) -> str:
    return (text or "").strip().lower()


def _thread_id(record: dict) -> str:
    return str((record.get("extra") or {}).get("thread_id") or record["id"])


def _classify(question: str, body: str, answers: list[str], categories: set[str], tags: set[str]) -> set[str]:
    found = {c for c in categories if c in TOPICS} | {t for t in tags if t in TOPICS}
    found |= {TAG_TOPICS[t] for t in tags if t in TAG_TOPICS}
    head = f"{question} {body} {' '.join(tags)}"
    text = " ".join(a[:800] for a in answers)
    for k, pat in _PATTERNS.items():
        # Question/body/tags are strong evidence; answers alone need two hits.
        if pat.search(head) or len(pat.findall(text)) >= 2:
            found.add(k)
    found |= {c for c in categories if c and c != "other"}  # custom dataset categories still work
    return found


def _good_seed(t: dict) -> bool:
    q = t["question"]
    if len(q.split()) < MIN_QUESTION_WORDS:
        return False
    if sum(len(a) for a in t["answers"]) < MIN_ANSWER_CHARS:
        return False
    return len(ASCII_GURMUKHI.findall(q)) < 2


def _build_threads() -> dict[str, dict]:
    """Group answer records into question threads, once per process."""
    threads: dict[str, dict] = {}
    for r in retrieval.all_records():
        tid = _thread_id(r)
        t = threads.setdefault(tid, {
            "id": tid, "seed": r, "question": r["question"],
            "body": (r.get("extra") or {}).get("question_body") or "",
            "answers": [], "categories": set(), "tags": set(), "primary": False,
        })
        t["answers"].append(r["answer"])
        t["categories"].add(_key(r.get("category")))
        t["tags"] |= {_key(x) for x in r.get("tags", [])}
        t["primary"] |= r.get("source_type", "primary") == "primary"
        pos = (r.get("extra") or {}).get("answer_position", 1)
        if pos < (t["seed"].get("extra") or {}).get("answer_position", 1):
            t["seed"] = r  # cite the first answer as the seed
    for t in threads.values():
        t["topics"] = _classify(t["question"], t["body"], t["answers"], t["categories"], t["tags"])
        t["good"] = _good_seed(t)
        # Richer threads make better rabbit holes (and better R4 perspectives).
        t["weight"] = 1 + min(len(t["answers"]), 5) + min(sum(map(len, t["answers"])) // 1500, 3)
    return threads


def _all_threads() -> dict[str, dict]:
    global _threads
    if _threads is None:
        with _lock:
            if _threads is None:
                _threads = _build_threads()
    return _threads


def _resolve(topic: Optional[str]) -> Optional[str]:
    """Map a topic key or label (any case) to a TOPICS key; None if free text."""
    t = _key(topic)
    for k, (label, _) in TOPICS.items():
        if t in (k, label.lower()):
            return k
    return None


def categories() -> list[str]:
    counts: dict[str, int] = {}
    for t in _all_threads().values():
        if t["good"]:
            for c in t["topics"]:
                counts[c] = counts.get(c, 0) + 1
    return [k for k in TOPICS if counts.get(k)] + sorted(c for c in counts if c not in TOPICS)


def _pool(topic: Optional[str]) -> list[dict]:
    threads = _all_threads()
    if not _key(topic):
        pool = list(threads.values())
    elif (k := _resolve(topic) or (_key(topic) if _key(topic) in categories() else None)):
        pool = [t for t in threads.values() if k in t["topics"]]
    else:
        ids = dict.fromkeys(_thread_id(r) for r in retrieval.search(topic, k=25) if r.get("score", 0) > 0)
        pool = [threads[i] for i in ids if i in threads]
    good = [t for t in pool if t["good"]] or pool
    return [t for t in good if t["primary"]] or good


def _pick(topic: Optional[str]) -> Optional[dict]:
    pool = _pool(topic)
    if not pool:
        return None
    key = _key(topic) or "*"
    with _lock:
        shown = _shown.setdefault(key, set())
        fresh = [t for t in pool if t["id"] not in shown]
        if not fresh:  # whole pool served: new cycle, but never the same question twice in a row
            shown.clear()
            fresh = [t for t in pool if t["id"] != _last.get(key)] or pool
        t = random.choices(fresh, weights=[x["weight"] for x in fresh])[0]
        shown.add(t["id"])
        _last[key] = t["id"]
    return t


def random_question(category: Optional[str] = None) -> Optional[dict]:
    """The seed record (first answer) of a random good thread in the topic."""
    t = _pick(category)
    return t["seed"] if t else None


HOOK_PROMPT = """You turn one question thread from SikhNet's Q&A archive into a single short, \
intriguing "rabbit-hole" question that makes a curious young person want to click it.

Rules:
- The ANSWERS must fully answer your question. Use only facts stated in them; add nothing.
- Keep the thread's key terms (names, Punjabi words) so a search for your question finds it.
- Never quote, paraphrase or invent Gurbani.
- Respectful, warm, curious. Under 20 words. Output only the question, ending with "?"."""


def _finds_thread(question: str, thread_id: str) -> bool:
    return any(_thread_id(r) == thread_id for r in retrieval.search(question, k=5))


def _hook(t: dict, label: str) -> str:
    seed = t["question"]
    if not llm.llm_enabled() or os.environ.get("SIKHNET_SURPRISE_HOOKS", "1") == "0":
        return seed
    if t["id"] in _hooks:
        return _hooks[t["id"]]
    answers = "\n---\n".join(a[:1200] for a in t["answers"][:3])
    try:
        resp = llm._get_client().messages.create(
            model=os.environ.get("SIKHNET_SURPRISE_MODEL", llm.MODEL),
            max_tokens=120,
            system=HOOK_PROMPT,
            messages=[{"role": "user", "content":
                       f"Topic: {label}\n\nQUESTION: {seed}\n{t['body'][:600]}\n\nANSWERS:\n{answers}"}],
            timeout=15,
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip().strip('"')
    except Exception:
        return seed
    if not text.endswith("?") or len(text) > 200 or "\n" in text or not _finds_thread(text, t["id"]):
        return seed
    _hooks[t["id"]] = text
    return text


def _label(topic: Optional[str], t: dict) -> tuple[str, str]:
    k = _resolve(topic)
    cat = k or _key(topic) or next((c for c in TOPICS if c in t["topics"]), "other")
    return cat, TOPICS[cat][0] if cat in TOPICS else (topic or "Sikhi")


def _prepare(topic: Optional[str]) -> Optional[dict]:
    t = _pick(topic)
    if not t:
        return None
    cat, label = _label(topic, t)
    return {"question": _hook(t, label), "category": cat, "id": t["seed"]["id"],
            "seed_question": t["question"]}


def _prefetch(topic: Optional[str]) -> None:
    def run():
        res = _prepare(topic)
        if res:
            with _lock:
                _ready[_key(topic) or "*"] = res
    threading.Thread(target=run, daemon=True).start()


@router.get("/api/categories")
def get_categories():
    cats = categories()
    return {"categories": cats,
            "labels": {c: TOPICS[c][0] if c in TOPICS else c.title() for c in cats}}


@router.get("/api/surprise")
def surprise(category: Optional[str] = None):
    with _lock:
        res = _ready.pop(_key(category) or "*", None)
    res = res or _prepare(category)
    if not res:
        return {"question": None, "category": category, "id": None}
    if llm.llm_enabled():
        _prefetch(category)  # make the next click instant
    return res
