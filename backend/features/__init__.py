"""Future features (R3 multi-source, R5 Surprise me). Owner: Bhajneek (see TEAM.md).

Mounted by backend/app.py via `app.include_router(router)`. Add new feature
endpoints here so they don't collide with the RAG lane's app.py.
"""
from backend.features.surprise import router

__all__ = ["router"]
