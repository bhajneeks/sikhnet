---
id: 006
title: Community features from SikhNet's feedback — ratings, popular, age groups, moderation, bulletin board, landing page
date: 2026-10-17
decided_by: Bhajneek (captain), on SikhNet's feedback
affects: [features, frontend, rag, product]
status: active
source: SikhNet feedback relayed by Bhajneek in chat — (1) rank answers / accuracy tag / audience rating, (2) popular topics & most asked, (3) age segregation, (4) moderation of junk, hate and bots; plus team ask for a bulletin board and a landing page
---

**Decision:** Build all four feedback items plus a bulletin board, entirely
additive (new `/api/*` routes in `backend/features/`, new pages
`community.html` and `moderate.html`; no change to `/api/ask*`). Contract in
docs/ARCHITECTURE.md § 3b.

- **Ratings (#1):** 👍/👎 on bot answers, each archive source and board replies;
  Wilson-score ranking so better answers rise (source cards reorder, replies sort,
  Surprise me favours well-rated answers); tags "Highly rated · 92% helpful";
  bot answers also show an accuracy tag from coverage ("Grounded in 3 SikhNet sources").
  👎 reasons feed the moderator's "low-rated answers" list, which flags archive
  answers for SikhNet to review.
- **Popular (#2):** anonymous ask counts → most asked + trending topics; archive's
  most-discussed threads fill in until there's traffic.
- **Age groups (#3):** "Who's asking? Kid / Teen / Adult" on every page. Threads,
  posts and questions get `all | teen | adult` ratings from keyword rules; lists
  filter; kid mode gates grown-up questions with a gentle note.
- **Moderation (#4):** honeypot + min time + rate limits + duplicate check (bots),
  hate → blocked, links/caps/junk/profanity → held, Claude second opinion in the
  background when a key is set, 3 reports → hidden, moderator queue with
  crisis items first; moderators can mark replies ✓ verified.
- **Crisis (brief non-negotiable):** chat and board messages about self-harm/abuse
  get help lines and are never answered by the AI; crisis chat text is not stored.
- **Bulletin board:** post, reply, vote, report, search, filter by topic/age;
  each question links to SikhNet's archive answers on the same topic.
- **Landing page:** the home screen explains the product (how it works, popular,
  community, safety) in Manveer's palette.

**Why:** it's SikhNet's (the judge's) direct feedback. Board content is kept out
of the model so answers stay grounded only in SikhNet's sources.

**Impact on other lanes:**
- Manveer: `frontend/index.html`, `app.js`, `style.css` gained the landing page,
  rating bars, age picker and crisis card (marked "decision 006"). Please review
  and restyle freely; `community.html`/`moderate.html`/`common.js` are new.
- Avneet: none required. Optional: use `audience` (sent by UI later) to adapt tone in
  the prompt, and `store.tallies()` to boost well-rated records in `search()`.
- Jaspreet: please add feedback #1-#4 to REQUIREMENTS.md as acceptance criteria and
  confirm the help-line list with SikhNet (they should swap in partner orgs).
