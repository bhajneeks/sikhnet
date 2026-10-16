# Avneet — RAG engine
updated: 2026-10-16
branch: avneet/rag

## Now
Answer layer: make /api/ask return `follow_ups` (R2) and `perspectives` (R4).
Both are required by the contract and are currently missing from the response.

## Done
- Real dataset ingested: 300 questions / 853 answers → data/processed/qa.jsonl,
  0 skipped, contract-clean, re-ingest byte-identical (ids stable).
  **One record per answer**, so the 230 multi-answer threads can be cited
  individually — that's the raw material for R4 perspectives.
- 12 forum categories mapped to the 6 contract categories. Original kept in
  `tags` + `extra.dataset_category`.
- Retrieval: indexes `extra.question_body`, strips quoted ">" reply lines,
  one hit per thread before runners-up (top-5 went from 3 distinct threads
  to 5), and implements the contract's R3 primary-first tie-break.
- gitignore hardened: `data/processed/` was **not** ignored, so qa.jsonl was
  one `git add -A` away from the public repo. Hackathon terms forbid that.

## Next
- `/api/ask` is missing `follow_ups` and `perspectives` entirely; `citations`
  is missing `source` and `source_type`. (contract § 3)
- Out-of-scope questions return `coverage: "grounded"` — "what is the capital
  of Brazil" matches at ~2.0 and MIN_SCORE is 1.0. Needs a real threshold
  plus a not_found eval case.
- Confirm the model id in `backend/llm.py` / `.env.example`: it is
  `claude-opus-5-5`, which I don't think exists. Verify before the demo —
  in llm mode this fails on every call, and we only ever ran fallback mode.
- Add ANTHROPIC_API_KEY to .env and confirm llm mode end to end.
- Retrieval: synonyms (started/founded), romanised Punjabi (dastaar/turban,
  nitnem), legacy ASCII-Gurmukhi posts (83 records tagged `gurmukhi`).

## Blocked on / needs from others
- **Bhajneek (R5):** no record maps to the `music` category — the dataset has
  no kirtan/music category, so a "music" dropdown entry returns nothing.
  Either drop it, or pull music Q&A from a secondary source.
- **Jaspreet:** answers are community opinions and often disagree (datasheet:
  "Not authoritative"). Need a ruling on how the UI frames that — the dataset
  has no single "org answer", which affects how we present R3/R4 primacy.

## Files I'm touching
- ingest/, backend/retrieval.py, backend/prompts.py, backend/llm.py, backend/app.py, data/

## Notes for everyone
- The dataset is **not** in git and must not be. Get it from the team Drive
  folder into `data/raw/`, then `python3 ingest/ingest.py data/raw/qa-sample-300.jsonl --source sikhnet-qa-dataset`.
- Terms: hackathon use only, no redistribution, delete all copies (including
  vector stores and caches) within 30 days. See `data/raw/DATASHEET.md`.
