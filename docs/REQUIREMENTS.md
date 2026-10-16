# Judge requirements — what we are scored on

Source: the judge/sponsor brief (shared by Manveer, 2026-10-16). **Owner of this file and of
all client-expectation questions: Jaspreet (Product & PM).** **Every feature,
prompt and UI decision should be checked against this list.** If a change
doesn't serve one of these, it's lower priority than one that does.

| # | Requirement | What "done" looks like in the demo | Owner(s) | Priority |
|---|---|---|---|---|
| R1 | **Pertinent, source-cited answers** — "here's where I got the answer from" | Every answer shows numbered citations; clicking one shows the original Q&A entry (and link if we have one). Off-topic questions get an honest "not in our sources". | Avneet (retrieval + prompt), Manveer (citation UI) | Must |
| R2 | **Follow-up suggestions after every answer** — "Here are some recommended questions based on your inquiry", like ChatGPT/Google | 3 clickable follow-up questions under every answer; clicking one asks it. Prefer follow-ups the dataset can actually answer. | Avneet (API `follow_ups`), Manveer (chips UI) | Must |
| R3 | **Scalable to the org's other properties** (e.g. SikhiWiki and their other websites); the org's own answer weighted most, other sources underneath | Data has a `source_type` (`primary` = the org's Q&A dataset, `secondary` = other properties). Retrieval/prompt rank primary first; secondary appears in a separate "From other sources" section. Adding a new site = run ingest with `--source-type secondary`. | Bhajneek (other-property importers + weighting), Avneet (ranking tie-break + prompt) | Should (optional per judge — design for it now, demo it if time) |
| R4 | **Multifaceted** — if there are alternative interpretations or different views, present them, but keep the org's answer clearly primary | Answer = clear main answer first, then an "Other perspectives" section (only when sources actually contain differing views — never invented), each with citations. | Avneet (prompt + `perspectives` field), Manveer (UI section) | Must |
| R5 | **"Surprise me"** with a topic dropdown (theology, music, literature, history, …) that gives a fun rabbit-hole prompt | Dropdown + "Surprise me" button; picking a topic returns an intriguing question drawn from our dataset in that category and asks it. | Bhajneek (`/api/surprise`, categories), Manveer (dropdown UI) | Must |

## Non-negotiables that cut across all of these

- Grounded only: nothing in an answer, follow-up, perspective, or surprise prompt
  may come from outside our sources (see `grounded-answer` skill).
- Respectful tone; org's position stated clearly and first.
- Demo must work end-to-end on `main`.

## How Jaspreet accepts our work against this (evals)

`evals/run_evals.py` should report, per requirement:
R1 citation rate + not_found on off-topic · R2 % answers with 3 follow-ups ·
R3 primary source cited first when both exist · R4 perspectives present only when
expected · R5 surprise works for every category.
