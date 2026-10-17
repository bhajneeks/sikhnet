"""Age groups for questions and answers (SikhNet feedback #3). Owner: Bhajneek.

Every archive thread, board post and question gets an age rating:
  all   — fine for kids (under 13)
  teen  — fine for teens (13-17) and adults: dating, alcohol, caste, 1984 …
  adult — adults only: sexual content, abuse, self-harm …

A viewer picks who's asking (kids / teens / adults); lists (Surprise me,
popular questions, the bulletin board) only show what fits. Ratings come from
keyword rules, so they're explainable; a poster can raise a post's rating but
never lower it below what the rules find.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

RATINGS = ["all", "teen", "adult"]
AUDIENCES = {"kids": "all", "teens": "teen", "adults": "adult"}
LABELS = {"kids": "Kids (under 13)", "teens": "Teens (13–17)", "adults": "Adults"}
RATING_LABELS = {"all": "All ages", "teen": "Teens+", "adult": "Adults"}

TEEN = ["dating", "date a", "boyfriend", "girlfriend", "crush", "relationship", "marriage", "married",
        "marry", "divorce", "alcohol", "drink", "drunk", "drug", "smok", "tobacco", "cigarett", "vap",
        "depress", "anxiety", "caste", "bully", "1984", "genocide", "torture", "riot", "killed", "killing",
        "murder", "violence", "weapon", "second wife", "second marriage", "elope", "interfaith marriage",
        "pregnan", "period", "menstrua"]
ADULT = ["sex", "sexual", "porn", "intercourse", "rape", "abortion", "affair", "adulter", "contracept",
         "masturbat", "suicid", "self-harm", "self harm", "cutting myself", "abuse", "abused", "incest",
         "prostitut", "naked", "nude", "kill myself"]
_TEEN = re.compile(r"\b(?:" + "|".join(map(re.escape, TEEN)) + r")", re.I)
_ADULT = re.compile(r"\b(?:" + "|".join(map(re.escape, ADULT)) + r")", re.I)


def rate_text(head: str, body: Iterable[str] = ()) -> str:
    """head (question/title) counts on one hit; body text (answers) needs two,
    so an answer that mentions alcohol once in passing doesn't age-gate a thread."""
    body = " ".join(b[:1500] for b in body)
    if _ADULT.search(head) or len(_ADULT.findall(body)) >= 2:
        return "adult"
    if _TEEN.search(head) or len(_TEEN.findall(body)) >= 2:
        return "teen"
    return "all"


def stricter(a: str, b: str) -> str:
    return max(a, b, key=RATINGS.index) if a in RATINGS and b in RATINGS else (a if a in RATINGS else b)


def normalize(audience: Optional[str]) -> Optional[str]:
    a = (audience or "").strip().lower()
    return a if a in AUDIENCES else None


def allowed(rating: str, audience: Optional[str]) -> bool:
    """No audience chosen = no filtering."""
    a = normalize(audience)
    if not a:
        return True
    return RATINGS.index(rating if rating in RATINGS else "all") <= RATINGS.index(AUDIENCES[a])
