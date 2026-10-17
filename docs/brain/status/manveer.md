# Manveer — UI / UX
updated: 2026-10-16 17:10
branch: manveer/ui

## Now
Sikh-themed UI (Khanda intro, surmai + basanti) tested on the real dataset with llm mode; merging to main.
Design: https://claude.ai/artifact/RDNoyCDZTpw4kvmi4fVPBg (private until shared)

## Done
- Khanda intro screen (public-domain Wikimedia Khanda) that fades into the app; surmai + basanti palette (Nishan Sahib colours per Rehat Maryada)
- Real-data fixes: partial-coverage note, longer loading stages, "SikhNet Q&A · forum answer" labels, Surprise me retries picks that come back not_found, starters swapped for ones the dataset answers
- Chat box v2: composer with Enter/Shift+Enter hint, rotating example questions, Stop (and Esc), "/" to focus; Copy + Ask again on each answer; scroll-to-latest button (auto-follow only when at bottom); staged loading text with timer; New chat; topic labels + free-text subject for Surprise me (decision 004)
- UI polish from "7 Rules for Gorgeous UI": light from above (raised buttons/cards, inset inputs), neutrals + one blue hue, doubled whitespace
- Light theme: beige + light blue, Newsreader serif for headings and answers (replaced black + orange)
- frontend/ v1: source cards + clickable [n] chips (R1), Keep exploring follow-ups (R2), Other perspectives / From other sources (R4/R3), topic dropdown + Surprise me (R5), loading / not_found / error states, mobile layout, dark mode. Follow-ups and perspectives stay hidden until /api/ask sends them.
- Claude Design mockup: desktop answer view (source cards R1, Other perspectives + "From other sources" R4/R3, 3 follow-up buttons R2, topic dropdown + Surprise me R5), mobile home, mobile loading + not_found

## Next
- Re-test against Avneet's follow_ups / perspectives once they land
- Polish with real dataset answers (long answers, many citations)
- Accessibility pass (design:accessibility-review)

## Blocked on / needs from others
- @Bhajneek: surprise.py falls back to raw forum titles that /api/ask can't answer (UI retries for now); topic matching is loose (music → Vaisakhi date)
- @Jaspreet: confirm starter questions and "forum answer" wording; any official SikhNet logo/colours?

## Files I'm touching
- frontend/
