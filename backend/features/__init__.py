"""Future features. Owner: Bhajneek (see TEAM.md).

- surprise.py   R5 Surprise me (topics, hooks)
- community.py  SikhNet feedback: ratings, popular topics, age groups, moderation,
                bulletin board (decision 006)

Mounted by backend/app.py via `app.include_router(router)`. Add new feature
endpoints here so they don't collide with the RAG lane's app.py.
"""
from fastapi import APIRouter

from backend.features import community, surprise

router = APIRouter()
router.include_router(surprise.router)
router.include_router(community.router)

__all__ = ["router"]
