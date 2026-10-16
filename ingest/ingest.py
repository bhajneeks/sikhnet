"""Convert a raw Q&A export (CSV / XLSX / JSON / JSONL) into data/processed/qa.jsonl.

Usage:
  python3 ingest/ingest.py data/raw/questions.csv
  python3 ingest/ingest.py data/raw/export.xlsx --question-col "Question" --answer-col "Answer"

Schema: docs/ARCHITECTURE.md § Data contract. Owner: data lane (see TEAM.md).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

QUESTION_GUESSES = ["question", "questions", "q", "query", "title", "prompt"]
ANSWER_GUESSES = ["answer", "answers", "a", "response", "reply", "body"]
URL_GUESSES = ["url", "link", "source_url", "source"]
TAG_GUESSES = ["tags", "tag", "category", "categories", "topic"]


def read_rows(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    if suffix == ".jsonl":
        return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("data") or data.get("items") or []
    if suffix in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook

        ws = load_workbook(path, read_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        header = [str(h).strip() if h is not None else f"col{i}" for i, h in enumerate(rows[0])]
        return [dict(zip(header, r)) for r in rows[1:]]
    sys.exit(f"Unsupported file type: {suffix}")


def pick(columns: list[str], explicit: str | None, guesses: list[str]) -> str | None:
    if explicit:
        if explicit not in columns:
            sys.exit(f"Column {explicit!r} not found. Columns: {columns}")
        return explicit
    lowered = {c.lower().strip(): c for c in columns}
    return next((lowered[g] for g in guesses if g in lowered), None)


def stable_id(question: str, source: str) -> str:
    norm = " ".join(question.lower().split())
    return "qa_" + hashlib.sha1(f"{norm}|{source}".encode()).hexdigest()[:10]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/processed/qa.jsonl"))
    ap.add_argument("--source", default=None, help="source label (default: input file stem)")
    ap.add_argument("--question-col")
    ap.add_argument("--answer-col")
    ap.add_argument("--url-col")
    ap.add_argument("--tags-col")
    ap.add_argument("--append", action="store_true", help="merge into existing output instead of replacing")
    args = ap.parse_args()

    rows = read_rows(args.input)
    if not rows:
        sys.exit("No rows read.")
    columns = list(rows[0].keys())
    q_col = pick(columns, args.question_col, QUESTION_GUESSES)
    a_col = pick(columns, args.answer_col, ANSWER_GUESSES)
    url_col = pick(columns, args.url_col, URL_GUESSES)
    tags_col = pick(columns, args.tags_col, TAG_GUESSES)
    if not q_col or not a_col:
        sys.exit(f"Could not detect question/answer columns. Columns: {columns}\n"
                 "Pass --question-col and --answer-col.")
    source = args.source or args.input.stem
    print(f"Columns: {columns}\nUsing question={q_col!r} answer={a_col!r} url={url_col!r} tags={tags_col!r}")

    records: dict[str, dict] = {}
    if args.append and args.out.exists():
        for line in args.out.open(encoding="utf-8"):
            r = json.loads(line)
            records[r["id"]] = r

    skipped = {"empty_question": 0, "empty_answer": 0, "duplicate": 0}
    used = {q_col, a_col, url_col, tags_col}
    for row in rows:
        q = str(row.get(q_col) or "").strip()
        a = str(row.get(a_col) or "").strip()
        if not q:
            skipped["empty_question"] += 1
            continue
        if not a:
            skipped["empty_answer"] += 1
            continue
        rid = stable_id(q, source)
        if rid in records:
            skipped["duplicate"] += 1
            continue
        tags_raw = row.get(tags_col) if tags_col else None
        tags = [t.strip() for t in str(tags_raw).replace(";", ",").split(",") if t.strip()] if tags_raw else []
        records[rid] = {
            "id": rid,
            "question": q,
            "answer": a,
            "source": source,
            "source_url": (str(row.get(url_col)).strip() or None) if url_col and row.get(url_col) else None,
            "tags": tags,
            "extra": {k: v for k, v in row.items() if k not in used and v not in (None, "")},
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    print(f"Rows read: {len(rows)}  Written: {len(records)}  Skipped: {skipped}")
    print(f"Output: {args.out}")


if __name__ == "__main__":
    main()
