"""Community features from SikhNet's feedback. Owner: Bhajneek.

1. Ratings      — 👍/👎 on bot answers, archive sources and board replies; Wilson
                  score ranks them so better answers rise; tags like "Highly rated".
2. Popular      — trending topics, most-asked questions, most-discussed threads.
3. Age groups   — every list filters by who's asking (kids / teens / adults).
4. Moderation   — bots, junk, hate, crisis → see moderation.py; queue for humans.
+  Bulletin board — people post questions, reply, vote replies up/down, report.

Board content is community content: it is never fed to the answering model and
is always labelled as such in the UI (grounded-answer contract).
Contract: docs/ARCHITECTURE.md § 3 "Community"; decision 006.
"""
from __future__ import annotations

import os
import re
import secrets
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend import retrieval
from backend.features import audience as ages, moderation, store, surprise

router = APIRouter()
VOTER = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
TARGET = re.compile(r"^(post|source|answer):[A-Za-z0-9_.:-]{1,80}$")


# ---------------------------------------------------------------- helpers
def _deployed() -> bool:
    """Running on a host (Railway, or SIKHNET_PRODUCTION=1), not a laptop."""
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("SIKHNET_PRODUCTION"))


def _ip(request: Request) -> str:
    # Railway's proxy sets X-Real-IP; X-Forwarded-For is a fallback for other hosts.
    raw = (request.headers.get("x-real-ip", "").strip()
           or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
           or (request.client.host if request.client else ""))
    return store.hash_ip(raw)


def _voter(v: Optional[str]) -> str:
    if not v or not VOTER.match(v):
        raise HTTPException(400, "Missing anonymous id. Reload the page and try again.")
    return v


def _tag(t: dict) -> Optional[dict]:
    """The accuracy/quality tag shown next to an answer, from community votes."""
    n = t["up"] + t["down"]
    if n < 3:
        return None
    pct = round(100 * t["up"] / n)
    if t["score"] >= 0.4 and pct >= 75:
        return {"kind": "good", "label": f"Highly rated · {pct}% helpful"}
    if t["score"] < 0.25 and t["down"] > t["up"]:
        return {"kind": "low", "label": f"Low rated · {pct}% helpful"}
    return {"kind": "mixed", "label": f"{pct}% found this helpful"}


def _rating_view(targets: list[str], voter: Optional[str]) -> dict:
    tallies = store.tallies(targets)
    mine = {}
    if voter and VOTER.match(voter) and targets:
        marks = ",".join("?" * len(targets))
        mine = {r["target"]: r["value"] for r in store.q(
            f"SELECT target, value FROM votes WHERE voter = ? AND target IN ({marks})", (voter, *targets))}
    return {t: {**v, "mine": mine.get(t, 0), "tag": _tag(v)} for t, v in tallies.items()}


def _excerpt(text: str, n: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"


def _topic_for(text: str) -> Optional[str]:
    return next(iter(surprise.topics_for_text(text)), None)


def _log(target: str, action: str, reason: str = "") -> None:
    store.x("INSERT INTO mod_log(target, action, reason, created) VALUES (?, ?, ?, ?)",
            (target, action, reason, store.now()))


# ---------------------------------------------------------------- safety + age check
class CheckIn(BaseModel):
    text: str = Field(max_length=4000)
    audience: Optional[str] = None


@router.post("/api/check")
def check(body: CheckIn):
    """Before asking the AI: crisis messages go to people, not the model; and the
    question's age rating vs the chosen audience."""
    crisis = moderation.is_crisis(body.text)
    rating = ages.rate_text(body.text)
    return {"crisis": crisis, "help": moderation.HELP if crisis else None,
            "age_rating": rating, "allowed": ages.allowed(rating, body.audience)}


@router.get("/api/audiences")
def audiences():
    return {"audiences": [{"key": k, "label": v} for k, v in ages.LABELS.items()]}


# ---------------------------------------------------------------- ratings
class VoteIn(BaseModel):
    target: str
    value: int = Field(ge=-1, le=1)   # 1 up, -1 down, 0 clear
    voter: str
    reason: Optional[str] = Field(None, max_length=200)


@router.post("/api/vote")
def vote(body: VoteIn, request: Request):
    voter, ip = _voter(body.voter), _ip(request)
    if not TARGET.match(body.target):
        raise HTTPException(400, "Unknown item.")
    if store.recent_count("votes", "voter = ?", (voter,), 60) >= moderation.VOTES_PER_MIN:
        raise HTTPException(429, "Slow down a little.")
    if body.target.startswith("post:"):
        row = store.q("SELECT voter, status FROM posts WHERE id = ?", (body.target[5:],))
        if not row or row[0]["status"] != "visible":
            raise HTTPException(404, "That post isn't available.")
        if row[0]["voter"] == voter:
            raise HTTPException(400, "You can't vote on your own post.")
    if body.value == 0:
        store.x("DELETE FROM votes WHERE target = ? AND voter = ?", (body.target, voter))
    else:
        # One shared network can't stack more than 3 votes on one item (bot farms, one person many tabs).
        same_ip = store.q("SELECT COUNT(*) AS n FROM votes WHERE target = ? AND ip = ? AND voter != ?",
                          (body.target, ip, voter))[0]["n"]
        if same_ip >= 3:
            raise HTTPException(429, "Too many votes from this network on this item.")
        store.x("INSERT INTO votes(target, voter, ip, value, reason, created) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(target, voter) DO UPDATE SET value = excluded.value, reason = excluded.reason, "
                "created = excluded.created", (body.target, voter, ip, body.value, body.reason, store.now()))
    return _rating_view([body.target], voter)[body.target]


@router.get("/api/ratings")
def ratings(targets: str = "", voter: Optional[str] = None):
    ts = [t for t in targets.split(",") if TARGET.match(t)][:100]
    return {"ratings": _rating_view(ts, voter)}


# ---------------------------------------------------------------- popular
class TrackIn(BaseModel):
    question: str = Field(max_length=1000)
    voter: str
    audience: Optional[str] = None


@router.post("/api/track")
def track(body: TrackIn):
    """Count a question for "most asked". Crisis messages are never stored."""
    voter = _voter(body.voter)
    q = body.question.strip()
    if not q or moderation.is_crisis(q) or store.recent_count("asks", "voter = ?", (voter,), 60) >= moderation.ASKS_PER_MIN:
        return {"ok": False}
    norm = " ".join(retrieval.tokenize(q))
    if not norm:
        return {"ok": False}
    store.x("INSERT INTO asks(question, norm, topic, audience, voter, created) VALUES (?, ?, ?, ?, ?, ?)",
            (q[:300], norm, _topic_for(q), ages.normalize(body.audience), voter, store.now()))
    return {"ok": True}


@router.get("/api/popular")
def popular(audience: Optional[str] = None, days: int = 30):
    aud = audience
    since = store.now() - days * 86400
    labels = {k: v[0] for k, v in surprise.TOPICS.items()}

    # Most asked: what people actually typed (one count per person per question).
    groups: dict[str, dict] = {}
    for r in store.q("SELECT norm, question, voter, created FROM asks WHERE created > ?", (since,)):
        g = groups.setdefault(r["norm"], {"voters": set(), "forms": Counter(), "last": 0})
        g["voters"].add(r["voter"])
        g["forms"][r["question"]] += 1
        g["last"] = max(g["last"], r["created"])

    def nicest(forms: Counter) -> str:
        # Prefer a properly written form: capitalised, ending in "?", then the most common.
        q = max(forms, key=lambda f: (f[:1].isupper(), f.endswith("?"), forms[f]))
        return q if q.endswith("?") else q + "?"
    ranked = sorted(groups.values(), key=lambda g: (-len(g["voters"]), -g["last"]))
    asked = [{"question": nicest(g["forms"]), "count": len(g["voters"])} for g in ranked
             if _allowed_text(" ".join(g["forms"]), aud) and not moderation._PROF.search(" ".join(g["forms"]))][:8]

    # Trending topics: asks + board threads; the archive fills in until there's traffic.
    counts: Counter = Counter()
    for r in store.q("SELECT topic, COUNT(*) AS n FROM asks WHERE created > ? AND topic IS NOT NULL GROUP BY topic", (since,)):
        counts[r["topic"]] += r["n"]
    for r in store.q("SELECT topic, COUNT(*) AS n FROM posts WHERE parent_id IS NULL AND status = 'visible' "
                     "AND created > ? AND topic IS NOT NULL GROUP BY topic", (since,)):
        counts[r["topic"]] += 2 * r["n"]
    live = sum(counts.values()) >= 5
    if not live:
        counts = Counter()
        for t in surprise.threads_for(aud):
            for k in t["topics"]:
                if k in labels:
                    counts[k] += 1
    topics = [{"key": k, "label": labels.get(k, k.title()), "count": n} for k, n in counts.most_common(8) if k in labels]

    # Most discussed in SikhNet's archive: threads with the most answers.
    threads = sorted(surprise.threads_for(aud), key=lambda t: (-len(t["answers"]), t["question"]))
    discussed = [{"question": t["question"], "answers": len(t["answers"]), "id": t["seed"]["id"]} for t in threads[:6]]

    board = _list_threads("top", None, aud, None, None, limit=4)
    return {"topics": topics, "topics_source": "community" if live else "archive",
            "asked": asked, "discussed": discussed, "board": board}


def _allowed_text(text: str, aud: Optional[str]) -> bool:
    return ages.allowed(ages.rate_text(text), aud)


def _ok(rating: str, aud: Optional[str]) -> bool:
    return ages.allowed(rating, aud)


def _age_label(rating: str) -> str:
    return ages.RATING_LABELS.get(rating, rating)


def _rate_hit(hit: dict) -> str:
    return ages.rate_text(hit["question"], [hit["answer"]])


# ---------------------------------------------------------------- bulletin board
class PostIn(BaseModel):
    title: str = Field(min_length=0, max_length=200)
    body: str = Field(default="", max_length=5000)
    topic: Optional[str] = None
    audience: Optional[str] = None      # who it's for: kids | teens | adults
    author: Optional[str] = Field(None, max_length=40)
    voter: str
    elapsed_ms: Optional[int] = None
    website: str = ""                    # honeypot: humans never see or fill it


class ReplyIn(BaseModel):
    body: str = Field(max_length=5000)
    author: Optional[str] = Field(None, max_length=40)
    voter: str
    elapsed_ms: Optional[int] = None
    website: str = ""


def _author(a: Optional[str]) -> str:
    a = re.sub(r"\s+", " ", (a or "")).strip()
    if not a or moderation._PROF.search(a) or moderation._HATE.search(a) or moderation._LINK.search(a):
        return "Anonymous"
    return a[:40]


def _create(parent_id: Optional[int], title: str, body: str, topic: Optional[str], aud: Optional[str],
            author: Optional[str], voter: str, ip: str, elapsed_ms: Optional[int], honeypot: str) -> dict:
    text = f"{title}\n{body}".strip()
    verdict = moderation.check(text, voter=voter, ip=ip, elapsed_ms=elapsed_ms, honeypot=honeypot)
    if verdict["action"] == "block":
        return {"ok": False, "status": "blocked", "message": verdict["reason"]}
    rating = ages.rate_text(text)
    chosen = ages.AUDIENCES.get(ages.normalize(aud) or "", "all")
    rating = ages.stricter(rating, chosen)
    topic = topic if topic in surprise.TOPICS else _topic_for(text)
    status = "visible" if verdict["action"] == "allow" else "review"
    pid = store.x(
        "INSERT INTO posts(parent_id, title, body, topic, audience, age_rating, status, flags, author, voter, ip, created) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (parent_id, title or None, body, topic, ages.normalize(aud) or "all", rating, status,
         ",".join(verdict["flags"]), _author(author), voter, ip, store.now()))
    if status == "review":
        _log(f"post:{pid}", "held", ",".join(verdict["flags"]))
    else:
        moderation.ai_review_async(pid, text)
    out = {"ok": True, "id": pid, "status": status, "message": verdict["reason"] or "Posted."}
    if verdict["crisis"]:
        out["help"] = moderation.HELP
    return out


@router.post("/api/board")
def create_thread(body: PostIn, request: Request):
    title = body.title.strip()
    if len(title) < 8:
        raise HTTPException(400, "Write your question as a full sentence (8+ characters).")
    return _create(None, title, body.body.strip(), body.topic, body.audience, body.author,
                   _voter(body.voter), _ip(request), body.elapsed_ms, body.website)


@router.post("/api/board/{thread_id}/reply")
def reply(thread_id: int, body: ReplyIn, request: Request):
    row = store.q("SELECT id FROM posts WHERE id = ? AND parent_id IS NULL AND status = 'visible'", (thread_id,))
    if not row:
        raise HTTPException(404, "That question isn't available.")
    if len(body.body.strip()) < 2:
        raise HTTPException(400, "Write a reply first.")
    return _create(thread_id, "", body.body.strip(), None, None, body.author,
                   _voter(body.voter), _ip(request), body.elapsed_ms, body.website)


def _post_view(r, rating: dict, voter: Optional[str]) -> dict:
    return {"id": r["id"], "title": r["title"], "body": r["body"], "topic": r["topic"],
            "topic_label": surprise.TOPICS[r["topic"]][0] if r["topic"] in surprise.TOPICS else None,
            "age_rating": r["age_rating"], "age_label": ages.RATING_LABELS.get(r["age_rating"]),
            "author": r["author"], "created": r["created"], "verified": bool(r["verified"]),
            "mine": bool(voter and r["voter"] == voter), **{k: rating[k] for k in ("up", "down", "score", "tag")},
            "my_vote": rating["mine"]}


def _list_threads(sort: str, topic: Optional[str], aud: Optional[str], voter: Optional[str],
                  search: Optional[str], limit: int = 50) -> list[dict]:
    rows = store.q("SELECT * FROM posts WHERE parent_id IS NULL AND status = 'visible' ORDER BY created DESC LIMIT 500")
    rows = [r for r in rows if ages.allowed(r["age_rating"], aud) and (not topic or r["topic"] == topic)]
    if search:
        terms = set(retrieval.tokenize(search))
        rows = [r for r in rows if terms & set(retrieval.tokenize(f"{r['title']} {r['body']}"))]
    ids = [r["id"] for r in rows]
    replies: dict[int, list] = {}
    if ids:
        marks = ",".join("?" * len(ids))
        for rep in store.q(f"SELECT * FROM posts WHERE parent_id IN ({marks}) AND status = 'visible'", tuple(ids)):
            if ages.allowed(rep["age_rating"], aud):
                replies.setdefault(rep["parent_id"], []).append(rep)
    rating = _rating_view([f"post:{i}" for i in ids] +
                          [f"post:{rep['id']}" for reps in replies.values() for rep in reps], voter)
    out = []
    for r in rows:
        v = _post_view(r, rating[f"post:{r['id']}"], voter)
        reps = sorted(replies.get(r["id"], []),
                      key=lambda x: (-x["verified"], -rating[f"post:{x['id']}"]["score"], x["created"]))
        v["body"] = _excerpt(r["body"], 240)
        v["replies"] = len(reps)
        v["has_verified"] = any(x["verified"] for x in reps)
        v["top_reply"] = ({"body": _excerpt(reps[0]["body"], 200), "author": reps[0]["author"],
                           "verified": bool(reps[0]["verified"]), "up": rating[f"post:{reps[0]['id']}"]["up"]}
                          if reps else None)
        last = max([r["created"]] + [x["created"] for x in reps])
        v["activity"] = last
        out.append(v)
    if sort == "new":
        out.sort(key=lambda v: -v["created"])
    elif sort == "unanswered":
        out = [v for v in out if not v["replies"]]
        out.sort(key=lambda v: -v["created"])
    else:  # top: best-rated questions, then most discussed, then recent activity
        out.sort(key=lambda v: (-v["score"], -v["replies"], -v["activity"]))
    return out[:limit]


@router.get("/api/board")
def list_board(sort: str = "top", topic: Optional[str] = None, audience: Optional[str] = None,
               voter: Optional[str] = None, q: Optional[str] = None):
    threads = _list_threads(sort, topic, audience, voter, q)
    total = store.q("SELECT COUNT(*) AS n FROM posts WHERE parent_id IS NULL AND status = 'visible'")[0]["n"]
    return {"threads": threads, "total": total,
            "topics": [{"key": k, "label": v[0]} for k, v in surprise.TOPICS.items()]}


@router.get("/api/board/{thread_id}")
def get_thread(thread_id: int, audience: Optional[str] = None, voter: Optional[str] = None):
    rows = store.q("SELECT * FROM posts WHERE id = ? AND parent_id IS NULL", (thread_id,))
    if not rows or (rows[0]["status"] != "visible" and rows[0]["voter"] != voter):
        raise HTTPException(404, "That question isn't available.")
    t = rows[0]
    if not _ok(t["age_rating"], audience):
        return {"restricted": True, "age_label": _age_label(t["age_rating"])}
    reps = [r for r in store.q("SELECT * FROM posts WHERE parent_id = ? AND (status = 'visible' OR voter = ?)",
                               (thread_id, voter or "")) if _ok(r["age_rating"], audience)]
    rating = _rating_view([f"post:{thread_id}"] + [f"post:{r['id']}" for r in reps], voter)
    replies = [{**_post_view(r, rating[f"post:{r['id']}"], voter), "pending": r["status"] != "visible"} for r in reps]
    # Best first: moderator-verified, then Wilson score (votes), then oldest.
    replies.sort(key=lambda v: (-v["verified"], -v["score"], v["created"]))
    # Grounded links back to SikhNet's own archive on the same question.
    related, seen = [], set()
    for hit in retrieval.search(f"{t['title']} {t['body']}"[:500], k=8):
        tid = (hit.get("extra") or {}).get("thread_id") or hit["id"]
        if tid in seen or hit.get("score", 0) < 1.0 or not _ok(_rate_hit(hit), audience):
            continue
        seen.add(tid)
        related.append({"question": hit["question"], "id": hit["id"]})
        if len(related) == 3:
            break
    view = _post_view(t, rating[f"post:{thread_id}"], voter)
    view["pending"] = t["status"] != "visible"
    return {"thread": view, "replies": replies, "related": related}


class ReportIn(BaseModel):
    target: str
    voter: str
    reason: Optional[str] = Field(None, max_length=200)


@router.post("/api/report")
def report(body: ReportIn):
    voter = _voter(body.voter)
    if not TARGET.match(body.target):
        raise HTTPException(400, "Unknown item.")
    res = moderation.report(body.target, voter, body.reason or "")
    return {"ok": True, "hidden": res["hidden"],
            "message": "Thanks. A moderator will take a look." if not res["hidden"]
            else "Thanks. This has been hidden until a moderator reviews it."}


# ---------------------------------------------------------------- moderators
def _admin(request: Request, token: Optional[str]) -> None:
    want = os.environ.get("SIKHNET_ADMIN_TOKEN")
    if want:
        if not token or not secrets.compare_digest(token, want):
            raise HTTPException(401, "Moderator token required.")
        return
    if _deployed():
        # Never fall back to "localhost is trusted" on a server: proxies make that spoofable.
        raise HTTPException(503, "Moderation is off: set SIKHNET_ADMIN_TOKEN on the server.")
    # No token configured: only allow from this machine (local demo).
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(401, "Set SIKHNET_ADMIN_TOKEN to moderate remotely.")


@router.get("/api/mod/queue")
def mod_queue(request: Request, x_admin_token: Optional[str] = Header(None)):
    _admin(request, x_admin_token)
    held = store.q("SELECT p.*, (SELECT COUNT(*) FROM reports r WHERE r.target = 'post:' || p.id) AS reports, "
                   "(SELECT title FROM posts t WHERE t.id = p.parent_id) AS thread_title "
                   "FROM posts p WHERE status != 'visible' ORDER BY (flags LIKE '%crisis%') DESC, created DESC LIMIT 200")
    reported = store.q("SELECT p.*, COUNT(r.voter) AS reports FROM posts p JOIN reports r ON r.target = 'post:' || p.id "
                       "WHERE p.status = 'visible' GROUP BY p.id ORDER BY reports DESC LIMIT 50")
    # Lowest-rated bot answers and archive sources: candidates for SikhNet to review or update.
    low = []
    for r in store.q("SELECT target, SUM(value > 0) AS up, SUM(value < 0) AS down, "
                     "GROUP_CONCAT(reason, ' · ') AS reasons FROM votes "
                     "WHERE target NOT LIKE 'post:%' GROUP BY target HAVING down >= 1"):
        low.append({"target": r["target"], "up": r["up"], "down": r["down"],
                    "score": store.wilson(r["up"], r["down"]), "reasons": r["reasons"]})
    low.sort(key=lambda v: (v["score"], -v["down"]))
    titles = {}
    by_id = {rec["id"]: rec for rec in retrieval.all_records()}
    for v in low[:20]:
        kind, ident = v["target"].split(":", 1)
        rec = by_id.get(ident) if kind == "source" else None
        titles[v["target"]] = rec["question"] if rec else None
    stats = {
        "threads": store.q("SELECT COUNT(*) AS n FROM posts WHERE parent_id IS NULL AND status='visible'")[0]["n"],
        "replies": store.q("SELECT COUNT(*) AS n FROM posts WHERE parent_id IS NOT NULL AND status='visible'")[0]["n"],
        "held": len(held), "votes": store.q("SELECT COUNT(*) AS n FROM votes")[0]["n"],
        "asks": store.q("SELECT COUNT(*) AS n FROM asks")[0]["n"],
    }

    def view(r):
        return {"id": r["id"], "parent_id": r["parent_id"], "thread_title": r["thread_title"] if "thread_title" in r.keys() else None,
                "title": r["title"], "body": r["body"], "status": r["status"], "flags": [f for f in r["flags"].split(",") if f],
                "reports": r["reports"], "age_rating": r["age_rating"], "author": r["author"], "created": r["created"],
                "verified": bool(r["verified"])}
    log = [dict(r) for r in store.q("SELECT * FROM mod_log ORDER BY id DESC LIMIT 30")]
    return {"held": [view(r) for r in held], "reported": [view(r) for r in reported],
            "low_rated": [{**v, "title": titles.get(v["target"])} for v in low[:20]], "log": log, "stats": stats}


class ModIn(BaseModel):
    action: str   # approve | hide | delete | verify | unverify
    reason: Optional[str] = Field(None, max_length=200)


@router.post("/api/mod/post/{post_id}")
def mod_post(post_id: int, body: ModIn, request: Request, x_admin_token: Optional[str] = Header(None)):
    _admin(request, x_admin_token)
    if not store.q("SELECT 1 FROM posts WHERE id = ?", (post_id,)):
        raise HTTPException(404, "No such post.")
    sql = {
        "approve": "UPDATE posts SET status = 'visible' WHERE id = ?",
        "hide": "UPDATE posts SET status = 'hidden' WHERE id = ?",
        "delete": "DELETE FROM posts WHERE id = ? OR parent_id = ?",
        "verify": "UPDATE posts SET verified = 1, status = 'visible' WHERE id = ?",
        "unverify": "UPDATE posts SET verified = 0 WHERE id = ?",
    }.get(body.action)
    if not sql:
        raise HTTPException(400, "Unknown action.")
    store.x(sql, (post_id, post_id) if body.action == "delete" else (post_id,))
    if body.action == "approve":
        store.x("DELETE FROM reports WHERE target = ?", (f"post:{post_id}",))
    _log(f"post:{post_id}", body.action, body.reason or "")
    return {"ok": True}


@router.get("/api/mod/whoami")
def mod_whoami(request: Request, x_admin_token: Optional[str] = Header(None)):
    _admin(request, x_admin_token)
    return {"ok": True}
