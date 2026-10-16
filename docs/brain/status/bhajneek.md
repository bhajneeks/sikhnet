# Bhajneek — Future features
updated: 2026-10-16
branch: bhajneek/features

## Now
R5 Surprise me v2 done on my branch — opening PR into main.

## Done
- R5: /api/surprise v2 — topics theology/history/music/literature/art/practice inferred
  from text (no category column needed), free-text topics, no repeats, primary first,
  Claude-written hook grounded in one entry (falls back to dataset question). Decision 004.
- Merged Manveer's UI v1 (origin/manveer/ui) into my branch to test against it.

## Next
- R3: first secondary-source importer (SikhiWiki) in ingest/sources/ with source_type secondary
- R3: agree with Avneet how secondary records are loaded (secondary.jsonl vs merged)
- docs/ROADMAP.md: what we'd build next for the org's other properties

## Blocked on / needs from others
- Real dataset in data/raw (Avneet) to tune topic keywords on real questions

## Files I'm touching
- backend/features/, ingest/sources/, docs/ROADMAP.md
