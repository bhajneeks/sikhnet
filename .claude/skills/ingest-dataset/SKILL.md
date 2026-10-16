---
name: ingest-dataset
description: Convert the raw Sikhi Q&A dataset (CSV, XLSX, JSON, Google Sheets export) into the canonical data/processed/qa.jsonl with stable ids and provenance, then report counts and data-quality issues. Use when the user says "ingest the data", "load the dataset", "we got new questions", "re-run ingestion", or adds files to data/raw/.
---

# Ingest Dataset

Adapted from gbrain's `ingest` + `bulk-ingestion` + `brain-ingest-gate` skills:
every record keeps where it came from, ingestion is idempotent, and you report
what you skipped instead of silently dropping it.

## Contract (owned by Avneet, RAG lane — see TEAM.md)

Output: `data/processed/qa.jsonl`, one JSON object per line, schema in
`docs/ARCHITECTURE.md` § Data contract. Required fields: `id`, `question`,
`answer`, `source`. Never change the schema without the `capture-decision` skill.

## Steps

1. Put raw exports in `data/raw/` (gitignored — share large raw files via the
   team Google Drive folder, not git).
2. Inspect before converting: print column names, row count, 3 sample rows,
   empty-cell counts per column. Map columns to the schema; ask the user if a
   mapping is ambiguous (e.g. two "answer"-like columns).
3. Run `python3 ingest/ingest.py data/raw/<file> [--question-col Q --answer-col A ...]`.
4. Read the report it prints. It must state: rows read, rows written,
   rows skipped and why (empty question/answer, exact duplicates).
5. Spot-check 5 random output records against the raw file.
6. Commit `data/processed/qa.jsonl` if it's under ~20 MB; otherwise record in
   `docs/brain/decisions/` where the processed file lives.
7. Update your status file with the new record count.

## Rules

- `id` must be stable across re-runs (hash of normalized question + source),
  so citations in evals and the UI don't break when data is re-ingested.
- Keep Gurmukhi text exactly as given (UTF-8). Do not transliterate, translate,
  or "clean up" Gurbani quotes.
- Never invent answers to fill gaps. Empty answer → skip and report.
