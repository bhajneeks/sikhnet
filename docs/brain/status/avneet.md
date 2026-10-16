# Avneet — RAG engine
updated: 2026-10-16
branch: avneet/rag

## Now
Nothing in flight. Next most useful thing is running llm mode for real
(needs ANTHROPIC_API_KEY) — everything below was verified in fallback mode only.

## Done
- **Real dataset ingested**: 300 questions / 853 answers → data/processed/qa.jsonl,
  0 skipped, contract-clean, re-ingest byte-identical (ids stable).
  **One record per answer**, so the 230 multi-answer threads can be cited
  individually — that's the material R4 perspectives is built from.
- 12 forum categories mapped to the 6 contract categories; original kept in
  `tags` + `extra.dataset_category`.
- **Retrieval**: indexes `extra.question_body`, strips quoted ">" reply lines,
  one hit per thread before runners-up (top-5 went from 3 distinct threads to
  5), R3 primary-first tie-break, and `thread_answers()` for perspectives.
- **`/api/ask` now meets contract § 3**: `follow_ups` (R2) and `perspectives`
  (R4) were missing entirely; `citations` lacked `source`/`source_type`.
  Verified field-by-field against Manveer's `frontend/app.js` — every field it
  reads off the ask response, citations and perspectives is now present.
- **llm mode** returns answer/coverage/perspectives/follow_ups in one
  structured-outputs call instead of scraping a trailing "COVERAGE:" line.
- **Model id was `claude-opus-5-5`, which doesn't exist** — llm mode would have
  failed on every call. Now `claude-opus-5`.
- **Coverage gate**: every out-of-scope question used to come back "grounded".
  Measured before fixing — BM25 scores don't separate in/out of scope (out
  reached 11.5, in went as low as 2.9). Unseen vocabulary does.
- gitignore hardened: `data/processed/` was **not** ignored, so qa.jsonl was one
  `git add -A` from the public repo. Hackathon terms forbid that.

## Next
- Add ANTHROPIC_API_KEY to .env and exercise llm mode end to end. Untested:
  the structured-output schema, perspectives quality, follow-up quality.
- Retrieval: synonyms (started/founded, community kitchen/langar), romanised
  Punjabi (dastaar/turban, nitnem), legacy ASCII-Gurmukhi posts (83 records
  tagged `gurmukhi` are currently unsearchable by their Gurmukhi text).
- Consider embeddings if keyword recall stays the limiting factor.

## Known gaps (not blockers, but don't demo into them)
- **Fallback mode still answers generic-English out-of-scope questions.**
  "What is the best laptop to buy?" returns `grounded` because *best*, *laptop*
  and *buy* all genuinely appear in forum posts. I tried question-side overlap
  and rarest-term matching; both rejected more real questions than they caught.
  llm mode handles this correctly, since the model reads the entries.
- **Fallback perspectives are raw forum posts.** Sibling answers are quoted
  verbatim, so some are chit-chat rather than a real alternative view (one
  came out as a post about shampoo). In llm mode the model decides what counts
  as a genuine differing view and returns `[]` when entries agree.

## Blocked on / needs from others
- **Jaspreet — `evals/questions.jsonl` is stale and silently scoring 0.**
  `expected_ids` are the placeholder sample ids (`qa_sample0001`), which cannot
  match real dataset ids, so retrieval hit@5 reads 0/3 no matter what retrieval
  does. Needs real ids, and ideally more than one out-of-scope case. Current:
  `hit@5 0/3 · cited 3/3 · out-of-scope→not_found 0/1` (the one failure is the
  laptop case above).
- **Jaspreet — framing.** The datasheet is explicit that these are unvetted
  community opinions that often disagree, and there is no single "org answer"
  in this dataset. That affects how R3/R4 primacy should read in the UI. I've
  made the prompt say answers are community views, not rulings — confirm that's
  the tone you want.
- **Bhajneek — R5 `music`.** No record maps to `music` (the forum had no
  kirtan/music category). Correction to what I wrote earlier: this degrades
  gracefully — `/api/categories` derives from the data, so `music` never
  appears in the dropdown. Only matters if you want music as a topic, which
  would need a secondary source.

## Files I'm touching
- ingest/, backend/retrieval.py, backend/prompts.py, backend/llm.py, backend/app.py, data/

## Notes for everyone
- The dataset is **not** in git and must not be — this repo is public and the
  hackathon terms forbid committing the data or anything derived from it. Get it
  from the team Drive folder into `data/raw/`, then:
  `python3 ingest/ingest.py data/raw/qa-sample-300.jsonl --source sikhnet-qa-dataset`
- Terms: hackathon use only, no redistribution, delete all copies (including
  vector stores and caches) within 30 days. See `data/raw/DATASHEET.md`.
