# Bhajneek — Future features
updated: 2026-10-16
branch: bhajneek/features

## Now
R5 Surprise me v3 pushed (PR #1). Branch now also carries avneet/rag + manveer/ui merges.

## Done
- R5 v3: picks per question thread, forum category + keyword topics (music/art now populate),
  quality-filtered seeds, hooks verified retrievable via search(), team model, background
  prefetch (instant clicks). Evals: R5 6/6 categories.
- R5: /api/surprise v2 — topics theology/history/music/literature/art/practice inferred
  from text (no category column needed), free-text topics, no repeats, primary first,
  Claude-written hook grounded in one entry (falls back to dataset question). Decision 004.
- Merged Manveer's UI v1 (origin/manveer/ui) into my branch to test against it.

## Next
- R3: first secondary-source importer (SikhiWiki) in ingest/sources/ with source_type secondary
- R3: agree with Avneet how secondary records are loaded (secondary.jsonl vs merged)
- docs/ROADMAP.md: what we'd build next for the org's other properties

## Blocked on / needs from others
- Real dataset file in my data/raw to tune keywords on real questions (tested on synthetic threads so far)

## Files I'm touching
- backend/features/, ingest/sources/, docs/ROADMAP.md
