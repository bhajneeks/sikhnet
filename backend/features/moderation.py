"""Moderation: junk, hate, bots and crisis messages (SikhNet feedback #4). Owner: Bhajneek.

Layers, cheapest first:
1. Bots      — honeypot field, too-fast submits, per-person/IP rate limits,
               duplicate posts. Blocked outright.
2. Rules     — hate phrases → blocked; links, shouting, keyboard-mash,
               profanity → held for review (hidden until a moderator approves).
3. Crisis    — self-harm / abuse / danger → never answered by the AI or left
               public: held for a human, and the person is shown help lines
               right away (brief non-negotiable).
4. Claude    — when an API key is set, every post that passed the rules is
               checked in the background; hate/harassment/spam gets hidden.
5. People    — anyone can report; 3 reports hide a post until reviewed.
               Moderators work the queue in /moderate.html.
"""
from __future__ import annotations

import json
import os
import re
import threading
from typing import Optional

from backend import llm
from backend.features import store

MIN_FORM_MS = 2500          # humans take longer than this to write a post
POSTS_PER_10_MIN = 5
VOTES_PER_MIN = 30
ASKS_PER_MIN = 20
REPORTS_TO_HIDE = 3

# Hate phrases: blocked. Kept short and generic on purpose; Claude catches the rest.
HATE = ["kill all", "death to", "gas the", "go back to your country", "subhuman", "vermin",
        "should be exterminated", "white power", "heil hitler", "sieg heil", "towelhead", "raghead",
        "sand nigger", "paki", "terrorist religion", "burn the gurdwara", "burn down the gurdwara"]
# Profanity: held for review (people can be upset without being hateful).
PROFANITY = ["fuck", "fucking", "fucked", "fucker", "shit", "shitty", "bullshit", "bitch", "bastard", "asshole", "dick", "cunt", "chutiya", "bhenchod",
             "madarchod", "kutta", "kamina", "harami"]
CRISIS = ["kill myself", "killing myself", "suicide", "suicidal", "end my life", "want to die",
          "self harm", "self-harm", "cut myself", "cutting myself", "hurt myself", "no reason to live",
          "being abused", "abusing me", "he hits me", "she hits me", "they hit me", "beats me",
          "molest", "raped", "rape me", "unsafe at home", "forced marriage", "forcing me to marry",
          "threatening to kill", "honour killing", "honor killing"]

# Whole words only, so "paki" never matches "Pakistan" nor "dick" "Dickens".
_HATE = re.compile(r"\b(?:" + "|".join(map(re.escape, HATE)) + r")s?\b", re.I)
_PROF = re.compile(r"\b(?:" + "|".join(map(re.escape, PROFANITY)) + r")s?\b", re.I)
_CRISIS = re.compile(r"\b(?:" + "|".join(map(re.escape, CRISIS)) + r")", re.I)
_LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|net|org|io|ru|xyz|info|biz|top)\b", re.I)
_MASH = re.compile(r"(.)\1{6,}|\b[bcdfghjklmnpqrstvwxz]{7,}\b", re.I)

# Shown to anyone whose message looks like a crisis. General lines only; SikhNet
# should swap in their partner organisations.
HELP = {
    "message": ("It sounds like you might be going through something really hard. You deserve support "
                "from a real person. Our assistant won't answer this, but these people can help right now."),
    "contacts": [
        {"name": "Emergency services", "detail": "If you're in danger now: 911 (US/Canada) · 112 (India/EU) · 999 (UK)"},
        {"name": "988 Suicide & Crisis Lifeline (US)", "detail": "Call or text 988", "url": "https://988lifeline.org"},
        {"name": "Tele MANAS (India)", "detail": "Call 14416 · free, 24/7, many languages"},
        {"name": "Samaritans (UK & Ireland)", "detail": "Call 116 123", "url": "https://www.samaritans.org"},
        {"name": "Childhelp (US, for kids and teens)", "detail": "Call or text 1-800-422-4453"},
    ],
    "human": "A SikhNet moderator will also see your message. Please talk to a parent, teacher, Granthi or someone you trust.",
}


def is_crisis(text: str) -> bool:
    return bool(_CRISIS.search(text or ""))


def check(text: str, *, voter: str, ip: str, elapsed_ms: Optional[int] = None,
          honeypot: str = "") -> dict:
    """Decide what happens to a new post.

    Returns {"action": "allow"|"review"|"block", "flags": [...], "crisis": bool, "reason": str}.
    """
    flags: list[str] = []
    t = (text or "").strip()

    # 1. bots
    if honeypot:
        return {"action": "block", "flags": ["bot:honeypot"], "crisis": False, "reason": "Looks automated."}
    if elapsed_ms is not None and elapsed_ms < MIN_FORM_MS:
        return {"action": "block", "flags": ["bot:fast"], "crisis": False,
                "reason": "That was very fast. Take a moment and try again."}
    if (store.recent_count("posts", "voter = ?", (voter,), 600) >= POSTS_PER_10_MIN
            or store.recent_count("posts", "ip = ?", (ip,), 600) >= POSTS_PER_10_MIN * 2):
        return {"action": "block", "flags": ["bot:rate"], "crisis": False,
                "reason": "You're posting a lot. Please wait a few minutes."}
    if store.q("SELECT 1 FROM posts WHERE body = ? AND created > ? LIMIT 1", (t, store.now() - 86400)):
        return {"action": "block", "flags": ["dup"], "crisis": False, "reason": "This was already posted."}

    # 2. rules
    if len(t) < 3:
        return {"action": "block", "flags": ["empty"], "crisis": False, "reason": "Please write a little more."}
    if _HATE.search(t):
        return {"action": "block", "flags": ["hate"], "crisis": False,
                "reason": "This breaks our community rules: no hate or attacks on anyone."}
    if _LINK.search(t):
        flags.append("link")
    letters = [c for c in t if c.isalpha()]
    if len(letters) > 20 and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        flags.append("caps")
    if _MASH.search(t):
        flags.append("junk")
    if _PROF.search(t):
        flags.append("profanity")

    # 3. crisis
    crisis = is_crisis(t)
    if crisis:
        flags.append("crisis")

    action = "review" if flags else "allow"
    reason = ("Thanks. A moderator will check this before it appears." if action == "review" else "")
    return {"action": action, "flags": flags, "crisis": crisis, "reason": reason}


AI_PROMPT = """You moderate a friendly, anonymous Q&A community about Sikhi, used by kids, teens and adults.
Classify the post. Respond with JSON only: {"hate": bool, "harassment": bool, "spam": bool, "sexual": bool, "crisis": bool}.
- hate: attacks a religion, caste, race, gender or group. Disagreeing respectfully about beliefs is NOT hate.
- harassment: insults or threatens a person.
- spam: ads, scams, links to sell something, gibberish.
- sexual: explicit sexual content.
- crisis: the writer or someone else may be in danger (self-harm, abuse, violence)."""


def ai_review_async(post_id: int, text: str) -> None:
    """Claude second opinion in the background; hides the post if it's flagged."""
    if not llm.llm_enabled() or os.environ.get("SIKHNET_AI_MODERATION", "1") == "0":
        return

    def run():
        try:
            resp = llm._get_client().messages.create(
                model=os.environ.get("SIKHNET_MODERATION_MODEL", llm.MODEL),
                max_tokens=100, system=AI_PROMPT, timeout=20,
                messages=[{"role": "user", "content": text[:4000]}],
            )
            raw = "".join(b.text for b in resp.content if b.type == "text")
            verdict = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        except Exception:
            return
        bad = [k for k in ("hate", "harassment", "spam", "sexual", "crisis") if verdict.get(k)]
        if bad:
            row = store.q("SELECT flags FROM posts WHERE id = ?", (post_id,))
            if not row:
                return
            flags = ",".join(filter(None, [row[0]["flags"]] + [f"ai:{b}" for b in bad]))
            store.x("UPDATE posts SET status = 'review', flags = ? WHERE id = ? AND status = 'visible'",
                    (flags, post_id))
            store.x("INSERT INTO mod_log(target, action, reason, created) VALUES (?, 'auto-hide', ?, ?)",
                    (f"post:{post_id}", "claude: " + ", ".join(bad), store.now()))

    threading.Thread(target=run, daemon=True).start()


def report(target: str, voter: str, reason: str) -> dict:
    store.x("INSERT OR IGNORE INTO reports(target, voter, reason, created) VALUES (?, ?, ?, ?)",
            (target, voter, (reason or "")[:200], store.now()))
    n = store.q("SELECT COUNT(*) AS n FROM reports WHERE target = ?", (target,))[0]["n"]
    hidden = False
    if n >= REPORTS_TO_HIDE and target.startswith("post:"):
        pid = int(target.split(":", 1)[1])
        row = store.q("SELECT flags, verified FROM posts WHERE id = ?", (pid,))
        if row and not row[0]["verified"]:
            flags = ",".join(filter(None, [row[0]["flags"], "reported"]))
            store.x("UPDATE posts SET status = 'review', flags = ? WHERE id = ? AND status = 'visible'", (flags, pid))
            store.x("INSERT INTO mod_log(target, action, reason, created) VALUES (?, 'auto-hide', ?, ?)",
                    (target, f"{n} reports", store.now()))
            hidden = True
    return {"reports": n, "hidden": hidden}
