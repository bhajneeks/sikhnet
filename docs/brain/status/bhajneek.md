# Bhajneek — Future features
updated: 2026-10-16
branch: bhajneek/features

## Now
SikhNet feedback shipped on bhajneek/features (decision 006): ratings, popular, age groups,
moderation, bulletin board, landing page. PR into main open; needs Manveer to review UI edits.

## Done
- Decision 006 (SikhNet feedback): 👍/👎 + Wilson ranking + accuracy tags; popular topics / most asked;
  Kid/Teen/Adult age groups; moderation (bots, hate, links, Claude review, reports, queue at /moderate.html);
  crisis → help lines, never AI; community board at /community.html; landing page explaining the product.
  All in backend/features/ + new pages; /api/ask untouched. SQLite in data/community/ (gitignored).
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
- railway.json, scripts/start.sh, scripts/fetch_dataset.py, docs/DEPLOY.md (decision 007)
- frontend/community.*, moderate.*, common.js (new) + landing/rating edits in index.html, app.js, style.css (told Manveer)
- backend/features/, ingest/sources/, docs/ROADMAP.md
