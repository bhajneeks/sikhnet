"""Run eval questions against a running backend. Owner: Avneet (runner) · acceptance questions: Jaspreet.

Usage: python3 evals/run_evals.py [--base-url http://localhost:8000] [--questions evals/questions.jsonl]
Contract: docs/ARCHITECTURE.md § 4. Per-requirement reporting: docs/REQUIREMENTS.md.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def post(base_url: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def get(base_url: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=60) as r:
        return json.loads(r.read())


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


def check_r5(base_url: str) -> tuple[int, int, list[str]]:
    """R5: surprise works for every category the API offers."""
    try:
        categories = get(base_url, "/api/categories").get("categories", [])
    except (urllib.error.URLError, OSError):
        return 0, 0, ["/api/categories unreachable"]
    ok, broken = 0, []
    for c in categories:
        try:
            res = get(base_url, f"/api/surprise?category={urllib.parse.quote(c)}")
        except (urllib.error.URLError, OSError):
            broken.append(f"{c} (error)")
            continue
        if res.get("question"):
            ok += 1
        else:
            broken.append(f"{c} (no question)")
    return ok, len(categories), broken


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--questions", type=Path, default=Path("evals/questions.jsonl"))
    ap.add_argument("--note", default="", help="what changed, for results.md")
    args = ap.parse_args()

    cases = [json.loads(l) for l in args.questions.open(encoding="utf-8") if l.strip()]

    hit = in_scope = cited = oos_ok = oos = 0
    r2_ok = r2_applicable = 0      # answers carrying 3 follow-ups
    r3_ok = r3_applicable = 0      # primary cited before secondary
    r4_ok = r4_expected = 0        # perspectives present only when expected
    mode = "?"

    for c in cases:
        res = post(args.base_url, "/api/ask", {"question": c["question"]})
        mode = res.get("mode", "?")
        citations = res.get("citations", [])
        ids = [x["id"] for x in citations]
        coverage = res.get("coverage")
        follow_ups = res.get("follow_ups") or []
        perspectives = res.get("perspectives") or []

        # R2 — 3 follow-ups under every answer that isn't a miss. Counted over
        # answers actually given, which is not the same set as the in-scope
        # cases: an off-topic case that wrongly answers still owes follow-ups.
        if coverage != "not_found":
            r2_applicable += 1
            r2_ok += len(follow_ups) == 3

        # R3 — when both source types are cited, primary must come first.
        types = [x.get("source_type", "primary") for x in citations]
        if "primary" in types and "secondary" in types:
            r3_applicable += 1
            r3_ok += types.index("primary") < types.index("secondary")

        # R4 — perspectives only when the case says to expect them.
        if "expect_perspectives" in c:
            r4_expected += 1
            r4_ok += bool(perspectives) == bool(c["expect_perspectives"])

        if c.get("should_cover", True):
            in_scope += 1
            ok_hit = bool(set(ids) & set(c.get("expected_ids", [])))
            hit += ok_hit
            cited += bool(ids) and coverage != "not_found"
            mark = "PASS" if ok_hit else "MISS"
        else:
            oos += 1
            ok = coverage == "not_found"
            oos_ok += ok
            mark = "PASS" if ok else "FAIL (should be not_found)"

        print(f"[{mark}] {c['question']}")
        print(f"        coverage={coverage} cites={len(citations)} follow_ups={len(follow_ups)} "
              f"perspectives={len(perspectives)}")
        if ids:
            print(f"        ids={ids[:5]}")

    r5_ok, r5_total, r5_broken = check_r5(args.base_url)

    print("\n--- per requirement (docs/REQUIREMENTS.md) ---")
    print(f"R1 citations     cited {pct(cited, in_scope)} · off-topic→not_found {pct(oos_ok, oos)}")
    print(f"R1 retrieval     hit@5 {pct(hit, in_scope)}")
    print(f"R2 follow-ups    exactly 3 on {pct(r2_ok, r2_applicable)} answers given")
    print(f"R3 primary first {pct(r3_ok, r3_applicable)}"
          + ("  (no case cites both source types yet)" if not r3_applicable else ""))
    print(f"R4 perspectives  as expected {pct(r4_ok, r4_expected)}"
          + ("  (no case sets expect_perspectives yet)" if not r4_expected else ""))
    print(f"R5 surprise      {pct(r5_ok, r5_total)} categories"
          + (f"  broken: {', '.join(r5_broken)}" if r5_broken else ""))

    summary = (f"hit@5 {pct(hit, in_scope)} · cited {pct(cited, in_scope)} · "
               f"off-topic→not_found {pct(oos_ok, oos)} · R2 {pct(r2_ok, r2_applicable)} · "
               f"R4 {pct(r4_ok, r4_expected)} · R5 {pct(r5_ok, r5_total)} · mode={mode}")
    print("\n" + summary)
    with Path("evals/results.md").open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.now():%Y-%m-%d %H:%M} · {summary}{' · ' + args.note if args.note else ''}\n")


if __name__ == "__main__":
    main()
