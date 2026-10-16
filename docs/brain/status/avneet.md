# Avneet — RAG engine
updated: 2026-10-16
branch: avneet/rag

## Now
Nothing in flight. **llm mode is live and verified** (key in `.env`, gitignored).
PR #2 open against main; Bhajneek's #1 carries Manveer's UI v1.

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
- `evals/questions.jsonl` is the blocker on R1 numbers now, not retrieval (see below).
- More retrieval: legacy ASCII-Gurmukhi posts (83 records tagged `gurmukhi`)
  are unsearchable by their Gurmukhi text. Embeddings if recall stays limiting.


## llm mode — measured, not assumed
- `claude-opus-5`, effort `high`, structured outputs. ~14s per answer; drop
  `SIKHNET_EFFORT` to `medium` if that's too slow for the demo.
- cited 2/3 · off-topic→not_found 1/1 · R2 3 follow-ups on every answer · R5 5/5.
- **R1 is honest**: asked why Sikhs wear a turban, it returned `partial` on its
  own, saying the entries touch on it but none explains it fully. Cited 4
  separate members, suggested asking a Granthi.
- **R4 is real**: on meat-eating, beard-trimming and marrying a non-Sikh it
  produced 2-3 separately-labelled perspectives each, citing genuine
  disagreement between members. Nothing invented.
- **Query expansion** bridges plain English to the dataset's vocabulary
  (community kitchen→langar, sword→kirpan), decided against corpus frequencies
  so it doesn't fire when members already use the user's word.

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
- **Jaspreet — `evals/questions.jsonl` needs rewriting against the real data.**
  Two problems. (1) `expected_ids` are placeholder sample ids (`qa_sample0001`)
  that cannot match real dataset ids, so hit@5 reads 0/3 regardless of
  retrieval quality. (2) More fundamental: the questions are encyclopedia
  basics — "Who started the Sikh faith?", "What is the community kitchen
  called?" — and **this dataset is a forum of specific, often advanced
  questions that does not contain basic definitions.** There is no thread
  saying Guru Nanak founded Sikhi. llm mode correctly answers `not_found`;
  fallback mode only looked better because it cites the top hit whatever it is.
  Acceptance questions should be things the forum actually discusses.
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
