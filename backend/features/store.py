"""Community storage (SQLite, stdlib only). Owner: Bhajneek.

Holds what people add to the app: votes/ratings, bulletin-board posts, reports,
anonymous ask counts and the moderation log. Never holds dataset content.

The file lives in data/community/ (gitignored): it is user-generated and the
repo is public. Override with SIKHNET_DB (":memory:" for tests).

Anonymous by design: no accounts. A "voter" is a random id the browser keeps in
localStorage; IPs are only stored as salted hashes, for rate limits and to stop
one person voting many times.
"""
from __future__ import annotations

import hashlib
import math
import os
import secrets
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_id INTEGER,                 -- NULL = thread, else reply to that thread
  title TEXT, body TEXT NOT NULL,
  topic TEXT, audience TEXT NOT NULL DEFAULT 'all',  -- who it's written for
  age_rating TEXT NOT NULL DEFAULT 'all',            -- all | teen | adult (max of poster + classifier)
  status TEXT NOT NULL DEFAULT 'visible',            -- visible | review | hidden
  flags TEXT NOT NULL DEFAULT '',                    -- comma list: link, caps, crisis, reported, ai:hate …
  verified INTEGER NOT NULL DEFAULT 0,               -- marked accurate by a SikhNet moderator
  author TEXT NOT NULL DEFAULT 'Anonymous',
  voter TEXT, ip TEXT, created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS posts_parent ON posts(parent_id, status);
CREATE TABLE IF NOT EXISTS votes (
  target TEXT NOT NULL, voter TEXT NOT NULL, ip TEXT, value INTEGER NOT NULL, reason TEXT,
  created REAL NOT NULL, PRIMARY KEY (target, voter)
);
CREATE TABLE IF NOT EXISTS reports (
  target TEXT NOT NULL, voter TEXT NOT NULL, reason TEXT, created REAL NOT NULL,
  PRIMARY KEY (target, voter)
);
CREATE TABLE IF NOT EXISTS asks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL, norm TEXT NOT NULL,
  topic TEXT, audience TEXT, voter TEXT, created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS asks_norm ON asks(norm);
CREATE TABLE IF NOT EXISTS mod_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT, action TEXT, reason TEXT, created REAL NOT NULL
);
"""


def _path() -> str:
    return os.environ.get("SIKHNET_DB", "data/community/community.db")


# Serverless hosts (Vercel) mount the code read-only; only /tmp is writable.
# /tmp is per-instance and wiped on cold start, so posts there don't last —
# set SIKHNET_DB to a persistent volume (Railway) for real storage.
_FALLBACK = os.path.join(tempfile.gettempdir(), "sikhnet", "community.db")


def _open(p: str) -> sqlite3.Connection:
    if p != ":memory:":
        Path(p).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p, check_same_thread=False, isolation_level=None)
    if p != ":memory:":
        c.execute("PRAGMA journal_mode=WAL")  # fails here too if the dir is read-only
    return c


def conn() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            p = _path()
            try:
                _conn = _open(p)
            except (OSError, sqlite3.OperationalError) as e:
                if p == ":memory:":
                    raise
                print(f"[store] {p} not writable ({e}); using {_FALLBACK} (not persistent)")
                _conn = _open(_FALLBACK)
            _conn.row_factory = sqlite3.Row
            _conn.executescript(SCHEMA)
        return _conn


def reset_for_tests() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = None


def q(sql: str, args: tuple = ()) -> list[sqlite3.Row]:
    with _lock:
        return conn().execute(sql, args).fetchall()


def x(sql: str, args: tuple = ()) -> int:
    """Execute a write; returns lastrowid."""
    with _lock:
        return conn().execute(sql, args).lastrowid


def now() -> float:
    return time.time()


def _salt() -> str:
    rows = q("SELECT value FROM meta WHERE key='salt'")
    if rows:
        return rows[0]["value"]
    s = secrets.token_hex(16)
    x("INSERT OR IGNORE INTO meta(key, value) VALUES ('salt', ?)", (s,))
    return q("SELECT value FROM meta WHERE key='salt'")[0]["value"]


def hash_ip(ip: str | None) -> str:
    return hashlib.sha256(f"{_salt()}:{ip or '-'}".encode()).hexdigest()[:16]


def wilson(up: int, down: int, z: float = 1.96) -> float:
    """Lower bound of the Wilson score interval: 'how good is this, at worst'.
    Ranks 9 up / 1 down above 1 up / 0 down, which a plain average gets wrong."""
    n = up + down
    if n == 0:
        return 0.0
    p = up / n
    return (p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / (1 + z * z / n)


def tallies(targets: list[str]) -> dict[str, dict]:
    """{target: {up, down, score}} for the given vote targets."""
    out = {t: {"up": 0, "down": 0, "score": 0.0} for t in targets}
    if not targets:
        return out
    for i in range(0, len(targets), 500):
        chunk = targets[i:i + 500]
        marks = ",".join("?" * len(chunk))
        for r in q(f"SELECT target, SUM(value > 0) AS up, SUM(value < 0) AS down "
                   f"FROM votes WHERE target IN ({marks}) GROUP BY target", tuple(chunk)):
            out[r["target"]] = {"up": r["up"], "down": r["down"], "score": wilson(r["up"], r["down"])}
    return out


def recent_count(table: str, where: str, args: tuple, seconds: float) -> int:
    return q(f"SELECT COUNT(*) AS n FROM {table} WHERE {where} AND created > ?",
             args + (now() - seconds,))[0]["n"]
