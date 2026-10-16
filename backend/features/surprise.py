"""R5 "Surprise me": topic list + a random rabbit-hole question. Owner: Bhajneek.

v1 picks a random dataset question in the category. Ideas for v2: rewrite it into a
more intriguing hook with Claude (grounded in that entry), avoid repeats per session.
"""
from __future__ import annotations

import random
from typing import Optional

from fastapi import APIRouter

from backend import retrieval

router = APIRouter()
DEFAULT_CATEGORIES = ["theology", "history", "music", "literature", "practice"]


def _category(record: dict) -> str:
    if record.get("category"):
        return record["category"]
    tags = [t.lower() for t in record.get("tags", [])]
    return next((c for c in DEFAULT_CATEGORIES if c in tags), "other")


def categories() -> list[str]:
    found = {_category(r) for r in retrieval.all_records()}
    return [c for c in DEFAULT_CATEGORIES if c in found] + sorted(found - set(DEFAULT_CATEGORIES))


def random_question(category: Optional[str] = None) -> Optional[dict]:
    pool = [r for r in retrieval.all_records() if not category or _category(r) == category]
    return random.choice(pool) if pool else None


@router.get("/api/categories")
def get_categories():
    return {"categories": categories()}


@router.get("/api/surprise")
def surprise(category: Optional[str] = None):
    r = random_question(category)
    if not r:
        return {"question": None, "category": category, "id": None}
    return {"question": r["question"], "category": _category(r), "id": r["id"]}
