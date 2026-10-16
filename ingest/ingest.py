"""Convert a raw Q&A export (CSV / XLSX / JSON / JSONL) into data/processed/qa.jsonl.

Usage:
  python3 ingest/ingest.py data/raw/qa-sample-300.jsonl        # SikhNet nested export
  python3 ingest/ingest.py data/raw/questions.csv
  python3 ingest/ingest.py data/raw/export.xlsx --question-col "Question" --answer-col "Answer"

Two input shapes are handled:

* **Nested** (the SikhNet forum release): one question per line with an
  ``answers`` list. Each answer becomes its own record, so a thread where
  members disagree yields several records that can be cited individually (R4).
* **Flat** (CSV/XLSX/JSON with question and answer columns): one record per row.

Schema: docs/ARCHITECTURE.md § Data contract. Owner: Avneet, RAG lane (see TEAM.md).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
from pathlib import Path

QUESTION_GUESSES = ["question", "questions", "q", "query", "title", "prompt"]
ANSWER_GUESSES = ["answer", "answers", "a", "response", "reply", "body"]
URL_GUESSES = ["url", "link", "source_url", "source"]
TAG_GUESSES = ["tags", "tag", "category", "categories", "topic"]

# The dataset's 12 forum categories -> the 6 in the data contract (R5 dropdown).
# The original value is always kept in tags + extra.dataset_category, so this
# mapping can be redone without re-reading the raw export.
CATEGORY_MAP = {
    "belief_philosophy": "theology",
    "gurbani_scripture": "theology",
    "interfaith": "theology",
    "history": "history",
    "politics_current_affairs": "history",
    "language_terms": "literature",
    "rehat_practice": "practice",
    "identity_appearance": "practice",
    "gurdwara_sangat": "practice",
    "festivals_ceremonies": "practice",
    "family_life": "practice",
    "other": "other",
}
# Kept in sync with docs/ARCHITECTURE.md § 1. `art` and `music` have no forum
# category to map from — backend/features/surprise.py infers those from text.
CONTRACT_CATEGORIES = {"theology", "history", "music", "literature", "art", "practice", "other"}

GURMUKHI = re.compile(r"[਀-੿]")


def clean(text) -> str:
    """Forum titles come out of the export HTML-escaped (&quot;, &amp;)."""
    return html.unescape(str(text or "")).strip()


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


def stable_id(question: str, source: str, answer_key: str = "") -> str:
    """Stable across re-ingestion. answer_key distinguishes answers to one question."""
    norm = " ".join(question.lower().split())
    seed = f"{norm}|{source}" + (f"|{answer_key}" if answer_key else "")
    return "qa_" + hashlib.sha1(seed.encode()).hexdigest()[:10]


def is_nested(rows: list[dict]) -> bool:
    return isinstance(rows[0].get("answers"), list)


def as_language_list(value) -> list[str]:
    """`language` is a string or a list in the raw data (datasheet: handle both)."""
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)] if value else []


def expand_nested(rows: list[dict], source: str, source_type: str) -> tuple[list[dict], dict]:
    """One record per answer, each carrying its thread's question."""
    records: list[dict] = []
    skipped = {"empty_question": 0, "empty_answer": 0, "duplicate": 0}
    seen: set[str] = set()

    for row in rows:
        title = clean(row.get("title"))
        body = clean(row.get("question"))
        question = title or body
        if not question:
            skipped["empty_question"] += 1
            continue

        raw_category = str(row.get("category") or "other").strip()
        category = CATEGORY_MAP.get(raw_category, "other")
        thread_id = row.get("id")
        languages = as_language_list(row.get("language"))
        answers = row.get("answers") or []

        for position, answer in enumerate(answers, start=1):
            text = clean(answer.get("text"))
            if not text:
                skipped["empty_answer"] += 1
                continue
            answer_id = str(answer.get("id") or f"{thread_id}-a{position}")
            rid = stable_id(question, source, answer_id)
            if rid in seen:
                skipped["duplicate"] += 1
                continue
            seen.add(rid)

            tags = [raw_category]
            if GURMUKHI.search(f"{question}\n{body}\n{text}"):
                tags.append("gurmukhi")

            records.append({
                "id": rid,
                "question": question,
                "answer": text,
                "source": source,
                "source_type": source_type,
                "source_url": None,
                "category": category,
                "tags": tags,
                "extra": {
                    "dataset_category": raw_category,
                    "thread_id": thread_id,
                    "answer_id": answer_id,
                    "answer_position": position,
                    "answers_in_thread": len(answers),
                    # Forum posts bury the real question in an informal body; keep it
                    # for retrieval and context, out of the display `question`.
                    "question_body": body if body and body != question else None,
                    "question_year": row.get("year"),
                    "answer_year": answer.get("year"),
                    "question_language": languages,
                    "answer_language": as_language_list(answer.get("language")),
                },
            })

    return records, skipped


def expand_flat(rows: list[dict], source: str, source_type: str, args) -> tuple[list[dict], dict]:
    columns = list(rows[0].keys())
    q_col = pick(columns, args.question_col, QUESTION_GUESSES)
    a_col = pick(columns, args.answer_col, ANSWER_GUESSES)
    url_col = pick(columns, args.url_col, URL_GUESSES)
    tags_col = pick(columns, args.tags_col, TAG_GUESSES)
    if not q_col or not a_col:
        sys.exit(f"Could not detect question/answer columns. Columns: {columns}\n"
                 "Pass --question-col and --answer-col.")
    print(f"Columns: {columns}\nUsing question={q_col!r} answer={a_col!r} url={url_col!r} tags={tags_col!r}")

    records: list[dict] = []
    skipped = {"empty_question": 0, "empty_answer": 0, "duplicate": 0}
    seen: set[str] = set()
    used = {q_col, a_col, url_col, tags_col}

    for row in rows:
        q = clean(row.get(q_col))
        a = clean(row.get(a_col))
        if not q:
            skipped["empty_question"] += 1
            continue
        if not a:
            skipped["empty_answer"] += 1
            continue
        rid = stable_id(q, source)
        if rid in seen:
            skipped["duplicate"] += 1
            continue
        seen.add(rid)

        tags_raw = row.get(tags_col) if tags_col else None
        tags = [t.strip() for t in str(tags_raw).replace(";", ",").split(",") if t.strip()] if tags_raw else []
        category = next((CATEGORY_MAP.get(t.lower(), t.lower()) for t in tags
                         if CATEGORY_MAP.get(t.lower(), t.lower()) in CONTRACT_CATEGORIES), "other")
        records.append({
            "id": rid,
            "question": q,
            "answer": a,
            "source": source,
            "source_type": source_type,
            "source_url": (str(row.get(url_col)).strip() or None) if url_col and row.get(url_col) else None,
            "category": category,
            "tags": tags,
            "extra": {k: v for k, v in row.items() if k not in used and v not in (None, "")},
        })

    return records, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/processed/qa.jsonl"))
    ap.add_argument("--source", default=None, help="source label (default: input file stem)")
    ap.add_argument("--source-type", default="primary", choices=["primary", "secondary"],
                    help="R3 weighting: the org's own dataset is primary")
    ap.add_argument("--question-col")
    ap.add_argument("--answer-col")
    ap.add_argument("--url-col")
    ap.add_argument("--tags-col")
    ap.add_argument("--append", action="store_true", help="merge into existing output instead of replacing")
    args = ap.parse_args()

    rows = read_rows(args.input)
    if not rows:
        sys.exit("No rows read.")
    source = args.source or args.input.stem

    nested = is_nested(rows)
    print(f"Input: {args.input}  shape={'nested (answers[])' if nested else 'flat (one row per pair)'}  "
          f"rows={len(rows)}  source={source!r}  source_type={args.source_type!r}")

    if nested:
        new_records, skipped = expand_nested(rows, source, args.source_type)
    else:
        new_records, skipped = expand_flat(rows, source, args.source_type, args)

    records: dict[str, dict] = {}
    if args.append and args.out.exists():
        for line in args.out.open(encoding="utf-8"):
            r = json.loads(line)
            records[r["id"]] = r
    kept_existing = len(records)
    for r in new_records:
        records[r["id"]] = r

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    by_category: dict[str, int] = {}
    for r in new_records:
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1

    print(f"Rows read: {len(rows)}  Records built: {len(new_records)}  Skipped: {skipped}")
    if args.append:
        print(f"Merged with existing: {kept_existing} already there -> {len(records)} total")
    print("Categories: " + "  ".join(f"{c}={n}" for c, n in sorted(by_category.items())))
    missing = sorted(CONTRACT_CATEGORIES - set(by_category))
    if missing:
        print(f"NOTE: ingest assigned no records to: {', '.join(missing)}. "
              f"backend/features/surprise.py infers those topics from text, so the "
              f"R5 dropdown can still offer them — no action needed unless it doesn't.")
    print(f"Output: {args.out}  ({len(records)} lines)")


if __name__ == "__main__":
    main()
