"""Run eval questions against a running backend. Owner: Avneet (runner) · acceptance questions: Jaspreet.

Usage: python3 evals/run_evals.py [--base-url http://localhost:8000] [--questions evals/questions.jsonl]
Contract: docs/ARCHITECTURE.md § 4.
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime
from pathlib import Path


def ask(base_url: str, question: str) -> dict:
    req = urllib.request.Request(
        f"{base_url}/api/ask",
        data=json.dumps({"question": question}).encode(),
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--questions", type=Path, default=Path("evals/questions.jsonl"))
    ap.add_argument("--note", default="", help="what changed, for results.md")
    args = ap.parse_args()

    cases = [json.loads(l) for l in args.questions.open(encoding="utf-8") if l.strip()]
    hit = in_scope = cited = oos_ok = oos = 0
    mode = "?"
    for c in cases:
        res = ask(args.base_url, c["question"])
        mode = res.get("mode", "?")
        ids = [x["id"] for x in res.get("citations", [])]
        if c.get("should_cover", True):
            in_scope += 1
            ok_hit = bool(set(ids) & set(c.get("expected_ids", [])))
            hit += ok_hit
            cited += bool(ids) and res.get("coverage") != "not_found"
            mark = "PASS" if ok_hit else "MISS"
        else:
            oos += 1
            ok = res.get("coverage") == "not_found"
            oos_ok += ok
            mark = "PASS" if ok else "FAIL (should be not_found)"
        print(f"[{mark}] {c['question']}  -> coverage={res.get('coverage')} cites={ids}")

    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"
    summary = (f"retrieval hit@5 {pct(hit, in_scope)} · cited {pct(cited, in_scope)} · "
               f"out-of-scope→not_found {pct(oos_ok, oos)} · mode={mode}")
    print("\n" + summary)
    with Path("evals/results.md").open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.now():%Y-%m-%d %H:%M} · {summary}{' · ' + args.note if args.note else ''}\n")


if __name__ == "__main__":
    main()
