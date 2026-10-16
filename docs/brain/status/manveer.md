# Manveer — UI / UX
updated: 2026-10-16 15:10
branch: manveer/ui

## Now
Chat UI v2 (beige + light blue) on manveer/ui; PR into main not opened yet.
Design: https://claude.ai/artifact/RDNoyCDZTpw4kvmi4fVPBg (private until shared)

## Done
- Chat box v2: composer with Enter/Shift+Enter hint, rotating example questions, Stop (and Esc), "/" to focus; Copy + Ask again on each answer; scroll-to-latest button (auto-follow only when at bottom); staged loading text with timer; New chat; topic labels + free-text subject for Surprise me (decision 004)
- Light theme: beige + light blue, Newsreader serif for headings and answers (replaced black + orange)
- frontend/ v1: source cards + clickable [n] chips (R1), Keep exploring follow-ups (R2), Other perspectives / From other sources (R4/R3), topic dropdown + Surprise me (R5), loading / not_found / error states, mobile layout, dark mode. Follow-ups and perspectives stay hidden until /api/ask sends them.
- Claude Design mockup: desktop answer view (source cards R1, Other perspectives + "From other sources" R4/R3, 3 follow-up buttons R2, topic dropdown + Surprise me R5), mobile home, mobile loading + not_found

## Next
- Re-test against Avneet's follow_ups / perspectives once they land
- Polish with real dataset answers (long answers, many citations)
- Accessibility pass (design:accessibility-review)

## Blocked on / needs from others
- @Avneet: /api/ask citations should include source + source_type (contract § 3); UI labels primary vs other sources from them

## Files I'm touching
- frontend/
